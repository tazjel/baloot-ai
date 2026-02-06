import unittest
from unittest.mock import MagicMock
from game_engine.logic.game import Game
from game_engine.core.recorder import TimelineRecorder

class TestTimelineRecorder(unittest.TestCase):
    def test_recording(self):
        # Mock Redis
        mock_redis = MagicMock()
        
        # Patch import in game engine? 
        # Easier to manually instantiate recorder and test it in isolation
        
        recorder = TimelineRecorder(mock_redis)
        from game_engine.core.state import GameState
        state = GameState(roomId="debug_room")
        
        recorder.record_state(state, "TEST_EVENT", "Testing")
        
        # Verify Redis Call
        mock_redis.xadd.assert_called_once()
        args = mock_redis.xadd.call_args[0]
        self.assertEqual(args[0], "game:debug_room:timeline")
        self.assertEqual(args[1]['event'], "TEST_EVENT")
        
if __name__ == "__main__":
    unittest.main()
