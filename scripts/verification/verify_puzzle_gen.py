
import sys
import os
import shutil
import json
import logging

# Fix Path
sys.path.append(os.getcwd())

from ai_worker.learning.puzzle_generator import PuzzleGenerator
from game_engine.models.card import Card

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyPuzzle")

def verify_puzzle_gen():
    print("--- Verifying Puzzle Generator ---")
    
    # 1. Setup Test Dir
    test_dir = "server/content/puzzles_test"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    pgen = PuzzleGenerator(puzzle_dir=test_dir)
    print(f"Generator initialized in {test_dir}")
    
    # 2. Mock Context
    class MockContext:
        def __init__(self):
            self.mode = "SUN"
            self.player_index = 0
            self.raw_state = {
                "gameId": "test_game_XYZ",
                "roundHistory": [],
                "players": [
                    {"name": "Me", "index": 0, "hand": ["S7", "HA"]}, # Should effectively remain
                    {"name": "Right", "index": 1, "hand": ["D10"]}, # Should be cleared
                    {"name": "Partner", "index": 2, "hand": ["CK"]}, # Should be cleared
                    {"name": "Left", "index": 3, "hand": ["SQ"]} # Should be cleared
                ]
            }
            
    ctx = MockContext()
    human_card = Card("S", "7")
    best_card = Card("H", "A")
    analysis = {"best_move": 1, "move_values": {}}
    
    # 3. Generate
    print("Generating Puzzle...")
    success = pgen.create_from_blunder(ctx, human_card, best_card, analysis)
    
    if not success:
        print("FAIL: create_from_blunder returned False")
        exit(1)
        
    # 4. Verify File
    files = os.listdir(test_dir)
    if not files:
        print("FAIL: No puzzle file created")
        exit(1)
        
    fpath = os.path.join(test_dir, files[0])
    print(f"Puzzle file found: {fpath}")
    
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # 5. Validate Content
    print("Validating content...")
    
    # Check ID
    if not data['id'].startswith('exam_'):
        print(f"FAIL: ID format wrong: {data['id']}")
        exit(1)

    # Check Solution
    sol_data = data['solution']['data']
    if sol_data != ["AH"]: # Card("H", "A") -> "AH"
        print(f"FAIL: Solution mismatch. Expected ['AH'], got {sol_data}")
        exit(1)
        
    # Check Hand Sanitization
    initial_players = data['initial_state']['players']
    me = initial_players[0]
    right = initial_players[1]
    
    if not me['hand']:
        print("FAIL: 'Me' hand shouldn't be empty")
        exit(1)
        
    if right['hand']:
        print(f"FAIL: 'Right' hand should be empty (Sanitized). Got: {right['hand']}")
        exit(1)
        
    print("--- VERIFICATION PASSED ✅ ---")

if __name__ == "__main__":
    verify_puzzle_gen()
