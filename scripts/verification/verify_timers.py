
import time
import sys
import os

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO)

from server.game_logic import Game, GamePhase, Card

def test_timers():
    print("Testing Timers...")
    
    # 1. Bidding Timeout
    print("[1] Testing Bidding Timeout...")
    g = Game("test_timer_room")
    for i in range(4):
        g.add_player(f"p{i}", f"Player {i}")
    g.start_game()
    g.turn_duration = 2
    
    # Start -> Phase=BIDDING, Turn=1 (Random dealer logic may vary but start_game sets turn)
    # Start -> Phase=BIDDING, Turn=1 (Random dealer logic may vary but start_game sets turn)
    current = g.current_turn
    g.reset_timer(2)
    # Manually expire
    g.timer.start_time = time.time() - 5 
    
    res = g.check_timeout()
    if res and res.get('success'):
        if g.players[current].action_text == "PASS":
            print("  PASS Success: Player passed automatically.")
        else:
            print(f"  FAIL: Action text is {g.players[current].action_text}")
    else:
        print(f"  FAIL: No result from check_timeout. Active={g.timer.active}")

    # 2. Playing Timeout
    print("[2] Testing Playing Timeout (Auto-Play Weakest)...")
    g.phase = GamePhase.PLAYING.value
    g.current_turn = 0
    p0 = g.players[0]
    # Hand: Ace (11) and 7 (0)
    p0.hand = [Card('♠', 'A'), Card('♥', '7')]
    # Mock table to make 7 valid (Empty table = any card valid)
    g.table_cards = []
    
    g.reset_timer()
    g.timer.start_time = time.time() - 50 # Expire
    
    res = g.check_timeout()
    
    if res and res.get('success'):
        if len(g.table_cards) == 1:
            card = g.table_cards[0]['card']
            print(f"  Played Card: {card.rank}{card.suit}")
            if card.rank == '7':
                print("  PASS Success: Weakest card (7) played.")
            else:
                print(f"  FAIL: Wrong card played ({card.rank})")
        else:
            print("  FAIL: No card on table")
    else:
        print("  FAIL: No result from check_timeout")

    # 3. Robustness Test (Bot Crash)
    print("[3] Testing Bot Crash Resilience...")
    g.phase = GamePhase.PLAYING.value
    g.current_turn = 0
    p0 = g.players[0]
    p0.hand = [Card('♠', 'A'), Card('♥', '7')]
    g.table_cards = [] 
    
    # Mock bot agent to fail
    from server import bot_agent
    original_decision = bot_agent.bot_agent.get_decision
    def crash_decision(*args):
        raise Exception("Simulated Bot Crash")
    bot_agent.bot_agent.get_decision = crash_decision
    
    g.reset_timer()
    g.timer.start_time = time.time() - 50
    
    res = g.check_timeout()
    if res and res.get('success'):
        print("  PASS Success: Fallback logic handled crash.")
    else:
        print(f"  FAIL: Crash caused failure: {res}")
        
    # Restore
    bot_agent.bot_agent.get_decision = original_decision

if __name__ == "__main__":
    try:
        test_timers()
        print("Done.")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
