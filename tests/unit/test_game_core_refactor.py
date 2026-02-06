import unittest
from game_engine.logic.game import Game
from game_engine.models.constants import GamePhase

class TestGameCoreRefactor(unittest.TestCase):
    def test_state_initialization(self):
        """Verify Game initializes GameState correctly"""
        game = Game("test_room_1")
        
        # Check Pydantic State existence
        self.assertIsNotNone(game.state)
        self.assertEqual(game.state.roomId, "test_room_1")
        
        # Check Legacy Mapping
        self.assertEqual(game.room_id, "test_room_1")
        self.assertEqual(game.phase, GamePhase.WAITING.value)
        
    def test_phase_property_sync(self):
        """Verify adjusting game.phase updates game.state.phase"""
        game = Game("test_room_2")
        
        # Update via legacy property
        game.phase = GamePhase.BIDDING.value
        
        # Check State
        self.assertEqual(game.state.phase, GamePhase.BIDDING.value)
        # Check Getter
        self.assertEqual(game.phase, GamePhase.BIDDING.value)
        
    def test_turn_index_sync(self):
        """Verify dealer and turn index sync"""
        game = Game("test_room_3")
        
        game.dealer_index = 2
        self.assertEqual(game.state.dealerIndex, 2)
        
        game.current_turn = 3
        self.assertEqual(game.state.currentTurnIndex, 3)

if __name__ == "__main__":
    unittest.main()
