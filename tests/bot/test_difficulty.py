from __future__ import annotations

import unittest
from unittest.mock import patch

from ai_worker.strategies.difficulty import (
    DifficultyLevel,
    get_difficulty_config,
    apply_difficulty_to_play,
    apply_difficulty_to_bid,
    should_use_endgame,
    should_use_brain,
    should_use_kaboot,
    get_bid_noise,
    get_forget_rate,
)
from ai_worker.bot_context import BotContext


def _make_game_state(player_index=0):
    """Build minimal game_state dict for BotContext."""
    return {
        'players': [
            {
                'hand': [{'suit': '♠', 'rank': 'A'}, {'suit': '♥', 'rank': 'K'}],
                'position': 'Bottom',
                'name': 'Test',
                'team': 'us',
                'avatar': 'bot_1'
            }
            for _ in range(4)
        ],
        'phase': 'PLAYING',
        'gameMode': 'SUN',
        'trumpSuit': None,
        'dealerIndex': 0,
        'biddingRound': 1,
        'tableCards': [],
        'currentTurn': player_index,
        'teamScores': {'us': 0, 'them': 0},
        'matchScores': {'us': 0, 'them': 0},
        'trickHistory': [],
        'bid': {},
        'bidHistory': [],
    }


class TestDifficultyLevel(unittest.TestCase):
    """Test DifficultyLevel enum."""

    def test_enum_values(self):
        """Test enum values are correct."""
        self.assertEqual(DifficultyLevel.EASY.value, 1)
        self.assertEqual(DifficultyLevel.MEDIUM.value, 2)
        self.assertEqual(DifficultyLevel.HARD.value, 3)
        self.assertEqual(DifficultyLevel.KHALID.value, 4)

    def test_ordering(self):
        """Test difficulty levels can be ordered."""
        self.assertLess(DifficultyLevel.EASY, DifficultyLevel.MEDIUM)
        self.assertLess(DifficultyLevel.MEDIUM, DifficultyLevel.HARD)
        self.assertLess(DifficultyLevel.HARD, DifficultyLevel.KHALID)


class TestDifficultyConfig(unittest.TestCase):
    """Test get_difficulty_config()."""

    def test_easy_config(self):
        """Test EASY config has high forget/random rates, no brain."""
        config = get_difficulty_config(DifficultyLevel.EASY)
        self.assertEqual(config['forget_rate'], 0.40)
        self.assertEqual(config['random_play_rate'], 0.15)
        self.assertEqual(config['random_bid_rate'], 0.10)
        self.assertFalse(config['use_brain'])
        self.assertFalse(config['use_endgame'])
        self.assertFalse(config['use_kaboot'])

    def test_medium_config(self):
        """Test MEDIUM config has moderate rates."""
        config = get_difficulty_config(DifficultyLevel.MEDIUM)
        self.assertEqual(config['forget_rate'], 0.10)
        self.assertEqual(config['random_play_rate'], 0.08)
        self.assertEqual(config['random_bid_rate'], 0.05)
        self.assertTrue(config['use_brain'])
        self.assertFalse(config['use_endgame'])
        self.assertFalse(config['use_kaboot'])

    def test_hard_config(self):
        """Test HARD config has zero forget/random rates, uses all features."""
        config = get_difficulty_config(DifficultyLevel.HARD)
        self.assertEqual(config['forget_rate'], 0.0)
        self.assertEqual(config['random_play_rate'], 0.0)
        self.assertTrue(config['use_brain'])
        self.assertTrue(config['use_endgame'])
        self.assertTrue(config['use_kaboot'])

    def test_khalid_config(self):
        """Test KHALID config is same as HARD."""
        config = get_difficulty_config(DifficultyLevel.KHALID)
        self.assertEqual(config['forget_rate'], 0.0)
        self.assertEqual(config['random_play_rate'], 0.0)
        self.assertTrue(config['use_brain'])
        self.assertTrue(config['use_endgame'])
        self.assertTrue(config['use_kaboot'])

    def test_all_configs_have_required_keys(self):
        """Test all configs have expected keys."""
        required_keys = {
            'forget_rate', 'random_play_rate', 'use_brain',
            'use_endgame', 'use_kaboot', 'bid_score_noise', 'random_bid_rate'
        }
        for level in DifficultyLevel:
            with self.subTest(level=level):
                config = get_difficulty_config(level)
                self.assertTrue(required_keys.issubset(config.keys()))


