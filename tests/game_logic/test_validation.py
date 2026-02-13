"""
Test Move Validation
Tests for is_move_legal and get_violation_details — the pure validation logic
for Baloot card play rules: follow suit, trump, over-trump, partner winning, Closed mode.
"""
import unittest
from game_engine.models.card import Card
from game_engine.logic.validation import is_move_legal, get_violation_details


PLAYERS_TEAM_MAP = {
    'Bottom': 'us',
    'Right': 'them',
    'Top': 'us',
    'Left': 'them',
}


class TestFollowSuit(unittest.TestCase):
    """Follow-suit rule applies in both Sun and Hokum."""

    def test_must_follow_suit_when_have_it(self):
        """Playing off-suit when you hold the lead suit is illegal."""
        hand = [Card('♥', 'A'), Card('♠', 'K')]
        table = [{'card': Card('♥', '7'), 'playedBy': 'Right'}]
        # Try to play ♠K when holding ♥A — illegal
        result = is_move_legal(Card('♠', 'K'), hand, table, 'SUN', None, 'us', PLAYERS_TEAM_MAP)
        self.assertFalse(result, "Must follow suit when holding lead suit card")

    def test_following_suit_is_legal(self):
        """Playing a card of the lead suit should always be legal."""
        hand = [Card('♥', 'A'), Card('♠', 'K')]
        table = [{'card': Card('♥', '7'), 'playedBy': 'Right'}]
        result = is_move_legal(Card('♥', 'A'), hand, table, 'SUN', None, 'us', PLAYERS_TEAM_MAP)
        self.assertTrue(result)

    def test_void_in_suit_allows_anything_sun(self):
        """In Sun, if void in lead suit, any card is legal."""
        hand = [Card('♠', 'A'), Card('♦', 'K')]
        table = [{'card': Card('♥', '7'), 'playedBy': 'Right'}]
        result = is_move_legal(Card('♠', 'A'), hand, table, 'SUN', None, 'us', PLAYERS_TEAM_MAP)
        self.assertTrue(result)


class TestLeadingFreedom(unittest.TestCase):
    """Leading (empty table) should always be legal except in Closed mode."""

    def test_leading_any_card_is_legal(self):
        """With no table cards, any card can be played."""
        hand = [Card('♥', 'A'), Card('♠', 'K')]
        result = is_move_legal(Card('♥', 'A'), hand, [], 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP)
        self.assertTrue(result)

    def test_closed_mode_blocks_trump_lead(self):
        """In Closed (Magfool/Locked) Hokum, leading with trump is illegal if you have alternatives."""
        hand = [Card('♠', 'J'), Card('♥', 'A')]
        result = is_move_legal(
            Card('♠', 'J'), hand, [], 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP,
            contract_variant='CLOSED'
        )
        self.assertFalse(result, "Cannot lead trump in Closed mode when holding non-trump")

    def test_closed_mode_allows_trump_if_only_trumps(self):
        """In Closed mode, trump lead is allowed if hand is all trumps."""
        hand = [Card('♠', 'J'), Card('♠', '9')]
        result = is_move_legal(
            Card('♠', 'J'), hand, [], 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP,
            contract_variant='CLOSED'
        )
        self.assertTrue(result, "Must allow trump lead when hand is trump-only")


class TestHokumTrumpObligation(unittest.TestCase):
    """In Hokum, void in lead suit → must play trump if available."""

    def test_must_trump_when_void_and_enemy_winning(self):
        """If void in lead suit and enemy winning, must play a trump card."""
        hand = [Card('♠', '9'), Card('♦', 'K')]  # No hearts, has trump
        table = [{'card': Card('♥', 'A'), 'playedBy': 'Right'}]  # Enemy leads
        # Try to play ♦K (non-trump, non-lead) while holding trump ♠9
        result = is_move_legal(Card('♦', 'K'), hand, table, 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP)
        self.assertFalse(result, "Must play trump when void in lead suit and having trump")

    def test_trump_play_accepted_when_void(self):
        """Playing trump when void in lead suit should be legal."""
        hand = [Card('♠', '9'), Card('♦', 'K')]
        table = [{'card': Card('♥', 'A'), 'playedBy': 'Right'}]
        result = is_move_legal(Card('♠', '9'), hand, table, 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP)
        self.assertTrue(result)

    def test_no_trump_no_suit_play_anything(self):
        """If void in both lead suit AND trump, any card is legal."""
        hand = [Card('♦', 'K'), Card('♣', '7')]  # No hearts, no spades
        table = [{'card': Card('♥', 'A'), 'playedBy': 'Right'}]
        result = is_move_legal(Card('♦', 'K'), hand, table, 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP)
        self.assertTrue(result)


