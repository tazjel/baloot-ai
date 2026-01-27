
import pytest
from unittest.mock import MagicMock, patch
from ai_worker.memory_hall import MemoryHall
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_redis():
    with patch('ai_worker.memory_hall.redis') as mock_redis_lib:
        mock_client = MagicMock()
        mock_redis_lib.from_url.return_value = mock_client
        yield mock_client

def test_remember_match(mock_redis):
    hall = MemoryHall()
    hall.redis_client = mock_redis
    
    user_id = "user_123"
    match_data = {
        'winner': 'us',
        'my_partner': 'Khalid',
        'opponents': ['Saad', 'Fahad'],
        'score_us': 152,
        'score_them': 100
    }
    
    hall.remember_match(user_id, "TestUser", match_data)
    
    # Check HINCRBY calls
    # 1. games_played
    mock_redis.hincrby.assert_any_call(f"rivalry:{user_id}", "games_played", 1)
    # 2. wins_vs_ai
    mock_redis.hincrby.assert_any_call(f"rivalry:{user_id}", "wins_vs_ai", 1)
    
    # 3. Relationships
    rel_key = f"rivalry:{user_id}:relationships"
    mock_redis.hincrby.assert_any_call(rel_key, "Khalid:won_with", 1)
    mock_redis.hincrby.assert_any_call(rel_key, "Saad:won_against", 1)
    mock_redis.hincrby.assert_any_call(rel_key, "Fahad:won_against", 1)

def test_get_rivalry_summary(mock_redis):
    hall = MemoryHall()
    hall.redis_client = mock_redis
    
    user_id = "user_123"
    
    # Mock Redis Return Values
    mock_redis.hgetall.side_effect = [
        # First call: rivalry:{user_id}
        {
            'games_played': '10',
            'wins_vs_ai': '6',
            'losses_vs_ai': '4'
        },
        # Second call: rivalry:{user_id}:relationships
        {
           'Saad:lost_to': '3',
           'Fahad:lost_to': '1',
           'Khalid:won_with': '5'
        }
    ]
    
    summary = hall.get_rivalry_summary(user_id)
    
    assert summary['status'] == 'regular'
    assert summary['games_played'] == 10
    assert summary['win_rate'] == 60.0
    assert summary['nemesis'] == 'Saad' # 3 losses
    assert summary['total_wins'] == 6
