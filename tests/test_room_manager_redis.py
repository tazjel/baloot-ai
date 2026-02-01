import unittest
from unittest.mock import MagicMock, patch
import pickle
import sys
import os

# Ensure root import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.room_manager import RoomManager
from game_engine.logic.game import Game

class TestRoomManagerRedis(unittest.TestCase):
    def setUp(self):
        # Mock Redis
        self.redis_patcher = patch('server.room_manager.redis_store')
        self.mock_redis = self.redis_patcher.start()
        
        # Reset Singleton
        RoomManager._instance = None
        self.rm = RoomManager()

    def tearDown(self):
        self.redis_patcher.stop()

    def test_save_game_redis(self):
        game = Game("ROOM_TEST")
        # Ensure ID is set
        game.room_id = "ROOM_TEST"
        
        self.rm.save_game(game)
        
        # Assert Redis setex called
        self.mock_redis.setex.assert_called()
        args, _ = self.mock_redis.setex.call_args
        self.assertEqual(args[0], "game:ROOM_TEST") # Key
        self.assertEqual(args[1], 3600) # Expiry

    def test_get_game_redis_hit(self):
        # Setup Redis Hit
        game = Game("ROOM_HIT")
        pickled_game = pickle.dumps(game)
        self.mock_redis.get.return_value = pickled_game
        
        # Action
        retrieved_game = self.rm.get_game("ROOM_HIT")
        
        # Assert
        self.assertIsNotNone(retrieved_game)
        self.assertEqual(retrieved_game.room_id, "ROOM_HIT")
        self.mock_redis.get.assert_called_with("game:ROOM_HIT")
        
    def test_get_game_redis_miss(self):
        # Setup Redis Miss
        self.mock_redis.get.return_value = None
        
        # Action
        retrieved_game = self.rm.get_game("ROOM_MISS")
        
        # Assert
        self.assertIsNone(retrieved_game)

if __name__ == '__main__':
    unittest.main()
