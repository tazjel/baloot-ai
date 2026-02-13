"""
Test Game Lifecycle
Tests for GameLifecycle: start_game, reset_round_state, deal_initial_cards,
complete_deal, end_round, and gameover detection.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.models.constants import GamePhase


class _LifecycleTestBase(unittest.TestCase):
    """Base: Create a game with 4 players."""

    def setUp(self):
        self.game = Game("test_room")
        for i in range(4):
            self.game.add_player(f"p{i}", f"Player {i}")


class TestStartGame(_LifecycleTestBase):
    """Tests for start_game."""

    def test_start_game_success(self):
        """Starting with 4 players should succeed."""
        result = self.game.lifecycle.start_game()
        self.assertTrue(result)

    def test_start_game_fails_with_less_than_4(self):
        """Cannot start game with fewer than 4 players."""
        game2 = Game("test2")
        game2.add_player("p0", "Player 0")
        game2.add_player("p1", "Player 1")
        result = game2.lifecycle.start_game()
        self.assertFalse(result)

    def test_phase_is_bidding_after_start(self):
        """Game phase should be BIDDING after start."""
        self.game.lifecycle.start_game()
        self.assertEqual(self.game.phase, GamePhase.BIDDING.value)

    def test_bidding_engine_created(self):
        """BiddingEngine should be initialized after start."""
        self.game.lifecycle.start_game()
        self.assertIsNotNone(self.game.bidding_engine)

    def test_dealer_assigned(self):
        """Dealer index should be set (0-3)."""
        self.game.lifecycle.start_game()
        self.assertIn(self.game.dealer_index, [0, 1, 2, 3])

    def test_current_turn_set(self):
        """Current turn should be set to bidding engine's first turn."""
        self.game.lifecycle.start_game()
        self.assertEqual(self.game.current_turn, self.game.bidding_engine.current_turn)


class TestDealInitialCards(_LifecycleTestBase):
    """Tests for deal_initial_cards."""

    def test_each_player_gets_5_cards(self):
        """Each player should receive exactly 5 cards."""
        self.game.lifecycle.start_game()
        for p in self.game.players:
            self.assertEqual(len(p.hand), 5)

    def test_floor_card_set(self):
        """Floor card should be set after initial deal."""
        self.game.lifecycle.start_game()
        self.assertIsNotNone(self.game._floor_card_obj)

    def test_deck_has_remaining_cards(self):
        """Deck should have cards remaining for complete_deal."""
        self.game.lifecycle.start_game()
        # 32 total - 20 dealt - 1 floor = 11 remaining
        self.assertEqual(len(self.game.deck.cards), 11)


class TestCompleteDeal(_LifecycleTestBase):
    """Tests for complete_deal."""

    def _setup_post_bidding(self):
        """Simulate completing a bid."""
        self.game.lifecycle.start_game()
        eng = self.game.bidding_engine
        first = eng.current_turn
        floor_suit = eng.floor_card.suit
        eng.process_bid(first, "HOKUM", suit=floor_suit)
        for _ in range(3):
            eng.process_bid(eng.current_turn, "PASS")
        # Pass through doubling
        eng.process_bid(eng.current_turn, "PASS")
        # Variant selection
        eng.process_bid(eng.contract.bidder_idx, "OPEN")
        return eng.contract.bidder_idx

    def test_bidder_gets_8_cards(self):
        """After complete_deal, bidder should have 8 cards (5 + floor + 2)."""
        bidder_idx = self._setup_post_bidding()
        self.game.lifecycle.complete_deal(bidder_idx)
        self.assertEqual(len(self.game.players[bidder_idx].hand), 8)

    def test_others_get_8_cards(self):
        """After complete_deal, non-bidders should have 8 cards (5 + 3)."""
        bidder_idx = self._setup_post_bidding()
        self.game.lifecycle.complete_deal(bidder_idx)
        for p in self.game.players:
            if p.index != bidder_idx:
                self.assertEqual(len(p.hand), 8)

    def test_phase_is_playing(self):
        """Phase should be PLAYING after complete_deal."""
        bidder_idx = self._setup_post_bidding()
        self.game.lifecycle.complete_deal(bidder_idx)
        self.assertEqual(self.game.phase, GamePhase.PLAYING.value)

    def test_current_turn_is_right_of_dealer(self):
        """Current turn should be dealer + 1."""
        bidder_idx = self._setup_post_bidding()
        self.game.lifecycle.complete_deal(bidder_idx)
        expected = (self.game.dealer_index + 1) % 4
        self.assertEqual(self.game.current_turn, expected)

    def test_floor_card_cleared(self):
        """Floor card should be cleared after bidder receives it."""
        bidder_idx = self._setup_post_bidding()
        self.game.lifecycle.complete_deal(bidder_idx)
        self.assertIsNone(self.game._floor_card_obj)

    def test_initial_hands_recorded(self):
        """Initial hands snapshot should be recorded."""
        bidder_idx = self._setup_post_bidding()
        self.game.lifecycle.complete_deal(bidder_idx)
        for p in self.game.players:
            self.assertIn(p.position, self.game.initial_hands)
            self.assertEqual(len(self.game.initial_hands[p.position]), 8)


