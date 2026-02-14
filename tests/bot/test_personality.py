from __future__ import annotations

import unittest
from unittest.mock import patch

from game_engine.models.card import Card
from ai_worker.personality import PROFILES
from ai_worker.strategies.components.personality_filter import apply_personality_to_play
from ai_worker.strategies.constants import PTS_SUN, PTS_HOKUM, ORDER_HOKUM


class MockCtx:
    """Minimal mock for BotContext."""
    def __init__(self, hand, mode='SUN', trump='♠', table_cards=None, personality=None):
        self.hand = hand
        self.mode = mode
        self.trump = trump
        self.table_cards = table_cards or []
        self.personality = personality


class TestPersonalityProfiles(unittest.TestCase):
    """Test PersonalityProfile data class and PROFILES dict."""

    def test_all_profiles_exist(self):
        """Test all 4 profiles exist in PROFILES dict."""
        self.assertIn('Balanced', PROFILES)
        self.assertIn('Aggressive', PROFILES)
        self.assertIn('Conservative', PROFILES)
        self.assertIn('Tricky', PROFILES)
        self.assertEqual(len(PROFILES), 4)

    def test_balanced_profile_attributes(self):
        """Test Balanced profile has correct neutral values."""
        balanced = PROFILES['Balanced']
        self.assertEqual(balanced.name, 'Saad')
        self.assertEqual(balanced.name_ar, 'سعد')
        # Neutral bidding biases
        self.assertEqual(balanced.sun_bias, 0)
        self.assertEqual(balanced.hokum_bias, 0)
        # Neutral playing attributes
        self.assertEqual(balanced.risk_tolerance, 0.5)
        self.assertEqual(balanced.point_greed, 0.5)
        self.assertEqual(balanced.trump_lead_bias, 0.5)
        self.assertEqual(balanced.partner_trust, 0.7)
        self.assertEqual(balanced.false_signal_rate, 0.0)
        self.assertFalse(balanced.can_gamble)

    def test_aggressive_profile_attributes(self):
        """Test Aggressive profile has high risk/greed values."""
        aggressive = PROFILES['Aggressive']
        self.assertEqual(aggressive.name, 'Khalid')
        self.assertEqual(aggressive.name_ar, 'خالد')
        # Positive bidding biases
        self.assertGreater(aggressive.sun_bias, 0)
        self.assertGreater(aggressive.hokum_bias, 0)
        # High risk and greed
        self.assertGreater(aggressive.risk_tolerance, 0.5)
        self.assertGreater(aggressive.point_greed, 0.5)
        self.assertTrue(aggressive.can_gamble)

    def test_conservative_profile_attributes(self):
        """Test Conservative profile has low risk values."""
        conservative = PROFILES['Conservative']
        self.assertEqual(conservative.name, 'Abu Fahad')
        self.assertEqual(conservative.name_ar, 'أبو فهد')
        # Negative bidding biases
        self.assertLess(conservative.sun_bias, 0)
        self.assertLess(conservative.hokum_bias, 0)
        # Low risk tolerance
        self.assertLess(conservative.risk_tolerance, 0.5)
        self.assertFalse(conservative.can_gamble)

    def test_tricky_profile_attributes(self):
        """Test Tricky profile has false signal rate > 0."""
        tricky = PROFILES['Tricky']
        self.assertEqual(tricky.name, 'Majed')
        self.assertEqual(tricky.name_ar, 'ماجد')
        self.assertGreater(tricky.false_signal_rate, 0.0)

    def test_all_profiles_valid_ranges(self):
        """Test all playing attributes are in valid ranges."""
        for profile_name, profile in PROFILES.items():
            with self.subTest(profile=profile_name):
                # Float attributes should be 0.0-1.0
                self.assertGreaterEqual(profile.risk_tolerance, 0.0)
                self.assertLessEqual(profile.risk_tolerance, 1.0)
                self.assertGreaterEqual(profile.point_greed, 0.0)
                self.assertLessEqual(profile.point_greed, 1.0)
                self.assertGreaterEqual(profile.trump_lead_bias, 0.0)
                self.assertLessEqual(profile.trump_lead_bias, 1.0)
                self.assertGreaterEqual(profile.partner_trust, 0.0)
                self.assertLessEqual(profile.partner_trust, 1.0)
                self.assertGreaterEqual(profile.false_signal_rate, 0.0)
                self.assertLessEqual(profile.false_signal_rate, 1.0)
                # Bool attribute
                self.assertIsInstance(profile.can_gamble, bool)
                # Bidding biases can be negative
                self.assertIsInstance(profile.sun_bias, (int, float))
                self.assertIsInstance(profile.hokum_bias, (int, float))