class TestApplyDifficultyToPlay(unittest.TestCase):
    """Test apply_difficulty_to_play()."""

    def test_hard_never_changes_decision(self):
        """Test HARD level never changes decision (random_play_rate=0)."""
        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = [0, 1, 2]

        result = apply_difficulty_to_play(decision, DifficultyLevel.HARD, legal_indices)
        self.assertEqual(result, decision)

    def test_returns_original_for_non_play_actions(self):
        """Test returns original for non-PLAY actions."""
        decision = {'action': 'BID', 'bid': 'SUN'}
        legal_indices = [0, 1]

        result = apply_difficulty_to_play(decision, DifficultyLevel.EASY, legal_indices)
        self.assertEqual(result, decision)

    def test_returns_original_when_empty_legal_indices(self):
        """Test returns original when legal_indices is empty."""
        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = []

        result = apply_difficulty_to_play(decision, DifficultyLevel.EASY, legal_indices)
        self.assertEqual(result, decision)

    @patch('ai_worker.strategies.difficulty.random.random')
    def test_easy_sometimes_changes_card(self, mock_random):
        """Test EASY level sometimes changes card."""
        mock_random.return_value = 0.05  # Below 0.15 threshold

        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = [0, 1, 2]

        result = apply_difficulty_to_play(decision, DifficultyLevel.EASY, legal_indices)
        self.assertEqual(result['action'], 'PLAY')
        self.assertIn(result['cardIndex'], legal_indices)

    @patch('ai_worker.strategies.difficulty.random.random')
    def test_easy_no_change_when_above_threshold(self, mock_random):
        """Test EASY doesn't change card when random value above threshold."""
        mock_random.return_value = 0.99  # Above 0.15 threshold

        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = [0, 1, 2]

        result = apply_difficulty_to_play(decision, DifficultyLevel.EASY, legal_indices)
        self.assertEqual(result, decision)


class TestApplyDifficultyToBid(unittest.TestCase):
    """Test apply_difficulty_to_bid()."""

    def test_hard_never_downgrades(self):
        """Test HARD level never downgrades bid."""
        decision = {'action': 'SUN', 'reasoning': 'Good hand'}
        result = apply_difficulty_to_bid(decision, DifficultyLevel.HARD)
        self.assertEqual(result, decision)

    def test_pass_never_upgraded(self):
        """Test PASS is never upgraded (important invariant)."""
        for level in DifficultyLevel:
            with self.subTest(level=level):
                decision = {'action': 'PASS', 'reasoning': 'Bad hand'}
                result = apply_difficulty_to_bid(decision, level)
                self.assertEqual(result['action'], 'PASS')

    @patch('ai_worker.strategies.difficulty.random.random')
    def test_easy_sometimes_downgrades_to_pass(self, mock_random):
        """Test EASY level sometimes downgrades bid to PASS."""
        mock_random.return_value = 0.05  # Below threshold

        decision = {'action': 'SUN', 'reasoning': 'Good hand'}
        result = apply_difficulty_to_bid(decision, DifficultyLevel.EASY)
        # Should downgrade to PASS
        self.assertEqual(result['action'], 'PASS')

    @patch('ai_worker.strategies.difficulty.random.random')
    def test_easy_no_downgrade_above_threshold(self, mock_random):
        """Test EASY doesn't downgrade when random value high."""
        mock_random.return_value = 0.99  # High value

        decision = {'action': 'SUN', 'reasoning': 'Good hand'}
        result = apply_difficulty_to_bid(decision, DifficultyLevel.EASY)
        self.assertEqual(result, decision)


