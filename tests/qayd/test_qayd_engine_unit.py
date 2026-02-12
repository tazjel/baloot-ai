"""
Test Qayd Engine Unit
Tests for the Qayd (Forensic Challenge) state machine transitions, penalties,
and edge cases without running a full game.
"""
import unittest
from game_engine.logic.game import Game
from game_engine.logic.qayd_state_machine import QaydStep, QaydMenuOption, empty_qayd_state as _empty_state
from game_engine.models.constants import GamePhase


class TestQaydTrigger(unittest.TestCase):
    """Tests for triggering the Qayd challenge."""

    def setUp(self):
        self.game = Game("test_qayd")
        self.game.add_player("p1", "Player 1")  # 0 Bottom, US
        self.game.add_player("p2", "Player 2")  # 1 Right, THEM
        self.game.add_player("p3", "Player 3")  # 2 Top, US
        self.game.add_player("p4", "Player 4")  # 3 Left, THEM
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        self.game.phase = 'PLAYING'
        self.game.is_locked = False

    def test_trigger_success(self):
        """Triggering Qayd should activate the challenge and lock the game."""
        result = self.game.qayd_engine.trigger(0)
        self.assertTrue(result['success'])
        self.assertTrue(self.game.qayd_engine.state['active'])
        self.assertEqual(self.game.qayd_engine.state['step'], QaydStep.MAIN_MENU)
        self.assertEqual(self.game.qayd_engine.state['reporter'], 'Bottom')
        self.assertTrue(self.game.is_locked)
        self.assertEqual(str(self.game.phase), GamePhase.CHALLENGE.value)

    def test_trigger_rejected_when_already_active(self):
        """A second trigger should be rejected if Qayd is already active."""
        self.game.qayd_engine.trigger(0)
        result = self.game.qayd_engine.trigger(1)
        self.assertFalse(result['success'])
        self.assertIn('already active', result['error'])

    def test_trigger_rejected_when_game_locked(self):
        """Trigger should fail if the game is already locked."""
        self.game.is_locked = True
        result = self.game.qayd_engine.trigger(0)
        self.assertFalse(result['success'])
        self.assertIn('locked', result['error'])

    def test_trigger_rejected_in_finished_phase(self):
        """Trigger should fail when game phase is FINISHED."""
        self.game.phase = GamePhase.FINISHED.value
        result = self.game.qayd_engine.trigger(0)
        self.assertFalse(result['success'])

    def test_trigger_rejected_in_gameover_phase(self):
        """Trigger should fail when game phase is GAMEOVER."""
        self.game.phase = GamePhase.GAMEOVER.value
        result = self.game.qayd_engine.trigger(0)
        self.assertFalse(result['success'])

    def test_trigger_sets_bot_timer(self):
        """Bot triggers should get a shorter timer."""
        self.game.players[1].is_bot = True
        result = self.game.qayd_engine.trigger(1)
        self.assertTrue(result['success'])
        self.assertTrue(self.game.qayd_engine.state['reporter_is_bot'])
        self.assertEqual(self.game.qayd_engine.state['timer_duration'], 2)  # TIMER_AI = 2

    def test_trigger_sets_human_timer(self):
        """Human triggers should get the longer timer."""
        result = self.game.qayd_engine.trigger(0)
        self.assertTrue(result['success'])
        self.assertFalse(self.game.qayd_engine.state['reporter_is_bot'])
        self.assertEqual(self.game.qayd_engine.state['timer_duration'], 60)  # TIMER_HUMAN = 60


class TestQaydStepTransitions(unittest.TestCase):
    """Tests for the step-by-step state machine transitions."""

    def setUp(self):
        self.game = Game("test_qayd")
        self.game.add_player("p1", "Player 1")
        self.game.add_player("p2", "Player 2")
        self.game.add_player("p3", "Player 3")
        self.game.add_player("p4", "Player 4")
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        self.game.phase = 'PLAYING'
        self.game.is_locked = False
        # Trigger Qayd to start from MAIN_MENU
        self.game.qayd_engine.trigger(0)

    def test_select_menu_option(self):
        """Selecting a menu option should move to VIOLATION_SELECT."""
        result = self.game.qayd_engine.select_menu_option(QaydMenuOption.REVEAL_CARDS)
        self.assertTrue(result['success'])
        self.assertEqual(self.game.qayd_engine.state['step'], QaydStep.VIOLATION_SELECT)
        self.assertEqual(self.game.qayd_engine.state['menu_option'], QaydMenuOption.REVEAL_CARDS)

    def test_select_menu_option_wrong_step(self):
        """Selecting a menu option from wrong step should fail."""
        # Move past MAIN_MENU first
        self.game.qayd_engine.select_menu_option(QaydMenuOption.REVEAL_CARDS)
        self.game.qayd_engine.select_violation('REVOKE')
        # Now at SELECT_CARD_1 — calling select_menu_option should fail
        result = self.game.qayd_engine.select_menu_option(QaydMenuOption.REVEAL_CARDS)
        self.assertFalse(result['success'])

    def test_select_violation(self):
        """Selecting a violation should move to SELECT_CARD_1."""
        self.game.qayd_engine.select_menu_option(QaydMenuOption.REVEAL_CARDS)
        result = self.game.qayd_engine.select_violation('REVOKE')
        self.assertTrue(result['success'])
        self.assertEqual(self.game.qayd_engine.state['step'], QaydStep.SELECT_CARD_1)
        self.assertEqual(self.game.qayd_engine.state['violation_type'], 'REVOKE')

    def test_reselect_violation_from_card_selection(self):
        """Should allow re-selecting violation from SELECT_CARD_1 or SELECT_CARD_2."""
        self.game.qayd_engine.select_menu_option(QaydMenuOption.REVEAL_CARDS)
        self.game.qayd_engine.select_violation('REVOKE')
        # Re-select from SELECT_CARD_1
        result = self.game.qayd_engine.select_violation('TRUMP_EVASION')
        self.assertTrue(result['success'])
        self.assertEqual(self.game.qayd_engine.state['violation_type'], 'TRUMP_EVASION')


