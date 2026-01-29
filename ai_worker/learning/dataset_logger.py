
import logging
import os
import json
import time
from typing import List, Dict
from ai_worker.bot_context import BotContext
from ai_worker.learning.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

class DatasetLogger:
    """
    Logs game states and MCTS decisions to a JSONL dataset.
    Features:
    - Buffering (flush every N records)
    - Thresholding (only log high-confidence moves)
    - JSONL format (efficient for ML)
    """
    def __init__(self, data_dir="ai_worker/data/training", min_confidence=0.95, buffer_size=50):
        self.data_dir = data_dir
        self.file_path = os.path.join(data_dir, "yolo_dataset.jsonl")
        self.extractor = FeatureExtractor()
        
        self.min_confidence = min_confidence
        self.buffer_size = buffer_size
        self.buffer = []
        
        # Ensure dir exists
        os.makedirs(data_dir, exist_ok=True)

    def log_sample(self, ctx: BotContext, mcts_move_idx: int, details: Dict):
        """
        Logs a single training sample if it meets criteria.
        mcts_move_idx: Index in HAND (0..N).
        """
        try:
            # 1. Check Confidence Threshold
            move_stats = details.get(mcts_move_idx, {})
            # Use 'win_rate' or visit count ratio as confidence?
            # Win rate is better for 'correctness', visit ratio for 'certainty'.
            # MCTS details usually has: {'visits': N, 'wins': M, 'win_rate': 0.X}
            
            # Let's use visit_ratio if available, else win_rate?
            # Actually, standard MCTS: visits = confidence.
            # But details here might just be win_rate derived.
            # Let's assume 'win_rate' is the Q-value.
            
            # If win_rate > threshold (e.g. 0.95), it's a "forced/obvious" move.
            win_rate = move_stats.get('win_rate', 0.0)
            visits = move_stats.get('visits', 0)
            
            if win_rate < self.min_confidence:
                return # Skip low confidence moves

            # 2. Extract Features
            vector = self.extractor.encode(ctx)
            # JSON-serializable list
            vector_list = [round(v, 4) for v in vector]
            
            # 3. Target info
            target_card = ctx.hand[mcts_move_idx] if mcts_move_idx < len(ctx.hand) else None
            # target_str = str(target_card) if target_card else "None" # Redundant if index is reliable, but good for debug
            
            # 4. Construct Record
            record = {
                "ts": int(time.time()),
                "game_id": ctx.raw_state.get('gameId', 'unknown'),
                "mode": ctx.mode,
                "vector": vector_list,
                "target_idx": mcts_move_idx,
                "target_card": str(target_card),
                "confidence": win_rate,
                "visits": visits
            }
            
            # 5. Buffer & Flush
            self.buffer.append(record)
            if len(self.buffer) >= self.buffer_size:
                self.flush()
                
        except Exception as e:
            logger.error(f"Dataset Logging Error: {e}", exc_info=False)
            pass

    def flush(self):
        """Writes buffer to disk."""
        if not self.buffer: return
        
        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                for record in self.buffer:
                    f.write(json.dumps(record) + '\n')
            
            self.buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush Yolo Buffer: {e}")