class TestHelperFunctions(unittest.TestCase):
    """Test difficulty helper functions."""

    def test_should_use_endgame(self):
        """Test should_use_endgame for each level."""
        self.assertFalse(should_use_endgame(DifficultyLevel.EASY))
        self.assertFalse(should_use_endgame(DifficultyLevel.MEDIUM))
        self.assertTrue(should_use_endgame(DifficultyLevel.HARD))
        self.assertTrue(should_use_endgame(DifficultyLevel.KHALID))

    def test_should_use_brain(self):
        """Test should_use_brain for each level."""
        self.assertFalse(should_use_brain(DifficultyLevel.EASY))
        self.assertTrue(should_use_brain(DifficultyLevel.MEDIUM))
        self.assertTrue(should_use_brain(DifficultyLevel.HARD))
        self.assertTrue(should_use_brain(DifficultyLevel.KHALID))

    def test_should_use_kaboot(self):
        """Test should_use_kaboot for each level."""
        self.assertFalse(should_use_kaboot(DifficultyLevel.EASY))
        self.assertFalse(should_use_kaboot(DifficultyLevel.MEDIUM))
        self.assertTrue(should_use_kaboot(DifficultyLevel.HARD))
        self.assertTrue(should_use_kaboot(DifficultyLevel.KHALID))

    def test_get_bid_noise(self):
        """Test get_bid_noise returns correct values."""
        # HARD should have zero noise
        for _ in range(5):
            easy_noise = get_bid_noise(DifficultyLevel.EASY)
            self.assertIsInstance(easy_noise, int)
            self.assertGreaterEqual(easy_noise, -4)
            self.assertLessEqual(easy_noise, 4)

        for _ in range(5):
            medium_noise = get_bid_noise(DifficultyLevel.MEDIUM)
            self.assertIsInstance(medium_noise, int)
            self.assertGreaterEqual(medium_noise, -2)
            self.assertLessEqual(medium_noise, 2)

        hard_noise = get_bid_noise(DifficultyLevel.HARD)
        self.assertEqual(hard_noise, 0)

        khalid_noise = get_bid_noise(DifficultyLevel.KHALID)
        self.assertEqual(khalid_noise, 0)

    def test_get_forget_rate(self):
        """Test get_forget_rate returns correct values."""
        self.assertEqual(get_forget_rate(DifficultyLevel.EASY), 0.40)
        self.assertEqual(get_forget_rate(DifficultyLevel.MEDIUM), 0.10)
        self.assertEqual(get_forget_rate(DifficultyLevel.HARD), 0.0)
        self.assertEqual(get_forget_rate(DifficultyLevel.KHALID), 0.0)


class TestBotContextIntegration(unittest.TestCase):
    """Test BotContext accepts difficulty parameter."""

    def test_bot_context_accepts_difficulty(self):
        """Test BotContext accepts difficulty parameter."""
        game_state = _make_game_state(player_index=0)
        ctx = BotContext(
            game_state=game_state,
            player_index=0,
            difficulty=DifficultyLevel.EASY
        )
        self.assertEqual(ctx.difficulty, DifficultyLevel.EASY)

    def test_bot_context_defaults_to_hard(self):
        """Test BotContext defaults to HARD difficulty."""
        game_state = _make_game_state(player_index=0)
        ctx = BotContext(game_state=game_state, player_index=0)
        self.assertEqual(ctx.difficulty, DifficultyLevel.HARD)

    def test_bot_context_with_all_difficulty_levels(self):
        """Test BotContext works with all difficulty levels."""
        game_state = _make_game_state(player_index=0)
        for level in DifficultyLevel:
            with self.subTest(level=level):
                ctx = BotContext(
                    game_state=game_state,
                    player_index=0,
                    difficulty=level
                )
                self.assertEqual(ctx.difficulty, level)


if __name__ == '__main__':
    unittest.main()
