
import pytest
from unittest.mock import MagicMock, patch
from ai_worker.professor import Professor
from game_engine.models.card import Card

@pytest.fixture
def mock_game():
    game = MagicMock()
    game.players = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    return game

def test_holographic_candidates_extraction():
    """
    Verify that check_move returns 'candidates' when a blunder is detected,
    and that these candidates are correctly ranked.
    """
    prof = Professor()
    prof.enabled = True
    prof.cognitive = MagicMock()
    
    # Mock Analysis
    # Best Move: Index 0 (Win Rate 0.8)
    # Runner Up: Index 1 (Win Rate 0.7)
    # Third: Index 2 (Win Rate 0.6)
    # Bad Move (Human): Index 3 (Win Rate 0.4)
    
    mock_details = {
        0: {'win_rate': 0.8, 'visits': 100},
        1: {'win_rate': 0.7, 'visits': 50},
        2: {'win_rate': 0.6, 'visits': 30},
        3: {'win_rate': 0.4, 'visits': 20}
    }
    
    prof.cognitive.analyze_position.return_value = {
        'best_move': 0,
        'move_values': mock_details
    }
    
    # Mock Player Hand
    human_card = Card('S', '7')
    best_card = Card('S', 'A')
    other_card1 = Card('S', 'K')
    other_card2 = Card('S', 'Q')
    
    player = MagicMock()
    player.hand = [best_card, other_card1, other_card2, human_card]
    player.name = "TestPlayer"
    
    game = MagicMock()
    game.players = [player]
    game.get_game_state.return_value = {} # Mock State
    
    # Mock BotContext to avoid validation errors
    with patch('ai_worker.professor.BotContext') as MockContext:
        MockContext.return_value = MagicMock()
        
        # Test: Human plays index 3 (Bad Move)
        # Expected: Intervention with top 3 candidates (0, 1, 2)
        
        result = prof.check_move(game, 0, 3)
    
        if result is None:
            print("Set -s to see this: Result is None!")
        
        assert result is not None
        assert result['type'] == 'BLUNDER' # 0.8 - 0.4 = 0.4 diff > 0.2
    assert 'candidates' in result
    
    candidates = result['candidates']
    assert len(candidates) == 3
    
    # Check Ranking
    assert candidates[0]['rank'] == 1
    assert candidates[0]['card'] == best_card.to_dict()
    assert candidates[0]['win_rate'] == 0.8
    
    assert candidates[1]['rank'] == 2
    assert candidates[1]['card'] == other_card1.to_dict()
    assert candidates[1]['win_rate'] == 0.7
    
    assert candidates[2]['rank'] == 3
    assert candidates[2]['card'] == other_card2.to_dict()
    
def test_no_intervention_if_optimal():
    prof = Professor()
    prof.cognitive = MagicMock()
    prof.cognitive.analyze_position.return_value = {
        'best_move': 0,
        'move_values': {0: {'win_rate': 0.8, 'visits': 100}}
    }
    
    game = MagicMock()
    player = MagicMock()
    player.hand = [Card('S', 'A')]
    game.players = [player]
    
    # Human plays 0 (Best)
    result = prof.check_move(game, 0, 0)
    assert result is None
