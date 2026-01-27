import time
import logging

logger = logging.getLogger(__name__)

class TimerManager:
    """
    Centralized timer logic for the Game Engine.
    Handles duration tracking, expiration checks, and drift calculations.
    """
    def __init__(self, default_duration=30):
        self.start_time = 0
        self.duration = default_duration
        self.active = False
        self.last_reset_time = 0

    def reset(self, duration=None):
        """Reset the timer with an optional new duration."""
        if duration is not None:
            self.duration = duration
        
        self.start_time = time.time()
        self.active = True
        self.last_reset_time = self.start_time
        self.paused = False
        self.paused_at = 0
        # logger.info(f"Timer RESET. Duration: {self.duration}s")

    def stop(self):
        """Stop the timer."""
        self.active = False

    def pause(self):
        """Pause the timer, freezing the elapsed time."""
        if not self.active or self.paused:
            return
        self.paused_at = time.time()
        self.paused = True
        logger.info("Timer PAUSED")

    def resume(self):
        """Resume the timer, adjusting start_time for the paused duration."""
        if not self.active or not self.paused:
            return
        
        pause_duration = time.time() - self.paused_at
        self.start_time += pause_duration # Shift start time forward
        self.paused = False
        logger.info(f"Timer RESUMED (Paused for {pause_duration:.2f}s)")

    def get_time_elapsed(self):
        """Return seconds elapsed since start."""
        if not self.active:
            return 0
        
        if self.paused:
            # If paused, elapsed time is fixed at the pause moment
            return self.paused_at - self.start_time
            
        return time.time() - self.start_time

    def get_time_remaining(self):
        """Return seconds remaining. Returns 0 if expired or inactive."""
        if not self.active:
            return 0
        elapsed = self.get_time_elapsed() # Handles paused state
        return max(0, self.duration - elapsed)

    def is_expired(self):
        """Check if timer has exceeded duration."""
        if not self.active or self.paused:
            return False
        return self.get_time_elapsed() > self.duration
        
    def get_lag(self):
        """Return how many seconds PAST the deadline we are."""
        if not self.active or self.paused:
            return 0
        elapsed = self.get_time_elapsed()
        return max(0, elapsed - self.duration)
