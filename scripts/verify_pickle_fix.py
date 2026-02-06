
import sys
import os
import pickle
import asyncio
# Mock socketio if imported by game modules
from unittest.mock import MagicMock
sys.modules['socketio'] = MagicMock()

# Ensure we can import from root
sys.path.append(os.getcwd())

from game_engine.logic.game import Game

async def test_pickle():
    print("Creating game...")
    game = Game("test_pickle_room")
    
    print("Adding players...")
    game.add_player("p1", "Player1")
    game.add_player("p2", "Player2")
    game.add_player("p3", "Player3")
    game.add_player("p4", "Player4")
    
    print("Starting game...")
    game.start_game()
    
    print(f"Current Phase: {game.phase}")
    
    print("Attempting pickle...")
    try:
        data = pickle.dumps(game)
        print(f"Pickle successful! Size: {len(data)} bytes")
        
        print("Attempting unpickle...")
        loaded_game = pickle.loads(data)
        print("Unpickle successful!")
        print(f"Loaded Room ID: {loaded_game.room_id}")
        
        # Verify excluded fields were re-initialized or handled
        if hasattr(loaded_game, 'timer_manager'):
             print(f"TimerManager present: {loaded_game.timer_manager is not None}")
        
        if hasattr(loaded_game, '_sherlock_lock'):
             print(f"Sherlock Lock present: {loaded_game._sherlock_lock}")
             
    except Exception as e:
        print(f"PICKLE FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pickle())
