import os
import time
import json
import logging
import hashlib
import traceback

# Settings
try:
    from server.settings import REDIS_URL, OFFLINE_MODE
except ImportError:
    REDIS_URL = "redis://localhost:6379/0"
    OFFLINE_MODE = False

# Redis
try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

class BrainClient:
    """
    Handles all interactions with 'The Brain' (Redis Layer).
    - Looks up learned moves.
    - Queues game states for analysis (The Scout).
    - Captures data for the Flywheel.
    """
    def __init__(self):
        self.redis_client = None
        self._connect()

    def _connect(self):
        if OFFLINE_MODE:
             logger.info("[BRAIN] OFFLINE_MODE. Redis disabled.")
             return

        if redis:
            try:
                self.redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1.0)
                logger.info("[BRAIN] Connected to Redis.")
            except Exception as e:
                logger.error(f"[BRAIN] Redis connection failed: {e}")

    def lookup_move(self, context_hash: str):
        """
        Check if The Brain has a correct move for this exact context.
        Returns the move dict if found, else None.
        """
        if not self.redis_client: return None

        try:
            start = time.perf_counter()
            # 1. Check for "Certified Correct" move
            key = f"brain:correct:{context_hash}"
            move_json = self.redis_client.get(key)

            # 2. Fallback: Check for "Manual Test Override" (for debugging)
            if not move_json:
                manual_key = "brain:move:FORCE_OVERRIDE_TEST"
                move_json = self.redis_client.get(manual_key)
                if move_json:
                     logger.info(f"[BRAIN] Force Override Triggered for {context_hash}")

            duration = (time.perf_counter() - start) * 1000
            if duration > 50: # strict perf log
                 logger.debug(f"[BRAIN] Lookup took {duration:.2f}ms")

            if move_json:
                return json.loads(move_json)
            
            return None

        except Exception as e:
            logger.error(f"[BRAIN] Lookup Error: {e}")
            return None

    def queue_analysis(self, ctx_payload: dict):
        """
        Push current context to the analysis queue for asynchronous processing.
        """
        if not self.redis_client: return

        try:
            self.redis_client.lpush("bot:analyze_queue", json.dumps(ctx_payload))
        except Exception as e:
            # Silent fail for fire-and-forget
            pass

    def capture_round_data(self, round_snapshot: dict):
        """
        Push finished round data to the analytics stream.
        """
        if not self.redis_client: return

        try:
            # Cap stream length to prevent memory leaks
            self.redis_client.xadd("analytics:hand_finished", {'data': json.dumps(round_snapshot)}, maxlen=1000)
        except Exception as e:
            logger.error(f"[BRAIN] Failed to capture data: {e}")
