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

def test_ledger_prevents_reaccusation(mock_game):
    engine = QaydEngine(mock_game)
    
    # 1. Pre-populate ledger with a resolved crime
    mock_game.state.resolved_crimes.append("0_2")
    
    # 2. Mock a trick that contains that SAME crime
    # Bot auto-accuse should find it, then Reject it
    
    # Mock card with 'is_illegal' flag
    mock_card = {'suit': 'S', 'rank': 'A'}
    mock_meta = {'is_illegal': True}
    
    # Place card in table_cards (current trick, index 0 in history if empty history? No, trick_idx=len)
    mock_game.round_history = [] # So trick_idx = 0
    mock_game.table_cards = [{'card': mock_card, 'playedBy': 'Bottom', 'metadata': mock_meta}]
    
    # Only 3 cards played, this is card 2 (index 2)
    # Wait, my logic says card_idx is index in table_cards.
    # So if I want to match "0_2", I need it to be at index 2.
    mock_game.table_cards = [{}, {}, {'card': mock_card, 'playedBy': 'Bottom', 'metadata': mock_meta}]
    
    # Act
    result = engine._bot_auto_accuse(0)
    
    # Assert
    assert result['success'] is False
    assert result['error'] == 'Double Jeopardy (Ledger)'
    assert not engine.state['active']
