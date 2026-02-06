import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from game_engine.logic.game import Game
from game_engine.models.card import Card

def header(msg):
    print(f"\n{'='*50}\n{msg}\n{'='*50}")

def verify_step(name, condition, error_msg):
    if condition:
        print(f"✅ {name}: PASS")
    else:
        print(f"❌ {name}: FAIL - {error_msg}")

def get_step_name(game):
    state = game.qayd_engine.state
    step = state.get('step')
    if hasattr(step, 'name'):
        return step.name
    return str(step)

def run_verification():
    header("STARTING QAYD REFACTOR VERIFICATION")

    # 1. Setup Game
    print("Initializing Game...")
    game = Game("verify_qayd_room")
    
    p0 = game.add_player("human", "Human Player") # Position 0
    p1 = game.add_player("bot1", "Bot 1")
    p2 = game.add_player("bot2", "Bot 2")
    p3 = game.add_player("bot3", "Bot 3")
    
    p0.is_bot = False
    p1.is_bot = True
    p2.is_bot = True
    p3.is_bot = True
    
    game.start_game()
    game.phase = "PLAYING"
    game.game_mode = "HOKUM"
    game.hokum_suit = "HEARTS"
    game.current_round_tricks = []
    
    # Force turns for test setup
    game.current_turn = 0
    
    # Give p0 some cards
    game.players[0].hand = [Card("HEARTS", "ACE"), Card("SPADES", "ACE")]
    # Give p1 (next player) some cards
    game.players[1].hand = [Card("HEARTS", "KING"), Card("DIAMONDS", "KING")]

    # 2. Simulate Illegal Move (Revoke)
    print("\n[Action] Player 0 plays SPADES ACE")
    game.current_turn = 0 # Ensure it's p0's turn
    res0 = game.play_card(0, 1) # Index 1 is Spades Ace
    print(f"P0 Play Result: {res0}")
    
    # Player 1 should follow suit (Spades), but plays Diamonds (Revoke) while having Hearts (Trump).
    game.players[1].hand = [Card("SPADES", "KING"), Card("DIAMONDS", "KING")]
    
    print("\n[Action] Player 1 plays DIAMONDS KING (Should be Revoke because they have SPADES KING)")
    game.current_turn = 1 # Force turn to P1
    res1 = game.play_card(1, 1) # Index 1 is Diamonds King
    print(f"P1 Play Result: {res1}")
    
    # 3. Simulate Bot (P2 - Partner or Enemy? P1 is next)
    # Let's have P2 (Bot) accuse P1 (Bot) or P0 (Human)?
    # Actually, the user report is about Bot accusing User.
    # So P0 (Human) plays illegal card? 
    # Let's swap: P0 plays normally, P1 (Bot) plays illegal, P2 (Bot) detects it? 
    # Or simply: P1 (Bot) triggers Qayd.
    
    print("\n--- STEP 1: Bot Trigger (P2 detecting P1 Revoke) ---")
    
    # We need to simulate P2 triggering.
    # P1 played Diamond King (Revoke).
    # P2 is next. P2 detects it?
    # Engine logic: _bot_auto_accuse just scans table.
    
    try:
        # P2 triggers
        print("Invoking game.handle_qayd_trigger(player_index=2)...")
        trigger_res = game.handle_qayd_trigger(player_index=2)
        print(f"Trigger Result: {trigger_res}")
    except Exception as e:
        print(f"❌ Failed to start challenge: {e}")
        import traceback
        traceback.print_exc()
        return

    # Expectation: Active=True, Step=RESULT (Waiting for timeout)
    verify_step("State is CHALLENGE", game.phase == "CHALLENGE", f"Phase is {game.phase}")
    
    step_name = get_step_name(game)
    verify_step("Qayd Step is RESULT", step_name == "RESULT", f"Step is {step_name}")
    
    verdict = game.qayd_engine.state.get('verdict')
    print(f"Initial Verdict: {verdict}")
    verify_step("Verdict is CORRECT", verdict == "CORRECT", f"Verdict is {verdict}")

    print("\n--- STEP 2: Wait for Timer (Simulate Delay) ---")
    # We won't actually sleep 2s to save time, but we call check_timeout manually
    # pretending time passed.
    game.qayd_engine.state['timer_start'] -= 3 # Force expiry
    
    print("Invoking game.check_timeout()...")
    timeout_res = game.check_timeout()
    print(f"Timeout Result: {timeout_res}")
    
    # Expectation: Result Confirmed, Round Ended (or transitioning)
    # check_timeout calls confirm(), which returns success dict.
    
    verify_step("Time-out confirmed verdict", timeout_res and timeout_res.get('success'), "Timeout didn't confirm")
    
    # Check if we moved to next round or finished
    # confirm() triggers next_round if penalty applied?
    # It sets trigger_next_round=True. Game loop handles it.
    
    print("\nverification complete.")
    return

    print("\nverification complete.")

if __name__ == "__main__":
    run_verification()
