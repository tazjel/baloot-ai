import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestSocketHandler(unittest.TestCase):
    def setUp(self):
        # Patch dependencies BEFORE importing socket_handler
        # This prevents side efffects or requires us to patch the module attributes after import
        self.room_manager_patcher = patch('server.socket_handler.room_manager')
        self.mock_room_manager = self.room_manager_patcher.start()
        
        self.sio_patcher = patch('server.socket_handler.sio')
        self.mock_sio = self.sio_patcher.start()

        # Import the module now
        from server import socket_handler
        self.socket_handler = socket_handler

    def get_mock_game_state(self):
        return {
            "roomId": "ROOM_123",
            "phase": "PLAYING",
            "players": [
                {
                    "id": "sid_1", "name": "TestPlayer", "avatar": "av1", "index": 0,
                    "hand": [], "score": 0, "team": "us", "position": "Bottom",
                    "isDealer": True, "actionText": "", "lastReasoning": "", "isBot": False
                }
            ],
            "tableCards": [],
            "currentTurnIndex": 0,
            "gameMode": "SUN",
            "teamScores": {"us": 0, "them": 0},
            "matchScores": {"us": 0, "them": 0},
            "analytics": {"winProbability": [], "blunders": []},
            "floorCard": None,
            "dealerIndex": 0,
            "biddingRound": 1,
            "declarations": {},
            "timer": {"remaining": 10, "duration": 30, "elapsed": 0, "active": True},
            "isProjectRevealing": False,
            "doublingLevel": 1,
            "isLocked": False,
            "dealingPhase": "FINISHED",
            "challengeActive": False,
            "timerStartTime": 0,
            "turnDuration": 30,
            "serverTime": 1000,
            "gameId": "ROOM_123",
            "settings": {}
        }


    def tearDown(self):
        self.room_manager_patcher.stop()
        self.sio_patcher.stop()

    def test_create_room(self):
        # Setup
        self.mock_room_manager.create_room.return_value = 'ROOM_123'
        
        # Test
        result = self.socket_handler.create_room('sid_1', {})
        
        # Assert
        self.mock_room_manager.create_room.assert_called_once()
        self.assertEqual(result, {'success': True, 'roomId': 'ROOM_123'})

    def test_join_room_success(self):
        # Setup
        room_id = 'ROOM_123'
        sid = 'sid_1'
        player_name = 'TestPlayer'
        
        mock_game = MagicMock()
        mock_player = MagicMock()
        mock_player.to_dict.return_value = {'name': player_name, 'index': 0}
        
        self.mock_room_manager.get_game.return_value = mock_game
        mock_game.add_player.return_value = mock_player
        mock_game.players = [mock_player] # Just one player

        # Test
        response = self.socket_handler.join_room(sid, {'roomId': room_id, 'playerName': player_name})

        # Assert
        # Assert
        print("Checking enter_room call...")
        self.mock_sio.enter_room.assert_called_with(sid, room_id)
        
        print("Checking emit call...")
        # We expect at least player_joined for the user
        # And potentially bots
        self.mock_sio.emit.assert_called() 
        self.assertTrue(response['success'])

    def test_join_room_not_found(self):
        # Setup
        self.mock_room_manager.get_game.return_value = None

        # Test
        response = self.socket_handler.join_room('sid', {'roomId': 'INVALID'})

        # Assert
        self.assertFalse(response['success'])
        self.assertEqual(response['error'], 'Room not found')

    def test_game_action_bid(self):
        # Setup
        room_id = 'ROOM_123'
        sid = 'sid_1'
        action_data = {'roomId': room_id, 'action': 'BID', 'payload': {'action': 'SUN'}}
        
        mock_game = MagicMock()
        mock_player = MagicMock()
        mock_player.id = sid
        mock_player.index = 0
        mock_game.players = [mock_player]
        self.mock_room_manager.get_game.return_value = mock_game
        
        mock_game.handle_bid.return_value = {'success': True}
        mock_game.get_game_state.return_value = self.get_mock_game_state()

        # Test
        result = self.socket_handler.game_action(sid, action_data)

        # Assert
        mock_game.handle_bid.assert_called_with(0, 'SUN', None)
        mock_game.handle_bid.assert_called_with(0, 'SUN', None)
        # Verify emit was called. Arguments are transformed by Pydantic dump so strict equality on dictionary is fragile here without replicating dump logic.
        self.mock_sio.emit.assert_called()
        args, kwargs = self.mock_sio.emit.call_args
        self.assertEqual(args[0], 'game_update')
        self.assertEqual(kwargs['room'], room_id)
        self.assertIn('gameState', args[1])
        self.assertTrue(result['success'])

    def test_game_action_play(self):
        # Setup
        room_id = 'ROOM_123'
        sid = 'sid_1'
        action_data = {'roomId': room_id, 'action': 'PLAY', 'payload': {'cardIndex': 2}}
        
        mock_game = MagicMock()
        mock_player = MagicMock()
        mock_player.id = sid
        mock_player.index = 0
        mock_game.players = [mock_player]
        self.mock_room_manager.get_game.return_value = mock_game
        
        mock_game.play_card.return_value = {'success': True}
        mock_game.get_game_state.return_value = self.get_mock_game_state()

        # Test
        result = self.socket_handler.game_action(sid, action_data)

        # Assert
        mock_game.play_card.assert_called_with(0, 2, metadata={})
        self.mock_sio.emit.assert_called()
        args, kwargs = self.mock_sio.emit.call_args
        self.assertEqual(args[0], 'game_update')

if __name__ == '__main__':
    unittest.main()
