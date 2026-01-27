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
        mock_game.get_game_state.return_value = {'state': 'mock', 'currentTurnIndex': 0}

        # Test
        result = self.socket_handler.game_action(sid, action_data)

        # Assert
        mock_game.handle_bid.assert_called_with(0, 'SUN', None)
        self.mock_sio.emit.assert_called_with('game_update', {'gameState': {'state': 'mock', 'currentTurnIndex': 0}}, room=room_id)
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
        mock_game.get_game_state.return_value = {'state': 'mock', 'currentTurnIndex': 0}

        # Test
        result = self.socket_handler.game_action(sid, action_data)

        # Assert
        mock_game.play_card.assert_called_with(0, 2, None)
        self.assertTrue(result['success'])

if __name__ == '__main__':
    unittest.main()
