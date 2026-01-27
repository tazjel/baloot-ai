import sys
import traceback

try:
    print("Attempting to import BiddingEngine...")
    from game_engine.logic.bidding_engine import BiddingEngine
    print("Success: BiddingEngine imported.")
    
    print("Attempting to import Game...")
    from game_engine.logic.game import Game
    print("Success: Game imported.")
except ImportError as e:
    print(f"ImportError Caught: {e}")
    print(f"Name: {e.name}")
    print(f"Path: {e.path}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Other Exception Caught: {e}")
    traceback.print_exc()
