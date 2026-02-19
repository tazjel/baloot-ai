import unittest
from unittest.mock import MagicMock
import sys

# 1. Setup mocks before importing the module under test
mock_action = MagicMock()
mock_request = MagicMock()
mock_response = MagicMock()
mock_db = MagicMock()

# Mock action.uses and action itself to be no-ops
mock_action.uses.side_effect = lambda *args: lambda f: f
mock_action.side_effect = lambda *args, **kwargs: lambda f: f

# Mock py4web module
sys.modules['py4web'] = MagicMock(
    action=mock_action, 
    request=mock_request, 
    response=mock_response
)

# Mock server.common module
mock_common = MagicMock()
mock_common.db = mock_db
sys.modules['server.common'] = mock_common

# 2. Now import the functions to test
from server.routes.stats import get_player_stats, get_leaderboard, record_game_result

class TestStatsAPI(unittest.TestCase):
    def setUp(self):
        # Reset mocks before each test
        mock_db.reset_mock()
        mock_db.return_value.select.side_effect = None
        mock_db.return_value.select.return_value = MagicMock()
        
        mock_request.reset_mock()
        mock_request.json = {}
        
        mock_response.reset_mock()
        mock_response.status = 200

    def test_get_player_stats_not_found(self):
        """1. get_player_stats returns 404 for unknown email"""
        # db(query).select().first() -> None
        mock_db.return_value.select.return_value.first.return_value = None
        
        result = get_player_stats("unknown@example.com")
        self.assertEqual(mock_response.status, 404)
        self.assertEqual(result, {"error": "User not found"})

    def test_get_player_stats_success(self):
        """2. get_player_stats returns correct stats for known player"""
        user = MagicMock()
        user.email = "test@example.com"
        user.first_name = "John"
        user.last_name = "Doe"
        user.league_points = 1200
        
        game1 = MagicMock(is_win=True)
        game2 = MagicMock(is_win=True)
        game3 = MagicMock(is_win=False)
        
        # 1st select() is for user, 2nd is for games
        mock_user_select = MagicMock()
        mock_user_select.first.return_value = user
        
        mock_db.return_value.select.side_effect = [
            mock_user_select,
            [game1, game2, game3]
        ]
        
        result = get_player_stats("test@example.com")
        self.assertEqual(result["email"], "test@example.com")
        self.assertEqual(result["gamesPlayed"], 3)
        self.assertEqual(result["wins"], 2)
        self.assertEqual(result["losses"], 1)
        self.assertAlmostEqual(result["winRate"], (2/3)*100)
        self.assertEqual(result["leaguePoints"], 1200)

    def test_get_player_stats_new_player(self):
        """3. get_player_stats returns 0 games for new player"""
        user = MagicMock()
        user.email = "new@example.com"
        user.first_name = "New"
        user.last_name = "Player"
        user.league_points = 1000
        
        mock_user_select = MagicMock()
        mock_user_select.first.return_value = user
        
        mock_db.return_value.select.side_effect = [
            mock_user_select,
            []
        ]
        
        result = get_player_stats("new@example.com")
        self.assertEqual(result["gamesPlayed"], 0)
        self.assertEqual(result["winRate"], 0)

    def test_get_leaderboard_sorted(self):
        """4. get_leaderboard returns sorted list"""
        user1 = MagicMock(first_name="A", last_name="B", league_points=2000)
        user2 = MagicMock(first_name="C", last_name="D", league_points=1500)
        mock_db.return_value.select.return_value = [user1, user2]
        
        result = get_leaderboard()
        self.assertEqual(len(result["leaderboard"]), 2)
        self.assertEqual(result["leaderboard"][0]["rank"], 1)
        self.assertEqual(result["leaderboard"][0]["leaguePoints"], 2000)
        self.assertEqual(result["leaderboard"][1]["rank"], 2)
        self.assertEqual(result["leaderboard"][1]["leaguePoints"], 1500)

    def test_get_leaderboard_max_50(self):
        """5. get_leaderboard returns max 50 entries"""
        mock_db.return_value.select.return_value = [MagicMock()] * 50
        get_leaderboard()
        # Verify limitby=(0, 50) was passed
        kwargs = mock_db.return_value.select.call_args.kwargs
        self.assertEqual(kwargs['limitby'], (0, 50))

    def test_record_game_result_missing_email(self):
        """6. record_game_result returns 400 when email missing"""
        mock_request.json = {"scoreUs": 100, "scoreThem": 50, "isWin": True}
        result = record_game_result()
        self.assertEqual(mock_response.status, 400)
        self.assertEqual(result, {"error": "Email is required"})

    def test_record_game_result_creates_row(self):
        """7. record_game_result creates game_result row"""
        mock_request.json = {
            "email": "test@example.com",
            "scoreUs": 100,
            "scoreThem": 50,
            "isWin": True
        }
        # Mock user not found for update to avoid more DB calls if we wanted, 
        # but we just care about insert here.
        mock_db.return_value.select.return_value.first.return_value = None
        
        record_game_result()
        mock_db.game_result.insert.assert_called_once_with(
            user_email="test@example.com",
            score_us=100,
            score_them=50,
            is_win=True
        )

    def test_record_game_result_updates_points_win(self):
        """8. record_game_result updates league_points +25 on win"""
        mock_request.json = {
            "email": "test@example.com",
            "scoreUs": 100,
            "scoreThem": 50,
            "isWin": True
        }
        user = MagicMock()
        user.league_points = 1000
        mock_db.return_value.select.return_value.first.return_value = user
        
        record_game_result()
        user.update_record.assert_called_once_with(league_points=1025)

    def test_record_game_result_updates_points_loss(self):
        """9. record_game_result updates league_points -15 on loss"""
        mock_request.json = {
            "email": "test@example.com",
            "scoreUs": 50,
            "scoreThem": 100,
            "isWin": False
        }
        user = MagicMock()
        user.league_points = 1000
        mock_db.return_value.select.return_value.first.return_value = user
        
        record_game_result()
        user.update_record.assert_called_once_with(league_points=985)

    def test_record_game_result_min_zero_points(self):
        """10. record_game_result never lets points go below 0"""
        mock_request.json = {
            "email": "test@example.com",
            "scoreUs": 50,
            "scoreThem": 100,
            "isWin": False
        }
        user = MagicMock()
        user.league_points = 10
        mock_db.return_value.select.return_value.first.return_value = user
        
        record_game_result()
        user.update_record.assert_called_once_with(league_points=0)

if __name__ == '__main__':
    unittest.main()
