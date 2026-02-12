"""
Test Timer Manager
Tests for TimerManager lifecycle, pause/resume, expiration, and lag detection.
"""
import time
import unittest
from unittest.mock import patch
from game_engine.logic.timer_manager import TimerManager


class TestTimerBasics(unittest.TestCase):
    """Basic timer lifecycle tests."""

    def test_initial_state(self):
        """Timer should start inactive with default duration."""
        tm = TimerManager(default_duration=30)
        self.assertFalse(tm.active)
        self.assertEqual(tm.duration, 30)
        self.assertEqual(tm.get_time_remaining(), 0)
        self.assertEqual(tm.get_time_elapsed(), 0)

    def test_custom_default_duration(self):
        """Timer should accept custom default duration."""
        tm = TimerManager(default_duration=60)
        self.assertEqual(tm.duration, 60)

    def test_reset_activates_timer(self):
        """Resetting should activate the timer and set start time."""
        tm = TimerManager()
        tm.reset()
        self.assertTrue(tm.active)
        self.assertGreater(tm.start_time, 0)

    def test_reset_with_custom_duration(self):
        """Resetting with a duration should override the default."""
        tm = TimerManager(default_duration=30)
        tm.reset(duration=45)
        self.assertEqual(tm.duration, 45)
        self.assertTrue(tm.active)

    def test_stop_deactivates(self):
        """Stopping should deactivate the timer."""
        tm = TimerManager()
        tm.reset()
        tm.stop()
        self.assertFalse(tm.active)
        self.assertEqual(tm.get_time_remaining(), 0)


class TestTimerElapsed(unittest.TestCase):
    """Tests for elapsed time and remaining time calculations."""

    def test_elapsed_time_progresses(self):
        """Elapsed time should increase after reset."""
        tm = TimerManager(default_duration=30)
        tm.reset()
        time.sleep(0.1)
        elapsed = tm.get_time_elapsed()
        self.assertGreater(elapsed, 0.05)
        self.assertLess(elapsed, 1.0)  # Sanity check

    def test_remaining_time_decreases(self):
        """Remaining time should be less than full duration after elapsed time."""
        tm = TimerManager(default_duration=30)
        tm.reset()
        time.sleep(0.1)
        remaining = tm.get_time_remaining()
        self.assertLess(remaining, 30)
        self.assertGreater(remaining, 29)

    def test_remaining_floors_at_zero(self):
        """Remaining time should never go negative."""
        tm = TimerManager(default_duration=0)  # Instantly expired
        tm.reset(duration=0)
        time.sleep(0.05)
        self.assertEqual(tm.get_time_remaining(), 0)

    def test_elapsed_inactive_returns_zero(self):
        """Elapsed time for an inactive timer should be 0."""
        tm = TimerManager()
        self.assertEqual(tm.get_time_elapsed(), 0)


class TestTimerPauseResume(unittest.TestCase):
    """Tests for pause and resume functionality."""

    def test_pause_freezes_elapsed(self):
        """Pausing should freeze elapsed time."""
        tm = TimerManager(default_duration=30)
        tm.reset()
        time.sleep(0.1)
        tm.pause()
        
        paused_elapsed = tm.get_time_elapsed()
        time.sleep(0.1)
        # Elapsed should NOT change while paused
        self.assertAlmostEqual(tm.get_time_elapsed(), paused_elapsed, places=2)

    def test_resume_continues_from_paused(self):
        """Resuming should continue timing from where it was paused."""
        tm = TimerManager(default_duration=30)
        tm.reset()
        time.sleep(0.1)
        tm.pause()
        paused_elapsed = tm.get_time_elapsed()
        time.sleep(0.1)  # Wait while paused
        tm.resume()
        
        # After resume, elapsed should be close to paused_elapsed (not paused_elapsed + 0.1)
        time.sleep(0.05)
        resumed_elapsed = tm.get_time_elapsed()
        # The difference should be small (just the 0.05s after resume, not the 0.1s pause)
        self.assertAlmostEqual(resumed_elapsed, paused_elapsed + 0.05, delta=0.05)

    def test_pause_prevents_expiration(self):
        """A paused timer should never report as expired."""
        tm = TimerManager(default_duration=0.05)
        tm.reset(duration=0.05)
        time.sleep(0.02)
        tm.pause()
        time.sleep(0.1)  # Wait well past expiration
        self.assertFalse(tm.is_expired(), "Paused timer should not expire")

    def test_double_pause_is_no_op(self):
        """Pausing an already paused timer should be a no-op."""
        tm = TimerManager()
        tm.reset()
        time.sleep(0.05)
        tm.pause()
        paused_at_1 = tm.paused_at
        tm.pause()  # Second pause — should be no-op
        self.assertEqual(tm.paused_at, paused_at_1)

    def test_resume_inactive_is_no_op(self):
        """Resuming a non-paused timer should be a no-op."""
        tm = TimerManager()
        tm.reset()
        start = tm.start_time
        tm.resume()  # Not paused — no-op
        self.assertEqual(tm.start_time, start)


class TestTimerExpiration(unittest.TestCase):
    """Tests for is_expired and get_lag."""

    def test_not_expired_when_within_duration(self):
        """Timer should not be expired when within its duration."""
        tm = TimerManager(default_duration=30)
        tm.reset()
        self.assertFalse(tm.is_expired())

    def test_expired_after_duration(self):
        """Timer should be expired after its duration passes."""
        tm = TimerManager()
        tm.reset(duration=0.05)
        time.sleep(0.1)
        self.assertTrue(tm.is_expired())

    def test_expired_inactive_returns_false(self):
        """Inactive timer should never report as expired."""
        tm = TimerManager()
        self.assertFalse(tm.is_expired())

    def test_lag_when_not_expired(self):
        """Lag should be 0 when timer has not expired."""
        tm = TimerManager(default_duration=30)
        tm.reset()
        self.assertEqual(tm.get_lag(), 0)

    def test_lag_when_expired(self):
        """Lag should be positive when timer has expired."""
        tm = TimerManager()
        tm.reset(duration=0.05)
        time.sleep(0.15)
        lag = tm.get_lag()
        self.assertGreater(lag, 0.05)

    def test_lag_inactive_returns_zero(self):
        """Lag for inactive timer should be 0."""
        tm = TimerManager()
        self.assertEqual(tm.get_lag(), 0)


if __name__ == '__main__':
    unittest.main()
