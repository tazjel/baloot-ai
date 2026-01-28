
import logging
import statistics
from ai_worker.bot_context import BotContext
from ai_worker.mcts.utils import generate_random_distribution
from ai_worker.mcts.fast_game import FastGame
from game_engine.models.constants import SUITS, BidType

logger = logging.getLogger(__name__)

class OracleBiddingStrategy:
    """
    Experimental PIMC (Perfect Information Monte Carlo) Bidding Engine.
    Estimates hand strength by simulating double-dummy games.
    """
    
    def evaluate_hand(self, ctx: BotContext) -> dict:
        """
        Runs simulations to estimate points for SUN and HOKUM.
        Returns detailed stats including Win Probability.
        """
        debug_logs = []
        debug_logs.append(f"[ORACLE] Evaluating Hand: {[str(c) for c in ctx.hand]}")
        
        # 1. Identify candidate suits
        candidates = ['SUN']
        for s in SUITS:
            # Only test suits we have some presence in (heuristic optimization)
            count = sum(1 for c in ctx.hand if c.suit == s)
            if count >= 2: candidates.append(s)
             
        # 2. Generate Worlds
        world_count = 15 # Increased for better stability
        worlds = []
        for _ in range(world_count):
             try:
                hands = generate_random_distribution(ctx)
                worlds.append(hands)
             except Exception as e:
                logger.warning(f"World Gen Failed: {e}")
                
        if not worlds:
             return {"best_bid": None, "error": "Failed to generate worlds"}
             
        # 3. Simulate
        # Store (Score, WinBool) for each simulation
        results = { k: [] for k in candidates }
        
        dealer_idx = ctx.raw_state.get('dealerIndex', 0)
        # Leader is always player after Dealer
        start_turn = (dealer_idx + 1) % 4
        
        for world in worlds:
             for mode in candidates:
                  curr_trump = mode if mode in SUITS else None
                  curr_mode = 'SUN' if mode == 'SUN' else 'HOKUM'
                  
                  # Create FastGame
                  game = FastGame(
                      players_hands=[h[:] for h in world], 
                      trump=curr_trump,
                      mode=curr_mode,
                      current_turn=start_turn,
                      dealer_index=dealer_idx
                  )
                  
                  try:
                      game.play_greedy()
                  except Exception as e:
                      # If simulation fails (e.g. empty hand bug), skip
                      continue
                  
                  # Score from 'us' perspective
                  my_score = game.scores['us']
                  their_score = game.scores['them']
                  
                  # Did we win the bid? (Strict win > them)
                  # In Baloot, if equal, Taker usually loses (Khasara).
                  # So we need MyScore > TheirScore.
                  win = (my_score > their_score)
                  
                  results[mode].append({
                      'score': my_score,
                      'win': win
                  })
                  
        # 4. Aggregate & Decide
        best_bid = "PASS"
        best_metric = 0 # Can be EV or WinProb mix
        details = {}
        
        for k in candidates:
             runs = results[k]
             if not runs: continue
             
             avg_score = statistics.mean([r['score'] for r in runs])
             win_prob = sum(1 for r in runs if r['win']) / len(runs)
             
             details[k] = {
                 'ev': avg_score,
                 'win_prob': win_prob,
                 'samples': len(runs)
             }
             
             debug_logs.append(f"[ORACLE] {k}: WinProb {win_prob:.2%} (EV {avg_score:.1f})")
             
             # Decision Logic
             # Safe Threshold: WinProb > 60% AND EV > Safe Margin
             # Sun Safe: > 76 points (Half of 152) roughly.
             # Hokum Safe: > 81 points (Half of 162).
             # UPDATE: FastGame returns raw points.
             # Sun Max: 130 + 10 = 140. Majority = 70.
             # Hokum Max: 152 + 10 = 162. Majority = 81.
             
             threshold_prob = 0.60 
             
             if k == 'SUN':
                 # Using 65 as baseline (slightly risky but aggressive for strong hands)
                 if win_prob > threshold_prob and avg_score > 65:
                     if win_prob > best_metric:
                         best_metric = win_prob
                         best_bid = "SUN"
                         
             elif k in SUITS:
                 if win_prob > threshold_prob and avg_score > 75: # Hokum usually higher points
                     if win_prob > best_metric:
                         best_metric = win_prob
                         best_bid = "HOKUM"
                         details['best_suit'] = k

        print("\n[ORACLE DEBUG]\n" + "\n".join(debug_logs))
        logger.info("\n".join(debug_logs))
        
        return {
            "best_bid": best_bid,
            "best_suit": details.get('best_suit'),
            "confidence": best_metric,
            "details": details
        }
