import pytest
from unittest.mock import MagicMock
from game_engine.logic.qayd_engine import QaydEngine, QaydStep
from game_engine.core.state import GameState

@pytest.fixture
def mock_game():
    game = MagicMock()
    game.state = GameState(roomId="test_room")
    game.players = [MagicMock(position='Bottom', team='us'), MagicMock(position='Right', team='them')]
    for i, p in enumerate(game.players):
        p.index = i
    game.round_history = []
    game.table_cards = []
    return game

def test_ledger_add_on_confirm(mock_game):
    engine = QaydEngine(mock_game)
    
    # Simulate a crime ready to confirm
    engine.state['active'] = True
    engine.state['step'] = QaydStep.RESULT
    engine.state['verdict'] = 'CORRECT'
    engine.state['loser_team'] = 'them'
    engine.state['penalty_points'] = 26
    
    # Crime signature: Trick 0, Card 2
    engine.state['crime_signature'] = (0, 2)
    
    # Act
    engine.confirm()
    
    # Assert
    assert "0_2" in mock_game.state.resolved_crimes
    assert engine.state['active'] is False


