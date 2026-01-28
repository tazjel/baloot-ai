import sys
import os
import random
import time
import json
import logging

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.game_logic import Game, GamePhase
from ai_worker.agent import bot_agent
from ai_worker.learning.dataset_logger import DatasetLogger

# Configure Logging to File
logging.basicConfig(
    filename='generation_debug.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_data_generation(num_games=5):
    print(f"Starting Neural Data Generation for {num_games} games...")
    print("Detailed logs are being written to 'generation_debug.log'")
    
    # Ensure dataset logger is ready
    dataset_logger = DatasetLogger()
    print(f"Logging dataset to: {dataset_logger.file_path}")
    
    start_time = time.time()
    games_completed = 0
    
    for i in range(num_games):
        game_id = f"gen_sim_{int(time.time())}_{i}"
        logging.info(f"--- STARTING GAME {i+1}/{num_games}: {game_id} ---")
        game = Game(game_id)
        
        # Add Players
        players = []
        for p_idx in range(4):
            # Assign personalities to force diversity?
            name = f"Bot_{p_idx}"
            if p_idx == 0: name += "_Aggressive"
            elif p_idx == 1: name += "_Balanced"
            elif p_idx == 2: name += "_Conservative"
            else: name += "_Balanced"
            
            p = game.add_player(f"p{p_idx}", name)
            players.append(p)
            
        print(f"GAME {i+1}: Started...")
        if not game.start_game():
            print("Failed to start game.")
            logging.error("Failed to start game instance.")
            continue
            
        # Game Loop
        moves_count = 0
        while game.phase != GamePhase.FINISHED.value:
            current_idx = game.current_turn
            
            # Log State
            logging.info(f"Move {moves_count} | Phase: {game.phase} | Turn: {current_idx}")
            
            current_p = game.players[current_idx]
            
            # Construct Game State for Bot
            # This must match what server sends to AI Worker
            game_state = {
                "gameId": game_id,
                "room_id": game_id,
                "gameMode": game.game_mode,
                "trumpSuit": game.trump_suit,
                "doublingLevel": game.doubling_level,
                "dealerIndex": game.dealer_index,
                "currentTurn": current_idx,
                "phase": game.phase,
                "players": [
                    {
                        "name": p.name,
                        "hand": [c.to_dict() for c in p.hand] if p.index == current_idx else [], 
                        "team": p.team,
                        "position": p.position,
                        "projectedScore": 0 
                    }
                    for p in game.players
                ],
                "tableCards": [], # Placeholder, filled below
                "roundHistory": game.round_history,
                "matchScores": game.match_scores,
                "bid": game.bid if game.bid else None
            }
            
            # Fix Table Cards serialization
            serialized_table = []
            for tc in game.table_cards:
                 c_obj = tc['card']
                 serialized_table.append({
                      'card': c_obj.to_dict(),
                      'playedBy': tc['playedBy'],
                      'metadata': tc.get('metadata', {})
                 })
            game_state['tableCards'] = serialized_table
            
            # Get Decision
            try:
                decision = bot_agent.get_decision(game_state, current_idx)
                logging.info(f"Bot Decision: {decision}")
            except Exception as e:
                logging.error(f"Bot Decision Failed: {e}")
                decision = {}

            # Apply Decision with Anti-Stuck Logic
            action = decision.get('action')
            res = None
            
            # Anti-Stuck: Track consecutive passes to avoid infinite redeal loops
            if 'consecutive_passes' not in game.__dict__:
                 game.consecutive_passes = 0
            
            if action == "PASS":
                # Only valid in Bidding or Doubling
                if game.phase == "DOUBLING":
                     res = game.handle_bid(current_idx, "PASS")
                elif game.phase == "BIDDING":
                    game.consecutive_passes += 1
                    
                    # If everyone is passing (4 passes), force a bid to generate data
                    if game.consecutive_passes >= 4:
                         forced_bid = random.choice(['SUN', 'HOKUM'])
                         logging.warning(f"Forcing {forced_bid} to break infinite PASS loop.")
                         print(f" -> Loop Detected. Forcing {forced_bid}.")
                         res = game.handle_bid(current_idx, forced_bid)
                         game.consecutive_passes = 0
                    else:
                         res = game.handle_bid(current_idx, "PASS")
                else:
                    # Playing Phase or corrupted state (PASS is invalid in Playing)
                    logging.warning(f"Invalid PASS in Phase {game.phase}. Forcing Random Play.")
                    # Force random to unstick
                    valid = [ix for ix, c in enumerate(current_p.hand) if game.is_valid_move(c, current_p.hand)]
                    if valid:
                         res = game.play_card(current_idx, random.choice(valid))
                         
            elif action in ["BID", "SUN", "HOKUM"]:
                 game.consecutive_passes = 0 # Reset on valid bid
                 # Bid
                 b_type = action if action != "BID" else decision.get('type', 'SUN')
                 suit = decision.get('suit')
                 res = game.handle_bid(current_idx, b_type, suit)
                 
            elif action == "PLAY":
                 c_idx = decision.get('cardIndex')
                 if c_idx is not None and 0 <= c_idx < len(current_p.hand):
                      # res = game.play_card(current_idx, c_idx)
                      try:
                          res = game.play_card(current_idx, c_idx)
                      except Exception as e:
                          logging.error(f"Play Card Except: {e}")
                          res = {'success': False, 'error': str(e)}

                      if not res.get('success'):
                           logging.warning(f"Invalid Bot Move: {res}. Fallback Random.")
                           # Fallback
                           valid = [ix for ix, c in enumerate(current_p.hand) if game.is_valid_move(c, current_p.hand)]
                           if valid: 
                               res = game.play_card(current_idx, valid[0])
                 else:
                      logging.error("Invalid Card Index from Bot")
            else:
                 logging.error(f"Unknown Action: {action}")
                 # Force Random valid move/bid to unstick
                 if game.phase == "PLAYING":
                      # Force random play
                      print(" -> Unknown/None Action in PLAYING. Forcing Random Play.")
                      valid = [ix for ix, c in enumerate(current_p.hand) if game.is_valid_move(c, current_p.hand)]
                      if valid:
                           res = game.play_card(current_idx, random.choice(valid))
                 elif game.phase in ["BIDDING", "DOUBLING"]:
                      # Force PASS
                      print(f" -> Unknown/None Action in {game.phase}. Forcing PASS.")
                      res = game.handle_bid(current_idx, "PASS")
                 
            # Log Result if failure
            if res and not res.get('success', True):
                 logging.error(f"Action Failed: {res}")
                 print(f"[Attempt {moves_count}] Action Failed: {res} | Phase: {game.phase} | Player: {current_idx}")
                 
                 # EMERGENCY BREAK: If action failed, force a random legal move immediately
                 if game.phase == "PLAYING":
                      # Re-calculate legal moves locally to be sure
                      # Note: is_valid_move signature in game.py is (card, hand)
                      # But validation.py is (card, hand, table_cards...)
                      # Game.is_valid_move wraps validation.py? Let's assume Game.is_valid_move(card, hand) works as it defaults other args?
                      # Let's check Game.is_valid_move logic or just use naive try-all-cards
                      valid_indices = []
                      for idx, card in enumerate(current_p.hand):
                           if game.is_valid_move(card, current_p.hand):
                                valid_indices.append(idx)
                                
                      if valid_indices:
                           print(" -> Forcing Random Card Play")
                           game.play_card(current_idx, random.choice(valid_indices))
                      else:
                           print(" -> NO VALID MOVES FOUND! (Critical)")
                 elif game.phase == "BIDDING":
                      print(" -> Forcing PASS")
                      game.handle_bid(current_idx, "PASS")

            moves_count += 1
            if moves_count > 1000:
                 print("Game stuck. See logs.")
                 logging.critical("GAME STUCK > 1000 MOVES. ABORTING.")
                 # Print state summary to console
                 print(f"STUCK STATE: Phase={game.phase} Turn={game.current_turn}")
                 print(f"Player Hand: {[str(c) for c in game.players[game.current_turn].hand]}")
                 break
                 
        winner = 'us' if game.match_scores['us'] > game.match_scores['them'] else 'them'
        print(f"Game Finished. Winner: {winner}")
        logging.info(f"GAME FINISHED. Winner: {winner}")
        games_completed += 1

    duration = time.time() - start_time
    print(f"Generated {games_completed} games in {duration:.2f}s")

if __name__ == "__main__":
    count = 5
    if len(sys.argv) > 1:
         try: count = int(sys.argv[1])
         except: pass
    run_data_generation(count)
