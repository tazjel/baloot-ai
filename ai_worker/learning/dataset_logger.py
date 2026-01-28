
import logging
import os
import csv
import time
from typing import List, Dict
from ai_worker.bot_context import BotContext
from ai_worker.learning.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

class DatasetLogger:
    """
    Logs game states and MCTS decisions to a CSV dataset.
    """
    def __init__(self, data_dir="ai_worker/data/training"):
        self.data_dir = data_dir
        self.file_path = os.path.join(data_dir, "dataset.csv")
        self.extractor = FeatureExtractor()
        
        # Ensure dir exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Check/Write Header
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                header = ["timestamp", "game_id", "vector_str", "target_move_idx", "target_card_str", "win_rate"]
                writer.writerow(header)

    def log_sample(self, ctx: BotContext, mcts_move_idx: int, details: Dict):
        """
        Logs a single training sample.
        mcts_move_idx: Index in HAND (0..N).
        """
        try:
            # Get Legal Moves Mask
            # MCTS returns index in hand.
            # We assume current hand state is valid.
            
            # We want to log the vector AND the target.
            
            # 1. Encode
            # For legal mask, we need to know all legal moves.
            # Usually we don't have them easily here unless passed.
            # We can skip mask for lightweight logging or re-calc.
            # Let's pass None for legal_moves_indices for now (feature mask = 0).
            vector = self.extractor.encode(ctx)
            vector_str = ",".join(f"{v:.2f}" for v in vector)
            
            # 2. Target info
            target_card = ctx.hand[mcts_move_idx] if mcts_move_idx < len(ctx.hand) else None
            target_str = str(target_card) if target_card else "None"
            
            # Win Rate
            # details is dict: { move_idx: {wins, visits, win_rate} }
            move_stats = details.get(mcts_move_idx, {})
            win_rate = move_stats.get('win_rate', 0.0)
            
            game_id = ctx.raw_state.get('gameId', 'unknown')
            ts = int(time.time())
            
            # 3. Write
            with open(self.file_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([ts, game_id, vector_str, mcts_move_idx, target_str, f"{win_rate:.4f}"])
                
        except Exception as e:
            logger.error(f"Dataset Logging Error: {e}", exc_info=True)
            pass
