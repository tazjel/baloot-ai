
import logging
from ai_worker.bot_context import BotContext
from ai_worker.mcts.mcts import MCTSSolver
from ai_worker.mcts.utils import generate_random_distribution
from ai_worker.mcts.fast_game import FastGame
from ai_worker.learning.dataset_logger import DatasetLogger

logger = logging.getLogger(__name__)

class CognitiveOptimizer:
    """
    The 'Brain' of the AI: Handles simulation-based decision making.
    Encapsulates MCTS, Hand Estimation, and Fast Simulation.
    """
    def __init__(self, use_inference=True, neural_strategy=None):
        self.solver = MCTSSolver(neural_strategy=neural_strategy)
        self.use_inference = use_inference
        self.enabled = True
        # YOLO Configuration: Only log highly confident moves (95%)
        # Buffer 50 moves before writing to disk
        self.dataset_logger = DatasetLogger(min_confidence=0.95, buffer_size=50)

    def get_decision(self, ctx: BotContext) -> dict:
        """
        Attempts to find the optimal move using MCTS.
        """
        if not self.enabled: return None
        
        # Trigger Condition: Run always for data collection
        if len(ctx.hand) == 0:
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
            # Calculate Adaptive Budget
            budget = self._calculate_budget(ctx)
            
            # 3. Execution (The Oracle)
            best_idx, details = self.solver.search_with_details(
                fast_game, 
                timeout_ms=500, # Increased timeout
                max_iterations=budget
            )
            
            # DATASET LOGGING (Neural Net Training)
            try:
                if self.dataset_logger:
                    self.dataset_logger.log_sample(ctx, best_idx, details)
            except: 
                pass
            
            return {
                "cardIndex": best_idx,
                "reasoning": f"Oracle (MCTS) - Budget {budget} - Verified {len(ctx.hand)} cards"
            }
            
        except Exception as e:
            logger.error(f"Cognitive Engine Failed: {e}", exc_info=False)
            # Ideally minimal logging to avoid spam in production, or verbose if debugging.
            return None

    def _calculate_budget(self, ctx: BotContext) -> int:
        """
        Dynamic Difficulty Adjustment (DDA).
        Adjusts simulation budget based on score difference.
        """
        base_budget = 2000
        
        # Get scores
        scores = ctx.raw_state.get('matchScores', {'us': 0, 'them': 0})
        us_score = scores.get('us', 0)
        them_score = scores.get('them', 0)
        
        diff = us_score - them_score
        
        # MERCY RULE: If we are winning big, play dumb.
        if diff > 50:
            return 500
            
        # PANIC RULE: If we are losing big, try harder.
        if diff < -50:
            return 5000
            
        return base_budget

    def analyze_position(self, ctx: BotContext) -> dict:
        """
        Returns detailed analysis of the current position using MCTS.
        Returns dict with keys: 'best_move', 'move_values' (dict of move_idx -> stats).
        """
        if not self.enabled: return None
        
        try:
            # 1. Probabilistic Inference
            hands = generate_random_distribution(ctx)
            
            # 2. Simulation Environment Setup
            fast_game = FastGame(
                players_hands=hands,
                trump=ctx.trump,
                mode=ctx.mode,
                current_turn=0,
                dealer_index=ctx.raw_state.get('dealerIndex', 0),
                table_cards=ctx.raw_state.get('tableCards', [])
            )
            
            # 3. Execution
            best_idx, details = self.solver.search_with_details(fast_game, timeout_ms=300)
            
            return {
                "best_move": best_idx,
                "move_values": details
            }
            
        except Exception as e:
            logger.error(f"Cognitive Analysis Failed: {e}", exc_info=False)
            return None
