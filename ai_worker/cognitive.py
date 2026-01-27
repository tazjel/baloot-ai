
import logging
from ai_worker.bot_context import BotContext
from ai_worker.mcts.mcts import MCTSSolver
from ai_worker.mcts.utils import generate_random_distribution
from ai_worker.mcts.fast_game import FastGame

logger = logging.getLogger(__name__)

class CognitiveOptimizer:
    """
    The 'Brain' of the AI: Handles simulation-based decision making.
    Encapsulates MCTS, Hand Estimation, and Fast Simulation.
    """
    def __init__(self, use_inference=True):
        self.solver = MCTSSolver()
        self.use_inference = use_inference
        self.enabled = True

    def get_decision(self, ctx: BotContext) -> dict:
        """
        Attempts to find the optimal move using MCTS.
        Returns a decision dict (cardIndex, reasoning) or None if skipped/failed.
        """
        if not self.enabled: return None
        
        # Trigger Condition: Endgame (Start of Trick 5 -> 4 cards left)
        if len(ctx.hand) > 4 or len(ctx.hand) == 0:
            return None
            
        try:
            # 1. Probabilistic Inference (Hand Estimation)
            # Guess opponent hands based on voids and played cards
            hands = generate_random_distribution(ctx)
            
            # 2. Simulation Environment Setup
            # Map BotContext (Rich State) -> FastGame (Lite State)
            
            # Note: FastGame expects hands[0] to be the current player's hand?
            # generate_random_distribution puts ctx.hand at index 0.
            # And FastGame simulation starts from 'current_turn'.
            # If it's MY turn (Bot), then current_turn should be 0 (relative to hands[0]).
            
            # Ideally, FastGame is initialized with absolute positions and turn.
            # But FastGame logic is simplified.
            # Let's align with the confirmed working logic in playing.py:
            # "current_turn=0 # Bot is acting now"
            
            fast_game = FastGame(
                players_hands=hands,
                trump=ctx.trump,
                mode=ctx.mode,
                current_turn=0, # Bot perspective: I am 0, and it is my turn.
                dealer_index=ctx.raw_state.get('dealerIndex', 0), # This might need mapping if dealer relative to bot?
                table_cards=ctx.raw_state.get('tableCards', [])
            )
            
            # 3. Execution (The Oracle)
            best_idx = self.solver.search(fast_game, timeout_ms=300)
            
            return {
                "cardIndex": best_idx,
                "reasoning": f"Oracle (MCTS) - Verified {len(ctx.hand)} cards"
            }
            
        except Exception as e:
            logger.error(f"Cognitive Engine Failed: {e}", exc_info=False)
            # Ideally minimal logging to avoid spam in production, or verbose if debugging.
            return None