class TestPartnerWinning(unittest.TestCase):
    """When partner is winning the trick, player has freedom."""

    def test_partner_winning_allows_any_card(self):
        """If partner is currently winning, no trump obligation."""
        hand = [Card('♠', '9'), Card('♦', 'K')]  # Has trump
        table = [
            {'card': Card('♥', '7'), 'playedBy': 'Right'},   # Them leads
            {'card': Card('♥', 'A'), 'playedBy': 'Top'},     # Partner wins with Ace
        ]
        # We're void in hearts but partner is winning — play anything
        result = is_move_legal(Card('♦', 'K'), hand, table, 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP)
        self.assertTrue(result, "Partner winning should allow any play")


class TestOvertrumpObligation(unittest.TestCase):
    """Must over-trump when enemy has played a trump and you can beat it."""

    def test_must_overtrump_when_possible(self):
        """If enemy played trump and you can beat it, you must play a higher trump."""
        hand = [Card('♠', 'J'), Card('♠', '7')]  # Both trumps; J beats 9
        table = [
            {'card': Card('♥', 'A'), 'playedBy': 'Bottom'},  # US leads hearts
            {'card': Card('♠', '9'), 'playedBy': 'Right'},   # Enemy plays strong trump
        ]
        # Playing ♠7 (lower trump) when we have ♠J (higher) — should be illegal
        result = is_move_legal(Card('♠', '7'), hand, table, 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP)
        self.assertFalse(result, "Must overtrump when holding a higher trump")

    def test_overtrump_with_valid_card_accepted(self):
        """Playing a trump that beats the current winner should be legal."""
        hand = [Card('♠', 'J'), Card('♠', '7')]
        table = [
            {'card': Card('♥', 'A'), 'playedBy': 'Bottom'},
            {'card': Card('♠', '9'), 'playedBy': 'Right'},
        ]
        result = is_move_legal(Card('♠', 'J'), hand, table, 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP)
        self.assertTrue(result)


class TestViolationDetails(unittest.TestCase):
    """Tests for get_violation_details — same logic but with reason/proof."""

    def test_revoke_detected_with_proof(self):
        """Revoke should return proof_hint with the card that should have been played."""
        hand = [Card('♥', 'A'), Card('♠', 'K')]
        table = [{'card': Card('♥', '7'), 'playedBy': 'Right'}]
        result = get_violation_details(Card('♠', 'K'), hand, table, 'SUN', None, 'us', PLAYERS_TEAM_MAP)
        self.assertFalse(result['is_legal'])
        self.assertEqual(result['violation_type'], 'REVOKE')
        self.assertIsNotNone(result['proof_hint'])

    def test_no_trump_violation_detected(self):
        """Playing non-trump when void in suit and having trump → NO_TRUMP violation."""
        hand = [Card('♠', '9'), Card('♦', 'K')]
        table = [{'card': Card('♥', 'A'), 'playedBy': 'Right'}]
        result = get_violation_details(Card('♦', 'K'), hand, table, 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP)
        self.assertFalse(result['is_legal'])
        self.assertEqual(result['violation_type'], 'NO_TRUMP')

    def test_legal_play_returns_clean(self):
        """A legal play should return is_legal=True with no violation."""
        hand = [Card('♥', 'A'), Card('♠', 'K')]
        table = [{'card': Card('♥', '7'), 'playedBy': 'Right'}]
        result = get_violation_details(Card('♥', 'A'), hand, table, 'SUN', None, 'us', PLAYERS_TEAM_MAP)
        self.assertTrue(result['is_legal'])
        self.assertIsNone(result['violation_type'])

    def test_closed_trump_lead_violation(self):
        """Leading trump in Closed mode should produce TRUMP_IN_DOUBLE violation."""
        hand = [Card('♠', 'J'), Card('♥', 'A')]
        result = get_violation_details(
            Card('♠', 'J'), hand, [], 'HOKUM', '♠', 'us', PLAYERS_TEAM_MAP,
            contract_variant='CLOSED'
        )
        self.assertFalse(result['is_legal'])
        self.assertEqual(result['violation_type'], 'TRUMP_IN_DOUBLE')


if __name__ == '__main__':
    unittest.main()
