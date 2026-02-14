"""
Test Game Lifecycle — Integration Test
A full game lifecycle: start → bid → play all 8 tricks → verify scoring.
No mocking — exercises the real Game, TrickManager, ScoringEngine pipeline end-to-end.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import GamePhase


class TestGameSetup(unittest.TestCase):
    """Tests for game initialization and setup."""

    def test_cannot_start_with_fewer_than_4_players(self):
        """Game should not start with fewer than 4 players."""
        game = Game("incomplete")
        game.add_player("p1", "Player 1")
        game.add_player("p2", "Player 2")
        result = game.start_game()
        self.assertFalse(result)

    def test_player_teams_assigned_correctly(self):
        """Players should be assigned to alternating teams."""
        game = Game("teams_test")
        game.add_player("p1", "P1")
        game.add_player("p2", "P2")
        game.add_player("p3", "P3")
        game.add_player("p4", "P4")
        self.assertEqual(game.players[0].team, 'us')
        self.assertEqual(game.players[1].team, 'them')
        self.assertEqual(game.players[2].team, 'us')
        self.assertEqual(game.players[3].team, 'them')

    def test_player_positions(self):
        """Players should have correct position labels."""
        game = Game("pos_test")
        game.add_player("p1", "P1")
        game.add_player("p2", "P2")
        game.add_player("p3", "P3")
        game.add_player("p4", "P4")
        positions = [p.position for p in game.players]
        self.assertEqual(positions, ['Bottom', 'Right', 'Top', 'Left'])

    def test_game_start_deals_initial_cards(self):
        """Starting a game should deal initial cards (5 in Baloot's 5+3 system)."""
        game = Game("deal_test")
        game.add_player("p1", "P1")
        game.add_player("p2", "P2")
        game.add_player("p3", "P3")
        game.add_player("p4", "P4")
        game.start_game()
        for p in game.players:
            self.assertGreater(len(p.hand), 0, f"{p.name} should have cards")
            self.assertLessEqual(len(p.hand), 8, f"{p.name} should have at most 8 cards")

    def test_all_dealt_cards_are_unique(self):
        """All dealt cards should be unique (no duplicates in any hand)."""
        game = Game("deck_test")
        game.add_player("p1", "P1")
        game.add_player("p2", "P2")
        game.add_player("p3", "P3")
        game.add_player("p4", "P4")
        game.start_game()

        all_cards = set()
        for p in game.players:
            for c in p.hand:
                card_id = f"{c.rank}{c.suit}"
                self.assertNotIn(card_id, all_cards, f"Duplicate card: {card_id}")
                all_cards.add(card_id)
        # All cards across all hands should be unique
        total_hand_cards = sum(len(p.hand) for p in game.players)
        self.assertEqual(len(all_cards), total_hand_cards)

    def test_game_start_enters_bidding(self):
        """Starting should set phase to BIDDING."""
        game = Game("phase_test")
        game.add_player("p1", "P1")
        game.add_player("p2", "P2")
        game.add_player("p3", "P3")
        game.add_player("p4", "P4")
        game.start_game()
        self.assertEqual(str(game.phase), GamePhase.BIDDING.value)


class TestBiddingPhase(unittest.TestCase):
    """Tests for bidding phase transitions."""

    def setUp(self):
        self.game = Game("bid_test")
        self.game.add_player("p1", "P1")
        self.game.add_player("p2", "P2")
        self.game.add_player("p3", "P3")
        self.game.add_player("p4", "P4")
        self.game.start_game()

    def test_sun_bid_transitions_to_playing(self):
        """A SUN bid should transition out of BIDDING."""
        bidder_idx = self.game.current_turn
        result = self.game.handle_bid(bidder_idx, "SUN")
        self.assertTrue(result.get('success'), f"Bid failed: {result}")
        self.assertIn(str(self.game.phase),
                      [GamePhase.PLAYING.value, GamePhase.DOUBLING.value])

    def test_all_pass_round_1_continues(self):
        """All 4 players passing in round 1 should continue to round 2."""
        for _ in range(4):
            result = self.game.handle_bid(self.game.current_turn, "PASS")
            self.assertTrue(result.get('success'), f"Pass failed: {result}")
        # After all pass Round 1, should still be in BIDDING
        self.assertEqual(str(self.game.phase), GamePhase.BIDDING.value)


class TestPlayPhase(unittest.TestCase):
    """Tests for card play and trick completion."""

    def setUp(self):
        self.game = Game("play_test")
        self.game.add_player("p1", "P1")
        self.game.add_player("p2", "P2")
        self.game.add_player("p3", "P3")
        self.game.add_player("p4", "P4")
        self.game.start_game()
        # Disable strict mode for integration tests (allows any card play)
        self.game.strictMode = False
        # Fast-forward to PLAYING
        bidder_idx = self.game.current_turn
        self.game.handle_bid(bidder_idx, "SUN")
        if str(self.game.phase) != GamePhase.PLAYING.value:
            self.game.phase = GamePhase.PLAYING.value

    def test_play_card_success(self):
        """Playing a valid card should succeed."""
        current = self.game.current_turn
        result = self.game.play_card(current, 0)
        self.assertTrue(result.get('success'), f"Play card failed: {result}")
        self.assertEqual(len(self.game.table_cards), 1)

    def test_full_trick_clears_table(self):
        """Playing 4 cards should complete a trick and clear table."""
        for _ in range(4):
            current = self.game.current_turn
            result = self.game.play_card(current, 0)
            self.assertTrue(result.get('success'), f"Play failed: {result}")
        self.assertEqual(len(self.game.table_cards), 0)
        self.assertEqual(len(self.game.round_history), 1)

    def test_full_round_ends_game(self):
        """Playing all 32 cards should end the round."""
        for trick in range(8):
            for _ in range(4):
                current = self.game.current_turn
                result = self.game.play_card(current, 0)
                self.assertTrue(result.get('success'),
                                f"Trick {trick + 1} play failed: {result}")
        self.assertIn(str(self.game.phase),
                      [GamePhase.FINISHED.value, GamePhase.GAMEOVER.value])

    def test_all_hands_empty_after_round(self):
        """After 8 tricks all players should have empty hands."""
        for _ in range(32):
            current = self.game.current_turn
            self.game.play_card(current, 0)
        for p in self.game.players:
            self.assertEqual(len(p.hand), 0, f"{p.name} should have 0 cards")


class TestScoringIntegration(unittest.TestCase):
    """Tests for end-of-round scoring integration."""

    def setUp(self):
        self.game = Game("scoring_test")
        self.game.add_player("p1", "P1")
        self.game.add_player("p2", "P2")
        self.game.add_player("p3", "P3")
        self.game.add_player("p4", "P4")
        self.game.start_game()
        # Disable strict mode for integration tests (allows any card play)
        self.game.strictMode = False
        bidder_idx = self.game.current_turn
        self.game.handle_bid(bidder_idx, "SUN")
        if str(self.game.phase) != GamePhase.PLAYING.value:
            self.game.phase = GamePhase.PLAYING.value

    def _play_full_round(self):
        for _ in range(32):
            current = self.game.current_turn
            self.game.play_card(current, 0)

    def test_round_result_recorded(self):
        """After a full round, past_round_results should have an entry."""
        self._play_full_round()
        self.assertGreater(len(self.game.past_round_results), 0)

    def test_round_result_has_team_data(self):
        """Round result should have 'us' and 'them' sections."""
        self._play_full_round()
        result = self.game.past_round_results[-1]
        self.assertIn('us', result)
        self.assertIn('them', result)

    def test_match_scores_accumulate(self):
        """Match scores should be updated after a round."""
        self._play_full_round()
        total = self.game.match_scores['us'] + self.game.match_scores['them']
        self.assertGreater(total, 0, "At least one team should score")


if __name__ == '__main__':
    unittest.main()