class TestResetRoundState(_LifecycleTestBase):
    """Tests for reset_round_state."""

    def test_clears_player_hands(self):
        """All player hands should be empty after reset."""
        self.game.lifecycle.start_game()
        self.game.lifecycle.reset_round_state()
        for p in self.game.players:
            self.assertEqual(len(p.hand), 0)

    def test_clears_table_cards(self):
        """Table cards should be empty after reset."""
        self.game.lifecycle.start_game()
        self.game.table_cards = [{'card': 'mock'}]
        self.game.lifecycle.reset_round_state()
        self.assertEqual(len(self.game.table_cards), 0)

    def test_refreshes_deck(self):
        """Deck should be refreshed with 32 cards."""
        self.game.lifecycle.start_game()
        self.game.lifecycle.reset_round_state()
        self.assertEqual(len(self.game.deck.cards), 32)


class TestEndRound(_LifecycleTestBase):
    """Tests for end_round."""

    def _setup_played_round(self):
        """Create a game in PLAYING state with minimal setup."""
        self.game.lifecycle.start_game()
        self.game.phase = GamePhase.PLAYING.value
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        # Mock scoring by setting scores directly
        self.game.match_scores = {'us': 0, 'them': 0}

    def test_dealer_advances(self):
        """Dealer index should advance by 1 after round end."""
        self._setup_played_round()
        old_dealer = self.game.dealer_index
        self.game.lifecycle.end_round(skip_scoring=True)
        expected = (old_dealer + 1) % 4
        self.assertEqual(self.game.dealer_index, expected)

    def test_phase_is_finished_when_no_winner(self):
        """Phase should be FINISHED if no team hit 152."""
        self._setup_played_round()
        self.game.lifecycle.end_round(skip_scoring=True)
        self.assertEqual(self.game.phase, GamePhase.FINISHED.value)

    def test_phase_is_gameover_when_us_wins(self):
        """Phase should be GAMEOVER when 'us' score >= 152."""
        self._setup_played_round()
        self.game.match_scores['us'] = 160
        self.game.lifecycle.end_round(skip_scoring=True)
        self.assertEqual(self.game.phase, GamePhase.GAMEOVER.value)

    def test_phase_is_gameover_when_them_wins(self):
        """Phase should be GAMEOVER when 'them' score >= 152."""
        self._setup_played_round()
        self.game.match_scores['them'] = 152
        self.game.lifecycle.end_round(skip_scoring=True)
        self.assertEqual(self.game.phase, GamePhase.GAMEOVER.value)

    def test_sawa_failed_khasara_cleared(self):
        """sawa_failed_khasara should be reset after round end."""
        self._setup_played_round()
        self.game.sawa_failed_khasara = True
        self.game.lifecycle.end_round(skip_scoring=True)
        self.assertFalse(self.game.sawa_failed_khasara)


class TestMultipleRounds(_LifecycleTestBase):
    """Tests for consecutive round lifecycle."""

    def test_can_start_second_round(self):
        """After FINISHED, starting a new game should work."""
        self.game.lifecycle.start_game()
        self.game.phase = GamePhase.FINISHED.value
        result = self.game.lifecycle.start_game()
        self.assertTrue(result)
        self.assertEqual(self.game.phase, GamePhase.BIDDING.value)


if __name__ == '__main__':
    unittest.main()
