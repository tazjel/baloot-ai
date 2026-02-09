import time
from game_logic import Game, GamePhase
from ai_worker.agent import bot_agent
import traceback

def run_bot_simulation():
    print("Starting Bot Logic Crash Test...")
    game = Game("bot_sim_room")
    
    # Add Players (All Bots)
    players = []
    for i in range(4):
        p = game.add_player(f"bot_p{i}", f"BotAgent {i}")
        p.is_bot = True # Mark as bot for logic if needed (though we drive manually)
        players.append(p)
        
    print("Players added.")
    
    if not game.start_game():
        print("Failed to start game.")
        return

    round_count = 0
    while game.phase != GamePhase.FINISHED.value and round_count < 200:
        current_idx = game.current_turn
        current_p = game.players[current_idx]
        
        print(f"--- Turn: {current_p.name} ({game.phase}) ---")
        
        try:
            # Get decision from BotAgent
            # We must pass the serialized game state as the bot expects
            game_state = game.get_game_state()
            decision = bot_agent.get_decision(game_state, current_idx)
            print(f"Decision: {decision}")
            
            action = decision.get('action')
            res = {'success': False}
            
            if game.phase == "BIDDING":
                # Bot returns string action usually? 
                # BotAgent returns {"action": "SUN"} etc.
                if action:
                    res = game.handle_bid(current_idx, action, decision.get('suit'))
                else:
                    print("Error: No action in decision")
                    
            elif game.phase == "PLAYING":
                card_idx = decision.get('cardIndex', 0)
                # Check bounds
                if card_idx < 0 or card_idx >= len(current_p.hand):
                     print(f"CRASH POTENTIAL: Invalid Card Index {card_idx} for hand size {len(current_p.hand)}")
                
                res = game.play_card(current_idx, card_idx)
                
            print(f"Result: {res}")
            
            if not res.get('success'):
                # If bot makes invalid move, it might loop forever or crash
                print("Invalid Move! Stopping to prevent loop.")
                break
                
        except Exception:
            print("CRASH DETECTED IN BOT LOGIC!")
            traceback.print_exc()
            break
            
        round_count += 1
        
    print("Bot Simulation Ended.")
    print(f"Phase: {game.phase}")

if __name__ == "__main__":
    run_bot_simulation()
