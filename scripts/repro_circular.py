import sys
import traceback

try:
    print("Attempting to import BiddingEngine...")
    from game_engine.logic.bidding_engine import BiddingEngine
    print("Success: BiddingEngine imported.")
except ImportError:
    print("ImportError Caught!")
    traceback.print_exc()
except Exception:
    print("Other Exception Caught!")
    traceback.print_exc()
