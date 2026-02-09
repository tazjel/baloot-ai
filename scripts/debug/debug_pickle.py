import sys
import os
import pickle

# Add project root to path
sys.path.append(os.getcwd())

import inspect
from game_engine.logic.game import Game

def inspect_game(game):
    print(f"\n🔍 Inspecting Attributes for {game.__class__.__name__}...")
    print(f"📁 Source: {inspect.getfile(Game)}")
    
    # 1. Check Root Attributes (using what Pickle would see)
    if hasattr(game, "__getstate__"):
         print("   ℹ️ Using __getstate__() for inspection.")
         state_to_check = game.__getstate__()
    else:
         state_to_check = game.__dict__

    for k, v in state_to_check.items():
        try:
            pickle.dumps(v)
            # print(f"✅ {k}: OK")
        except Exception as e:
            print(f"❌ {k}: FAILED ({type(v).__name__}) -> {e}")
            
            # Recurse if it's a known complex object
            if hasattr(v, '__dict__'):
                 print(f"   🔻 Drilling down into {k}...")
                 for sub_k, sub_v in v.__dict__.items():
                      try:
                           pickle.dumps(sub_v)
                      except Exception as sub_e:
                           print(f"      ❌ {k}.{sub_k}: FAILED ({type(sub_v).__name__}) -> {sub_e}")

def main():
    print("🚀 Initializing Game...")
    room_id = "debug_room"
    game = Game(room_id)
    
    try:
        # Simulate full init
        game.reset_round_state()
        game.deal_initial_cards()
        
        pickle.dumps(game)
        print("✅ Game object is picklable!")
    except Exception as e:
        print(f"⚠️ GLOBAL PICKLE FAILED: {e}")
        inspect_game(game)

if __name__ == "__main__":
    main()
