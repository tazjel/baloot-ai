"""
GBaloot Autopilot — Closed-loop bot player for the Source platform.

Intercepts SFS2X WebSocket traffic, translates events into BotAgent-compatible
game_state, obtains decisions, and injects JavaScript to execute moves.

Usage::

    # From capture_session.py with --autopilot flag:
    python gbaloot/capture_session.py --label auto_01 --autopilot --username MyUser

    # Programmatic (sync Playwright):
    autopilot = AutopilotSession(page, username="MyUser")
    autopilot.start()

Safety:
    - Kill switch: touch gbaloot/.pause to pause, rm to resume
    - Minimum 2s delay between actions (human-like timing)
    - Skips action if hand is empty or seat unknown
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from gbaloot.core.capturer import WS_INTERCEPTOR_JS, collect_messages
from gbaloot.core.decoder import SFS2XDecoder, decode_message, try_decompress
from gbaloot.core.state_builder import StateBuilder
from gbaloot.core.gboard import GBoard

logger = logging.getLogger(__name__)

# Kill switch file path
PAUSE_FILE = Path(__file__).parent / ".pause"


class AutopilotSession:
    """Main autopilot orchestrator — sync Playwright edition.

    Ties together:
      - WS interceptor (existing capturer JS)
      - SFS2X decoder (existing)
      - StateBuilder (translates events → game_state)
      - GBoard (executes decisions via JS injection)
      - BotAgent (AI decision engine)
    """

    def __init__(
        self,
        page,
        username: str,
        min_action_delay: float = 2.0,
        poll_interval: float = 0.2,
    ):
        self.page = page
        self.username = username
        self.state_builder = StateBuilder(my_username=username)
        self.gboard = GBoard(page)
        self.running = True

        # Timing
        self.min_action_delay = min_action_delay
        self.poll_interval = poll_interval
        self.last_action_time = 0.0

        # Stats
        self.events_processed = 0
        self.actions_taken = 0
        self.errors = 0

    # ── Main Entry Point ─────────────────────────────────────────

    def start(self):
        """Inject interceptor, run recon, and start the autopilot loop.

        This is a blocking call — runs until Ctrl+C or self.running = False.
        """
        # Step 1: Ensure WS interceptor is injected
        try:
            self.page.evaluate(WS_INTERCEPTOR_JS)
            logger.info("Autopilot: WS interceptor injected")
        except Exception as e:
            logger.warning(f"Autopilot: WS interceptor may already be active: {e}")

        # Step 2: Run GBoard reconnaissance
        logger.info("Autopilot: Running GBoard reconnaissance...")
        recon = self.gboard.initialize_sync()

        if not self.gboard.is_ready:
            logger.warning(
                "Autopilot: GBoard recon did not find game API. "
                "Will retry recon periodically. You can also configure "
                "paths manually via gboard.configure_paths()."
            )
        else:
            logger.info(f"Autopilot: GBoard ready — {self.gboard.status()}")

        logger.info(
            f"Autopilot: Started for user '{self.username}'. "
            f"Polling every {self.poll_interval}s, "
            f"min action delay {self.min_action_delay}s."
        )

        # Step 3: Main loop
        self._loop()

    # ── Main Loop ────────────────────────────────────────────────

    def _loop(self):
        """Core event loop — poll, decode, decide, act."""
        recon_retry_interval = 30.0
        last_recon_retry = time.time()

        while self.running:
            try:
                # Kill switch check
                if self._is_paused():
                    time.sleep(1.0)
                    continue

                # Retry recon if GBoard not ready
                if not self.gboard.is_ready:
                    now = time.time()
                    if now - last_recon_retry > recon_retry_interval:
                        logger.info("Autopilot: Retrying GBoard recon...")
                        self.gboard.initialize_sync()
                        last_recon_retry = now

                # Collect new intercepted messages
                messages = self._collect_messages()

                # Decode and process each message
                for msg in messages:
                    self._process_message(msg)

                # Check if it's our turn and act
                if self.state_builder.is_my_turn() and self.gboard.is_ready:
                    self._act()

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("Autopilot: Interrupted by user")
                self.running = False
            except Exception as e:
                self.errors += 1
                logger.error(f"Autopilot: Loop error: {e}")
                time.sleep(1.0)

        logger.info(
            f"Autopilot: Stopped. Events={self.events_processed}, "
            f"Actions={self.actions_taken}, Errors={self.errors}"
        )

    # ── Message Collection ───────────────────────────────────────

    def _collect_messages(self) -> list:
        """Pull intercepted WS messages from the browser."""
        try:
            return collect_messages(self.page) or []
        except Exception as e:
            logger.debug(f"Autopilot: Message collection error: {e}")
            return []

    # ── Message Processing ───────────────────────────────────────

    def _process_message(self, msg: dict):
        """Decode a raw WS message and feed it to StateBuilder."""
        data = msg.get("data", "")
        direction = msg.get("type", "RECV")

        if not isinstance(data, str):
            return

        # Only process binary SFS2X messages (hex-encoded)
        if not data.startswith("[hex:"):
            return

        try:
            decoded = decode_message(data)
            fields = decoded.get("fields", {})
            if not fields:
                return

            # Build a GameEvent-like dict for StateBuilder
            action = self._classify_action(fields)
            event = {
                "timestamp": msg.get("t", 0),
                "direction": direction,
                "action": action,
                "fields": fields,
                "raw_size": msg.get("size", 0),
            }

            self.state_builder.process_event(event)
            self.events_processed += 1

        except Exception as e:
            logger.debug(f"Autopilot: Decode error: {e}")

    def _classify_action(self, fields: dict) -> str:
        """Classify a decoded SFS2X message into an action name.

        Uses the same classification logic as the existing GameDecoder,
        but simplified for real-time processing.
        """
        from gbaloot.core.event_types import ALL_GAME_ACTIONS

        # Check nested p.p structure for action markers
        params = fields.get("p", {})
        if isinstance(params, dict):
            # Check for "c" command field
            c_val = params.get("c")
            if isinstance(c_val, str) and c_val in ALL_GAME_ACTIONS:
                return c_val

            # Check inner p.p
            inner = params.get("p", {})
            if isinstance(inner, dict):
                c_inner = inner.get("c")
                if isinstance(c_inner, str) and c_inner in ALL_GAME_ACTIONS:
                    return c_inner

                # Check last_action
                last_action = inner.get("last_action", {})
                if isinstance(last_action, dict):
                    la = last_action.get("action", "")
                    if la in ALL_GAME_ACTIONS:
                        return la

                # Has game state fields → it's a game_state update
                if "played_cards" in inner or "pcsCount" in inner or "gStg" in inner:
                    return "game_state"

            # Top-level params keys
            for key in params:
                if key in ALL_GAME_ACTIONS:
                    return key

        # Check top-level fields
        for key in fields:
            if key in ALL_GAME_ACTIONS:
                return key

        return "unknown"

    # ── Decision & Execution ─────────────────────────────────────

    def _act(self):
        """Get a decision from BotAgent and execute it via GBoard."""
        # Rate limiting — human-like delay
        now = time.time()
        if now - self.last_action_time < self.min_action_delay:
            return

        # Safety: skip if we don't know our seat or hand is empty
        gs = self.state_builder.game_state
        if self.state_builder.my_seat is None:
            logger.debug("Autopilot: Seat not yet discovered, skipping")
            return

        our_hand = gs["players"][0]["hand"]
        phase = gs.get("phase")

        if phase == "PLAYING" and not our_hand:
            logger.debug("Autopilot: Empty hand in PLAYING phase, skipping")
            return

        try:
            from ai_worker.agent import bot_agent

            decision = bot_agent.get_decision(gs, player_index=0)

            if not decision:
                return

            action = decision.get("action")
            if action == "PASS" and phase == "PLAYING":
                # In playing phase, PASS is not valid — skip
                return

            self.gboard.execute_sync(decision, gs)
            self.last_action_time = time.time()
            self.actions_taken += 1

            logger.info(
                f"Autopilot ACTION: {action} "
                f"cardIndex={decision.get('cardIndex')} "
                f"suit={decision.get('suit')} "
                f"reason={decision.get('reasoning', '')[:60]}"
            )

        except Exception as e:
            self.errors += 1
            logger.error(f"Autopilot: Decision/execution error: {e}")

    # ── Kill Switch ──────────────────────────────────────────────

    def _is_paused(self) -> bool:
        """Check if the kill switch file exists."""
        return PAUSE_FILE.exists()

    # ── Status ───────────────────────────────────────────────────

    def status(self) -> dict:
        """Return autopilot status summary."""
        return {
            "running": self.running,
            "paused": self._is_paused(),
            "username": self.username,
            "my_seat": self.state_builder.my_seat,
            "phase": self.state_builder.game_state.get("phase"),
            "is_my_turn": self.state_builder.is_my_turn(),
            "events_processed": self.events_processed,
            "actions_taken": self.actions_taken,
            "errors": self.errors,
            "gboard_ready": self.gboard.is_ready,
            "state_summary": self.state_builder.summary(),
        }
