import pytest
from unittest.mock import MagicMock, patch, ANY
import sys
import importlib

# We do NOT patch sys.modules globally to avoid breaking other tests
# instead we will import and patch in fixtures

class TestSocketHandler:
    
    @pytest.fixture(scope="class", autouse=True)
    def module_setup(self):
        """Ensure module is loaded with mocked dependencies where strictly necessary"""
        # Patch socketio before import if strictly needed, or just allow import
        # Here we allow import, assuming socketio is installed.
        # But we patch the 'sio' object on the module after import.
        import server.socket_handler
        # We reload to ensure a fresh state if previous tests messed it up
        importlib.reload(server.socket_handler)
        
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup common mocks for all tests"""
        self.mock_sio = MagicMock()
        
        # Configure the decorator pass-through behavior on the mock
        def event_decorator(func=None, *args, **kwargs):
            if func is None:
                return lambda f: f
            return func
        self.mock_sio.event = event_decorator
        self.mock_sio.emit = MagicMock()
        self.mock_sio.enter_room = MagicMock()
        self.mock_sio.start_background_task = MagicMock()
        
        # Patch the sio instance in the module
        with patch('server.socket_handler.sio', self.mock_sio):
            # Patch room_manager
            with patch('server.socket_handler.room_manager') as mock_rm:
                self.mock_rm = mock_rm
                # Patch bot_agent to avoid importing ai_worker logic
                with patch('server.socket_handler.bot_agent') as mock_bot_agent:
                    self.mock_bot_agent = mock_bot_agent
                    yield

    def test_create_room(self):
        from server.socket_handler import create_room
        
        self.mock_rm.create_room.return_value = "ROOM_123"
        res = create_room("sid_1", {})
        
        assert res['success'] is True
        assert res['roomId'] == "ROOM_123"

    def test_join_room_success(self):
        from server.socket_handler import join_room
        
        mock_game = MagicMock()
        mock_player = MagicMock()
        mock_player.index = 0
        mock_player.to_dict.return_value = {'id': 'sid_1', 'index': 0}
        
        mock_game.add_player.return_value = mock_player
        mock_game.players = [mock_player]
        mock_game.get_game_state.return_value = {'phase': 'WAITING'}
        self.mock_rm.get_game.return_value = mock_game
        
        data = {'roomId': 'ROOM_123', 'playerName': 'TestUser'}
        
        res = join_room('sid_1', data)
        
        assert res['success'] is True
        self.mock_sio.enter_room.assert_called_with('sid_1', 'ROOM_123')
        self.mock_sio.emit.assert_called()

    def test_game_action_play(self):
        from server.socket_handler import game_action
        
        mock_game = MagicMock()
        mock_player = MagicMock()
        mock_player.id = 'sid_1'
        mock_player.index = 0
        
        # Mock finding player
        mock_game.players = [mock_player]
        
        # Mock play result
        mock_game.play_card.return_value = {'success': True}
        mock_game.get_game_state.return_value = {'phase': 'PLAYING', 'currentTurnIndex': 0}
        self.mock_rm.get_game.return_value = mock_game
        
        data = {
            'roomId': 'R1', 
            'action': 'PLAY', 
            'payload': {'cardIndex': 5}
        }
        
        res = game_action('sid_1', data)
        
        print(f"DEBUG: SIO Emit Calls: {self.mock_sio.emit.mock_calls}")
        
        assert res['success'] is True
        mock_game.play_card.assert_called_with(0, 5, None)
        
        # Verify call arguments
        # We expect ('game_update', {'gameState': ...}, room='R1')
        args, kwargs = self.mock_sio.emit.call_args
        assert args[0] == 'game_update'
        assert kwargs['room'] == 'R1'

    def test_bot_loop_safety(self):
        from server.socket_handler import bot_loop
        
        mock_game = MagicMock()
        with patch('server.socket_handler.logger') as mock_logger:
            bot_loop(mock_game, 'R1', recursion_depth=501)
            mock_logger.warning.assert_called_with("Bot Loop Safety Break (Depth 501)")
