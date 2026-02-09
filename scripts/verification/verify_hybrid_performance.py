import logging
import sys
import os
import random
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.logic.game import Game
from game_engine.models.constants import GamePhase
from game_engine.models.card import Card
from ai_worker.agent import bot_agent
from ai_worker.bot_context import BotContext

# Configure Logging
# Force reset of logging handlers
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    filename='hybrid_verification.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

def run_tournament(num_games=20):
    print(f"🏆 STARTING HYBRID MCTS vs HEURISTIC TOURNAMENT ({num_games} Games) 🏆")
    print("Format: Team US (P0, P2) = Hybrid MCTS | Team THEM (P1, P3) = Heuristic")
    
    wins = {'hybrid': 0, 'heuristic': 0}
    start_time = time.time()
    
    for i in range(num_games):
        game_id = f"hybrid_tourney_{int(time.time())}_{i}"
        game = Game(game_id)
        
        # Setup Players
        game.add_player("p0", "Hybrid_Bot_1")
        game.add_player("p1", "Heuristic_Bot_1")
        game.add_player("p2", "Hybrid_Bot_2")
        game.add_player("p3", "Heuristic_Bot_2")
        
        if not game.start_game():
            continue
            
        print(f"Game {i+1}/{num_games} Starting... Floor: {game.floor_card}")
        
        consecutive_passes = 0
        moves_count = 0
        
        while game.phase != GamePhase.FINISHED.value:
            current_idx = game.current_turn
            current_p = game.players[current_idx]
            
            # Construct State with Strategy Config
            game_state = {
                "gameId": game_id,
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
                        "projectedScore": 0,
                        # META-CONFIG: Strategy Injection
                        "strategy": "hybrid" if p.index in [0, 2] else "heuristic"
                    }
                    for p in game.players
                ],
                "tableCards": [],
                "roundHistory": game.round_history,
                "matchScores": game.match_scores,
                "bid": game.bid if game.bid else None
            }
            
            # Serialize Table
            serialized_table = []
            for tc in game.table_cards:
                 serialized_table.append({
                      'card': tc['card'].to_dict(),
                      'playedBy': tc['playedBy'],
                      'metadata': tc.get('metadata', {})
                 })
            game_state['tableCards'] = serialized_table
            
            # Get Decision
            try:
                decision = bot_agent.get_decision(game_state, current_idx)
            except Exception as e:
                logging.error(f"Agent Error: {e}")
                decision = {}

            # Execute
            action = decision.get('action')
            res = None
            
            if action == "PASS":
                if game.phase == "BIDDING":
                    consecutive_passes += 1
                    if consecutive_passes >= 4:
                         res = game.handle_bid(current_idx, "SUN")
                         consecutive_passes = 0
                    else:
                         res = game.handle_bid(current_idx, "PASS")
                elif game.phase == "DOUBLING":
                     res = game.handle_bid(current_idx, "PASS")
                else: 
                     # Force Play Fallback
                     valid = [ix for ix, c in enumerate(current_p.hand) if game.is_valid_move(c, current_p.hand)]
                     if valid: res = game.play_card(current_idx, valid[0])

            elif action in ["BID", "SUN", "HOKUM"]:
                 consecutive_passes = 0
                 b_type = action if action != "BID" else decision.get('type', 'SUN')
                 res = game.handle_bid(current_idx, b_type, decision.get('suit'))
                 if not res or not res.get('success'):
                      # Fallback if illegal bid
                      res = game.handle_bid(current_idx, "PASS")

            elif action == "PLAY":
                 c_idx = decision.get('cardIndex')
                 if c_idx is not None and 0 <= c_idx < len(current_p.hand):
                      res = game.play_card(current_idx, c_idx)
                      if not res or not res.get('success'):
                           valid = [ix for ix, c in enumerate(current_p.hand) if game.is_valid_move(c, current_p.hand)]
                           if valid: res = game.play_card(current_idx, valid[0])
            
            moves_count += 1
            if moves_count > 600: 
                 print("Game Stuck! Breaking.")
                 break
            
        # Determine Winner
        us_score = game.match_scores['us']
        them_score = game.match_scores['them']
        
        winner = 'AMBIGUOUS'
        if us_score > them_score:
             wins['hybrid'] += 1
             winner = 'HYBRID'
        elif them_score > us_score:
             wins['heuristic'] += 1
             winner = 'HEURISTIC'
             
        res_msg = f"Game {i+1}: {winner} (Hybrid: {us_score}, Heuristic: {them_score})"
        print(f"{res_msg}")
        logging.info(res_msg)
        
    print(f"\n\n🏁 TOURNAMENT COMPLETE 🏁")
    print(f"Total Games: {num_games}")
    print(f"Hybrid Wins: {wins['hybrid']} ({wins['hybrid']/num_games*100:.1f}%)")
    print(f"Heuristic Wins: {wins['heuristic']} ({wins['heuristic']/num_games*100:.1f}%)")
    
    with open('hybrid_results.txt', 'w') as f:
         f.write(f"Hybrid: {wins['hybrid']}\nHeuristic: {wins['heuristic']}")

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_tournament(count)