class TestQaydCancel(unittest.TestCase):
    """Tests for cancelling an active Qayd challenge."""

    def setUp(self):
        self.game = Game("test_qayd")
        self.game.add_player("p1", "Player 1")
        self.game.add_player("p2", "Player 2")
        self.game.add_player("p3", "Player 3")
        self.game.add_player("p4", "Player 4")
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        self.game.phase = 'PLAYING'
        self.game.is_locked = False

    def test_cancel_active_qayd(self):
        """Cancelling an active Qayd should reset state and unlock the game."""
        self.game.qayd_engine.trigger(0)
        result = self.game.qayd_engine.cancel()
        self.assertTrue(result['success'])
        self.assertFalse(self.game.qayd_engine.state['active'])
        self.assertEqual(self.game.qayd_engine.state['step'], QaydStep.IDLE)
        self.assertFalse(self.game.is_locked)

    def test_cancel_restores_playing_phase(self):
        """Cancelling Qayd should restore phase to PLAYING."""
        self.game.qayd_engine.trigger(0)
        self.assertEqual(str(self.game.phase), GamePhase.CHALLENGE.value)
        self.game.qayd_engine.cancel()
        self.assertEqual(str(self.game.phase), GamePhase.PLAYING.value)

    def test_cancel_when_not_active(self):
        """Cancelling when no Qayd is active should fail gracefully."""
        result = self.game.qayd_engine.cancel()
        self.assertFalse(result['success'])
        self.assertIn('No active Qayd', result['error'])


class TestQaydPenalty(unittest.TestCase):
    """Tests for penalty calculation."""

    def setUp(self):
        self.game = Game("test_qayd")
        self.game.add_player("p1", "Player 1")
        self.game.add_player("p2", "Player 2")
        self.game.add_player("p3", "Player 3")
        self.game.add_player("p4", "Player 4")

    def test_hokum_base_penalty(self):
        """Hokum base penalty should be 16."""
        self.game.game_mode = 'HOKUM'
        self.game.doubling_level = 1
        penalty = self.game.qayd_engine._calculate_penalty()
        self.assertEqual(penalty, 16)

    def test_sun_base_penalty(self):
        """Sun base penalty should be 26."""
        self.game.game_mode = 'SUN'
        self.game.doubling_level = 1
        penalty = self.game.qayd_engine._calculate_penalty()
        self.assertEqual(penalty, 26)

    def test_doubled_penalty(self):
        """Doubled game should multiply penalty by 2."""
        self.game.game_mode = 'HOKUM'
        self.game.doubling_level = 2
        penalty = self.game.qayd_engine._calculate_penalty()
        self.assertEqual(penalty, 32)  # 16 * 2

    def test_tripled_penalty(self):
        """Tripled game should multiply penalty by 3."""
        self.game.game_mode = 'SUN'
        self.game.doubling_level = 3
        penalty = self.game.qayd_engine._calculate_penalty()
        self.assertEqual(penalty, 78)  # 26 * 3

    def test_ashkal_uses_sun_penalty(self):
        """Ashkal mode should use the Sun penalty base (26)."""
        self.game.game_mode = 'ASHKAL'
        self.game.doubling_level = 1
        penalty = self.game.qayd_engine._calculate_penalty()
        self.assertEqual(penalty, 26)


class TestQaydEmptyState(unittest.TestCase):
    """Tests for the _empty_state helper."""

    def test_empty_state_has_all_keys(self):
        """Empty state should contain all required keys."""
        state = _empty_state()
        required_keys = [
            'active', 'step', 'reporter', 'reporter_is_bot',
            'menu_option', 'violation_type', 'crime_card', 'proof_card',
            'verdict', 'verdict_message', 'loser_team', 'penalty_points',
            'timer_duration', 'timer_start', 'crime_signature',
            'status', 'reason', 'target_play'
        ]
        for key in required_keys:
            self.assertIn(key, state, f"Missing key: {key}")

    def test_empty_state_is_idle(self):
        """Empty state should start as IDLE and inactive."""
        state = _empty_state()
        self.assertFalse(state['active'])
        self.assertEqual(state['step'], QaydStep.IDLE)
        self.assertIsNone(state['reporter'])

    def test_empty_state_is_independent(self):
        """Each call to _empty_state should return a unique dict (no shared references)."""
        s1 = _empty_state()
        s2 = _empty_state()
        s1['active'] = True
        self.assertFalse(s2['active'], "Modifying one state should not affect another")


if __name__ == '__main__':
    unittest.main()