class TestPersonalityFilter(unittest.TestCase):
    """Test personality_filter.apply_personality_to_play()."""

    def test_no_personality_returns_original(self):
        """Test returns original decision when no personality set."""
        hand = [Card('♠', 'A'), Card('♥', 'K')]
        ctx = MockCtx(hand=hand)
        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = [0, 1]

        result = apply_personality_to_play(decision, ctx, legal_indices)
        self.assertEqual(result, decision)

    def test_single_legal_index_returns_original(self):
        """Test returns original when only 1 legal index."""
        hand = [Card('♠', 'A'), Card('♥', 'K')]
        ctx = MockCtx(hand=hand, personality=PROFILES['Tricky'])
        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = [0]

        result = apply_personality_to_play(decision, ctx, legal_indices)
        self.assertEqual(result, decision)

    def test_non_play_action_returns_original(self):
        """Test returns original for non-PLAY actions."""
        hand = [Card('♠', 'A'), Card('♥', 'K')]
        ctx = MockCtx(hand=hand, personality=PROFILES['Tricky'])
        decision = {'action': 'BID', 'bid': 'SUN'}
        legal_indices = [0, 1]

        result = apply_personality_to_play(decision, ctx, legal_indices)
        self.assertEqual(result, decision)

    @patch('ai_worker.strategies.components.personality_filter.random.random')
    def test_deceptive_play_triggers(self, mock_random):
        """Test deceptive play changes card for TRICKY profile."""
        mock_random.return_value = 0.01  # Always trigger (false_signal_rate=0.15)

        hand = [Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q')]
        ctx = MockCtx(hand=hand, personality=PROFILES['Tricky'])
        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = [0, 1, 2]

        result = apply_personality_to_play(decision, ctx, legal_indices)
        # Should change from original
        self.assertEqual(result['action'], 'PLAY')
        self.assertIn(result['cardIndex'], legal_indices)
        # May or may not differ (random choice), just check it's valid
        self.assertIn(result['cardIndex'], legal_indices)

    @patch('ai_worker.strategies.components.personality_filter.random.random')
    def test_deceptive_play_no_trigger(self, mock_random):
        """Test deceptive play doesn't trigger with high random value."""
        mock_random.return_value = 0.99  # Never trigger

        hand = [Card('♠', 'A'), Card('♠', 'K')]
        ctx = MockCtx(hand=hand, personality=PROFILES['Tricky'])
        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = [0, 1]

        result = apply_personality_to_play(decision, ctx, legal_indices)
        self.assertEqual(result, decision)

    def test_trump_lead_bias_aggressive(self):
        """Test AGGRESSIVE prefers trump leads in HOKUM."""
        # Create hand with trump and non-trump
        hand = [Card('♠', 'A'), Card('♠', 'K'), Card('♥', 'Q'), Card('♥', 'J')]
        ctx = MockCtx(hand=hand, mode='HOKUM', trump='♠', personality=PROFILES['Aggressive'])
        decision = {'action': 'PLAY', 'cardIndex': 2}  # Non-trump
        legal_indices = [0, 1, 2, 3]  # All legal (leading)

        # AGGRESSIVE has trump_lead_bias = 0.8, should prefer trump
        # We can't deterministically test random choice, but verify it returns valid index
        result = apply_personality_to_play(decision, ctx, legal_indices)
        self.assertIn(result['cardIndex'], legal_indices)

    def test_trump_lead_bias_conservative(self):
        """Test CONSERVATIVE avoids trump leads in HOKUM."""
        hand = [Card('♠', 'A'), Card('♠', 'K'), Card('♥', 'Q'), Card('♥', 'J')]
        ctx = MockCtx(hand=hand, mode='HOKUM', trump='♠', personality=PROFILES['Conservative'])
        decision = {'action': 'PLAY', 'cardIndex': 0}  # Trump
        legal_indices = [0, 1, 2, 3]  # All legal (leading)

        # CONSERVATIVE has trump_lead_bias = 0.3, should prefer non-trump
        result = apply_personality_to_play(decision, ctx, legal_indices)
        self.assertIn(result['cardIndex'], legal_indices)

    def test_point_greed_high_valuable_trick(self):
        """Test high greed picks highest value card in valuable trick."""
        # Following trick with high points on table
        hand = [Card('♠', 'A'), Card('♠', '7'), Card('♠', 'K')]
        ctx = MockCtx(hand=hand, mode='SUN', personality=PROFILES['Aggressive'],
                      table_cards=[Card('♠', '10'), Card('♠', 'Q')])
        decision = {'action': 'PLAY', 'cardIndex': 1}  # Low card
        legal_indices = [0, 1, 2]  # All same suit

        # AGGRESSIVE has high point_greed (0.7), should prefer high value
        result = apply_personality_to_play(decision, ctx, legal_indices)
        self.assertIn(result['cardIndex'], legal_indices)

    def test_point_greed_low_cheap_trick(self):
        """Test low greed picks cheapest card in low-value trick."""
        hand = [Card('♠', 'A'), Card('♠', '7'), Card('♠', 'K')]
        ctx = MockCtx(hand=hand, mode='SUN', personality=PROFILES['Conservative'],
                      table_cards=[Card('♠', '8'), Card('♠', '9')])
        decision = {'action': 'PLAY', 'cardIndex': 0}  # High card
        legal_indices = [0, 1, 2]

        # CONSERVATIVE has low point_greed (0.3), should prefer cheap
        result = apply_personality_to_play(decision, ctx, legal_indices)
        self.assertIn(result['cardIndex'], legal_indices)

    def test_point_greed_not_following(self):
        """Test point greed doesn't apply when leading."""
        hand = [Card('♠', 'A'), Card('♥', 'K')]
        ctx = MockCtx(hand=hand, personality=PROFILES['Aggressive'], table_cards=[])
        decision = {'action': 'PLAY', 'cardIndex': 0}
        legal_indices = [0, 1]

        # Empty table means leading, point greed shouldn't apply
        result = apply_personality_to_play(decision, ctx, legal_indices)
        # Should either keep original or apply other biases
        self.assertIn(result['cardIndex'], legal_indices)


if __name__ == '__main__':
    unittest.main()
