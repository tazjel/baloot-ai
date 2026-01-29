
import os
import shutil
import logging
import sys

# Fix Path
sys.path.append(os.getcwd())

from ai_worker.learning.dataset_logger import DatasetLogger
from ai_worker.bot_context import BotContext

def verify_yolo():
    print("--- Verifying YOLO Logger ---")
    data_dir = "ai_worker/data/test_yolo"
    
    # Clean up previous run
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    
    # 1. Init Logger (Low buffer for testing)
    logger = DatasetLogger(data_dir=data_dir, min_confidence=0.80, buffer_size=2)
    print(f"Logger initialized in {data_dir}")
    
    # 2. Mock Context (Minimal)
    class MockCard:
        def __init__(self, suit, rank):
            self.suit = suit
            self.rank = rank
        def __str__(self): return f"{self.suit}{self.rank}"
        
    class MockContext:
        def __init__(self):
            self.mode = "SUN"
            # Use 'S' for Spades etc? FeatureExtractor usually handles standard constants.
            # Let's assume constants match.
            self.hand = [MockCard("♠", "7"), MockCard("♥", "A"), MockCard("♦", "10")]
            self.raw_state = {"gameId": "test_game_123"}
            self.trump = None
            self.lead_suit = None
            self.table_cards = []
            
            # Mock Memory for extractor dependency?
            self.memory = type('obj', (object,), {'discards': {}, 'played_cards': []})
            
    ctx = MockContext()
    
    # 3. Test: Low Confidence (Should NOT log)
    print("Test 1: Low Confidence Move (0.50)")
    details_low = {0: {'win_rate': 0.50, 'visits': 100}}
    logger.log_sample(ctx, 0, details_low)
    
    # Check buffer (Should be empty)
    if len(logger.buffer) != 0:
        print(f"FAIL: Buffer should be empty, has {len(logger.buffer)}")
        return
        
    # 4. Test: High Confidence (Should log)
    print("Test 2: High Confidence Move (0.90)")
    details_high = {1: {'win_rate': 0.90, 'visits': 1000}}
    logger.log_sample(ctx, 1, details_high)
    
    if len(logger.buffer) != 1:
        print(f"FAIL: Buffer should have 1 item, has {len(logger.buffer)}")
        return
        
    # 5. Test: Flush
    print("Test 3: Buffer Flush (adding 2nd item)")
    # Must use index 2 in details, or reuse index 1 in call?
    # Let's add key 2 to details dict or separate details
    details_flush = {2: {'win_rate': 0.95, 'visits': 1200}}
    logger.log_sample(ctx, 2, details_flush) # Buffer size is 2, should flush now
    
    if len(logger.buffer) != 0:
        print(f"FAIL: Buffer should be empty after flush, has {len(logger.buffer)}")
        return
        
    # 6. Verify File
    file_path = os.path.join(data_dir, "yolo_dataset.jsonl")
    if not os.path.exists(file_path):
        print("FAIL: Output file not created")
        return
        
    with open(file_path, 'r') as f:
        lines = f.readlines()
        print(f"Success! File created with {len(lines)} records.")
        print("Sample Record:", lines[0].strip())
        
    print("--- VERIFICATION PASSED ✅ ---")

if __name__ == "__main__":
    verify_yolo()
