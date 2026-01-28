
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
        Runs simulations to estimate points for SUN and HOKUM (Best Suit).
        Returns: { 'SUN': ev, 'HOKUM': ev, 'reasoning': ... }
        """
        debug_logs = []
        debug_logs.append(f"[ORACLE] Evaluating Hand: {[str(c) for c in ctx.hand]}")
        
        # 1. Identify candidate suits (Only check suits we actually have > 1 of?)
        # Or just check highest point suit.
        # Heuristic: Only check 'candidate' suits to save time.
        # Check all SUITS and SUN.
        
        candidates = ['SUN']
        # Add suits where we have at least 2 cards or J/9/A
        for s in SUITS:
             count = sum(1 for c in ctx.hand if c.suit == s)
             if count >= 2: candidates.append(s)
             
        # 2. Generate Worlds
        world_count = 10 # Keep low for MVP speed
        worlds = []
        for _ in range(world_count):
             try:
                hands = generate_random_distribution(ctx)
                worlds.append(hands)
             except Exception as e:
                logger.warning(f"World Gen Failed: {e}")
                
        if not worlds:
             return {"error": "Failed to generate worlds"}
             
        # 3. Simulate
        results = { k: [] for k in candidates }
        
        for idx, world in enumerate(worlds):
             for mode in candidates:
                  # Create Game
                  # Note: Bidding assumes WE start? Or Dealer starts?
                  # In Bidding phase, actual gameplay hasn't started.
                  # Logic: If I bid, I become the Declarer. 
                  # Who leads? The player to the Right of the Dealer (First Player).
                  # We need to respect the actual dealer index.
                  
                  # If we are bidding, we are considering successful bid.
                  # Trump = mode (if suit) or None (if SUN)
                  curr_trump = mode if mode in SUITS else None
                  curr_mode = 'SUN' if mode == 'SUN' else 'HOKUM'
                  
                  # Who leads? 
                  # Dealer Index is in ctx.
                  # Leader = (Dealer + 1) % 4
                  dealer_idx = ctx.raw_state.get('dealerIndex', 0)
                  start_turn = (dealer_idx + 1) % 4
                  
                  game = FastGame(
                      players_hands=[h[:] for h in world], # Copy hands
                      trump=curr_trump,
                      mode=curr_mode,
                      current_turn=start_turn,
                      dealer_index=dealer_idx
                  )
                  
                  game.play_greedy()
                  
                  # Score from 'us' perspective (Indices 0 and 2)
                  # FastGame scores are 'us' vs 'them'.
                  score = game.scores['us']
                  results[mode].append(score)
                  
        # 4. Aggregate
        summary = {}
        for k in candidates:
             vals = results[k]
             avg = statistics.mean(vals)
             min_v = min(vals)
             max_v = max(vals)
             summary[k] = avg
             debug_logs.append(f"[ORACLE] {k}: Avg {avg:.1f} (Range {min_v}-{max_v})")
             
        logger.info("\n".join(debug_logs))
        
        return summary
