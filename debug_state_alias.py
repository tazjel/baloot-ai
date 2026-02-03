
import sys
import os

# Add project root to path
sys.path.append('c:\\Users\\MiEXCITE\\Projects\\baloot-ai')

from game_engine.logic.game import Game
from game_engine.logic.trick_manager import TrickManager

def test_alias():
    print("Initializing Game...")
    game = Game("debug_room")
    game.start_game()
    
    print(f"Game Qayd State ID: {id(game.qayd_state)}")
    print(f"TrickManager Qayd State ID: {id(game.trick_manager.qayd_state)}")
    
    if game.qayd_state is game.trick_manager.qayd_state:
        print("✅ SUCCESS: Objects are aliased (Same Object).")
    else:
        print("❌ FAILURE: Objects are DIFFERENT (Split Brain).")
        
    # Simulate Challenge Phase trigger
    print("\nTriggering Challenge Phase...")
    game.phase = "CHALLENGE"
    
    # Simulate Divergence
    print("Modifying TrickManager state...")
    game.trick_manager.qayd_state['active'] = False
    
    print(f"Game Active: {game.qayd_state.get('active')}")
    print(f"TrickManager Active: {game.trick_manager.qayd_state.get('active')}")
    
    if game.qayd_state.get('active') == False:
        print("✅ Sync check passed.")
    else:
        print("❌ Sync check FAILED.")

if __name__ == "__main__":
    test_alias()
