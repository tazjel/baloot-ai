import sys
import os
import random
import time
# Add parent directory to sys.path to allow importing modules from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.game_logic import Game, GamePhase, SUITS

def run_simulation():
    print("Starting Headless Game Simulation...")
    game = Game("sim_room")
    
    # Add Players
    players = []
    for i in range(4):
        p = game.add_player(f"p{i}", f"Bot {i}")
        players.append(p)
    print("Players added.")
    
    # Start Game
    if game.start_game():
        print("Game started successfully.")
    else:
        print("Failed to start game.")
        return

    round_count = 0
    while game.phase != GamePhase.FINISHED.value and round_count < 100: # Safety break
        current_p = game.players[game.current_turn]
        
        if game.phase == GamePhase.BIDDING.value:
            # Simple Bidding Logic
            # Dealer's teammate (current_turn) usually passes or bids
            # Let's just make someone bid SUN to get things moving
            # If current_turn is 0, bid SUN, else PASS
            
            # Use a simple counter to vary bids? 
            # Or just have the first player bid SUN.
            
            # To test game logic, we need a valid bid.
            print(f"Bidding Phase. Turn: {current_p.name}")
            
            # Try to bid SUN if no bid yet
            if not game.bid['type']:
                # 50% chance to bid if not yet bid
                if random.random() > 0.5:
                    res = game.handle_bid(current_p.index, "SUN")
                    print(f"{current_p.name} bids SUN: {res}")
                else:
                    res = game.handle_bid(current_p.index, "PASS")
                    print(f"{current_p.name} passes: {res}")
            else:
                 # If bid already exists, everyone passes to start game
                 res = game.handle_bid(current_p.index, "PASS")
                 print(f"{current_p.name} passes (game should start soon): {res}")
                 
        elif game.phase == GamePhase.PLAYING.value:
            # Playing Logic
            # Find valid move
            valid_indices = []
            for idx, card in enumerate(current_p.hand):
                if game.is_valid_move(card, current_p.hand):
                    valid_indices.append(idx)
            
            if valid_indices:
                card_idx = random.choice(valid_indices)
                card = current_p.hand[card_idx]
                print(f"Playing Phase. Turn: {current_p.name}. Plays {card}")
                res = game.play_card(current_p.index, card_idx)
                if not res.get('success'):
                    print(f"Error playing card: {res}")
                    break
            else:
                print(f"Error: No valid moves for {current_p.name} with hand {current_p.hand}")
                break
                
        elif game.phase == GamePhase.WAITING.value:
             print("Game validation error: Back to WAITING?")
             break
             
        round_count += 1
        # time.sleep(0.05) # Small delay to see output if needed
    
    print("Simulation Ended.")
    print(f"Phase: {game.phase}")
    print(f"Scores: Us={game.match_scores['us']}, Them={game.match_scores['them']}")
    print("-" * 20)

if __name__ == "__main__":
    run_simulation()
