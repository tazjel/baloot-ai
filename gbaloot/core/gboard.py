"""
GBoard — JavaScript injection actuator for the source platform game platform.

Executes BotAgent decisions by reverse-engineering the game's internal
JavaScript objects and invoking them directly via page.evaluate().
No pixel clicking — deterministic JS function calls.

The GBoard is initialized in two phases:
  1. RECON: Run gboard_recon to discover game framework internals.
  2. INIT: Configure actuator paths based on recon results.

Usage::

    gboard = GBoard(page)           # Playwright page (sync or async)
    recon = gboard.initialize()     # Must be called after game loads
    await gboard.execute(decision, game_state)  # Execute a BotAgent decision
"""
from __future__ import annotations

import json
import logging

from gbaloot.core.card_mapping import SUIT_SYMBOL_TO_IDX, RANK_TO_IDX

logger = logging.getLogger(__name__)


class GBoard:
    """Actuator that executes BotAgent decisions via JS injection.

    Supports three execution strategies (tried in order):
      1. Game controller — call the game's own playCard/submitBid methods
      2. SFS2X client — send ExtensionRequests directly to the server
      3. Canvas events — dispatch synthetic pointer events (last resort)
    """

    def __init__(self, page):
        self.page = page
        self.game_controller_path: str | None = None
        self.sfs_client_path: str | None = None
        self.sfs_api_available: bool = False
        self._initialized: bool = False
        self._recon_report: dict = {}

    # ── Initialization ───────────────────────────────────────────

    def initialize_sync(self) -> dict:
        """Run reconnaissance to discover game internals (sync Playwright).

        Must be called after the game has loaded and a round has started.
        Returns the recon report for inspection.
        """
        from gbaloot.core.gboard_recon import run_full_recon_sync

        report = run_full_recon_sync(self.page)
        self._recon_report = report
        self._configure_from_recon(report)
        return report

    async def initialize(self) -> dict:
        """Run reconnaissance to discover game internals (async Playwright).

        Must be called after the game has loaded and a round has started.
        Returns the recon report for inspection.
        """
        from gbaloot.core.gboard_recon import run_full_recon

        report = await run_full_recon(self.page)
        self._recon_report = report
        self._configure_from_recon(report)
        return report

    def _configure_from_recon(self, report: dict):
        """Extract actuator paths from the recon report."""
        # SFS2X client path
        sfs_info = report.get("sfs_client", {})
        if isinstance(sfs_info, dict) and sfs_info.get("path"):
            self.sfs_client_path = sfs_info["path"]
            logger.info(f"GBoard: SFS2X client found at {self.sfs_client_path}")

        # SFS2X API availability (check both old and new recon key names)
        for api_key in ("sfs2x_api", "sfs2x_api_check"):
            api_info = report.get(api_key, {})
            if isinstance(api_info, dict) and api_info.get("available"):
                self.sfs_api_available = True
                # Log key capabilities
                if api_info.get("has_extension_request"):
                    logger.info("GBoard: SFS2X ExtensionRequest available")
                if api_info.get("has_sfs_object"):
                    logger.info("GBoard: SFS2X SFSObject available")
                break

        # Game controller (card-play functions)
        card_funcs = report.get("card_play_functions", [])
        if isinstance(card_funcs, list):
            for func in card_funcs:
                name = func.get("name", "")
                if name.lower() in ("playcard", "play_card", "doplay",
                                     "sendplay", "handleplay"):
                    # Use the parent object as the controller
                    path = func.get("path", "")
                    parts = path.rsplit(".", 1)
                    if len(parts) == 2:
                        self.game_controller_path = parts[0]
                        logger.info(
                            f"GBoard: Game controller found at "
                            f"{self.game_controller_path} (method: {name})"
                        )
                    break

        self._initialized = bool(
            self.game_controller_path or self.sfs_client_path
        )

        if not self._initialized:
            logger.warning(
                "GBoard: No game API found. Card play and bid functions "
                "will not work until recon discovers valid paths."
            )

    # ── Execution ────────────────────────────────────────────────

    def execute_sync(self, decision: dict, game_state: dict):
        """Execute a BotAgent decision (sync Playwright).

        @param decision: BotAgent decision dict (action, cardIndex, etc.)
        @param game_state: Current game state dict.
        """
        action = decision.get("action")

        if action == "PLAY":
            card_index = decision.get("cardIndex", 0)
            hand = game_state["players"][0]["hand"]
            if card_index < 0 or card_index >= len(hand):
                logger.error(f"GBoard: cardIndex {card_index} out of range (hand size {len(hand)})")
                return
            card = hand[card_index]
            self._play_card_sync(card)

        elif action in ("SUN", "HOKUM", "PASS", "DOUBLE"):
            suit = decision.get("suit")
            self._submit_bid_sync(action, suit)

        else:
            logger.warning(f"GBoard: Unknown action {action!r}")

    async def execute(self, decision: dict, game_state: dict):
        """Execute a BotAgent decision (async Playwright)."""
        action = decision.get("action")

        if action == "PLAY":
            card_index = decision.get("cardIndex", 0)
            hand = game_state["players"][0]["hand"]
            if card_index < 0 or card_index >= len(hand):
                logger.error(f"GBoard: cardIndex {card_index} out of range (hand size {len(hand)})")
                return
            card = hand[card_index]
            await self._play_card(card)

        elif action in ("SUN", "HOKUM", "PASS", "DOUBLE"):
            suit = decision.get("suit")
            await self._submit_bid(action, suit)

        else:
            logger.warning(f"GBoard: Unknown action {action!r}")

    # ── Card Play ────────────────────────────────────────────────

    def _card_to_source_index(self, card: dict) -> int:
        """Convert a card dict to its Source 0-51 index."""
        suit_idx = SUIT_SYMBOL_TO_IDX.get(card["suit"], 0)
        rank_idx = RANK_TO_IDX.get(card["rank"], 0)
        return suit_idx * 13 + rank_idx

    def _play_card_sync(self, card: dict):
        """Play a card via JS injection (sync)."""
        source_idx = self._card_to_source_index(card)
        logger.info(f"GBoard: Playing {card['rank']}{card['suit']} (source index {source_idx})")

        if self.sfs_client_path and self.sfs_api_available:
            self._send_sfs_extension_sync("a_play", {"card": source_idx})
        elif self.game_controller_path:
            self.page.evaluate(
                f"() => {{ {self.game_controller_path}.playCard({source_idx}); }}"
            )
        else:
            logger.error("GBoard: No actuator available for card play")

    async def _play_card(self, card: dict):
        """Play a card via JS injection (async)."""
        source_idx = self._card_to_source_index(card)
        logger.info(f"GBoard: Playing {card['rank']}{card['suit']} (source index {source_idx})")

        if self.sfs_client_path and self.sfs_api_available:
            await self._send_sfs_extension("a_play", {"card": source_idx})
        elif self.game_controller_path:
            await self.page.evaluate(
                f"() => {{ {self.game_controller_path}.playCard({source_idx}); }}"
            )
        else:
            logger.error("GBoard: No actuator available for card play")

    # ── Bidding ──────────────────────────────────────────────────

    _BID_MAP: dict[str, int] = {
        "PASS": 0,
        "SUN": 1,
        "HOKUM": 2,
        "DOUBLE": 3,
    }

    def _submit_bid_sync(self, action: str, suit: str | None = None):
        """Submit a bid via JS injection (sync)."""
        bid_value = self._BID_MAP.get(action, 0)
        suit_idx = SUIT_SYMBOL_TO_IDX.get(suit, -1) if suit else -1

        logger.info(f"GBoard: Bidding {action} (bid={bid_value}, suit={suit_idx})")

        params: dict = {"bid": bid_value}
        if suit_idx >= 0:
            params["ts"] = suit_idx

        if self.sfs_client_path and self.sfs_api_available:
            self._send_sfs_extension_sync("bidAction", params)
        elif self.game_controller_path:
            self.page.evaluate(
                f"() => {{ {self.game_controller_path}.submitBid({bid_value}, {suit_idx}); }}"
            )
        else:
            logger.error("GBoard: No actuator available for bidding")

    async def _submit_bid(self, action: str, suit: str | None = None):
        """Submit a bid via JS injection (async)."""
        bid_value = self._BID_MAP.get(action, 0)
        suit_idx = SUIT_SYMBOL_TO_IDX.get(suit, -1) if suit else -1

        logger.info(f"GBoard: Bidding {action} (bid={bid_value}, suit={suit_idx})")

        params: dict = {"bid": bid_value}
        if suit_idx >= 0:
            params["ts"] = suit_idx

        if self.sfs_client_path and self.sfs_api_available:
            await self._send_sfs_extension("bidAction", params)
        elif self.game_controller_path:
            await self.page.evaluate(
                f"() => {{ {self.game_controller_path}.submitBid({bid_value}, {suit_idx}); }}"
            )
        else:
            logger.error("GBoard: No actuator available for bidding")

    # ── SFS2X Direct Commands ────────────────────────────────────

    def _build_sfs_extension_js(self, cmd: str, params: dict) -> str:
        """Build the JS code for sending an SFS2X ExtensionRequest."""
        params_json = json.dumps(params)
        return f"""
            () => {{
                const sfs = {self.sfs_client_path};
                const SFSObject = (typeof SFS2X !== 'undefined' && SFS2X.Entities && SFS2X.Entities.Data)
                    ? SFS2X.Entities.Data.SFSObject
                    : null;

                if (!sfs || !SFSObject) {{
                    console.error('GBoard: SFS client or SFSObject not found');
                    return false;
                }}

                const obj = new SFSObject();
                const params = {params_json};
                for (const [key, val] of Object.entries(params)) {{
                    if (typeof val === 'number') {{
                        if (Number.isInteger(val)) obj.putInt(key, val);
                        else obj.putDouble(key, val);
                    }}
                    else if (typeof val === 'string') obj.putUtfString(key, val);
                    else if (typeof val === 'boolean') obj.putBool(key, val);
                }}

                const ExtReq = (typeof SFS2X !== 'undefined' && SFS2X.Requests && SFS2X.Requests.System)
                    ? SFS2X.Requests.System.ExtensionRequest
                    : null;

                if (!ExtReq) {{
                    console.error('GBoard: ExtensionRequest constructor not found');
                    return false;
                }}

                const req = new ExtReq('{cmd}', obj, sfs.lastJoinedRoom);
                sfs.send(req);
                return true;
            }}
        """

    def _send_sfs_extension_sync(self, cmd: str, params: dict):
        """Send a raw SFS2X ExtensionRequest (sync Playwright)."""
        if not self.sfs_client_path:
            logger.error("GBoard: No SFS2X client path configured")
            return
        js = self._build_sfs_extension_js(cmd, params)
        try:
            result = self.page.evaluate(js)
            if not result:
                logger.warning(f"GBoard: SFS2X send returned falsy for {cmd}")
        except Exception as e:
            logger.error(f"GBoard: SFS2X send failed for {cmd}: {e}")

    async def _send_sfs_extension(self, cmd: str, params: dict):
        """Send a raw SFS2X ExtensionRequest (async Playwright)."""
        if not self.sfs_client_path:
            logger.error("GBoard: No SFS2X client path configured")
            return
        js = self._build_sfs_extension_js(cmd, params)
        try:
            result = await self.page.evaluate(js)
            if not result:
                logger.warning(f"GBoard: SFS2X send returned falsy for {cmd}")
        except Exception as e:
            logger.error(f"GBoard: SFS2X send failed for {cmd}: {e}")

    # ── Manual Path Configuration ────────────────────────────────

    def configure_paths(
        self,
        sfs_client_path: str | None = None,
        game_controller_path: str | None = None,
    ):
        """Manually set actuator paths (bypass recon).

        Use this after inspecting a recon_report.json to hardcode
        known-good paths.
        """
        if sfs_client_path:
            self.sfs_client_path = sfs_client_path
        if game_controller_path:
            self.game_controller_path = game_controller_path
        self._initialized = bool(
            self.sfs_client_path or self.game_controller_path
        )
        logger.info(
            f"GBoard: Paths configured manually. "
            f"SFS={self.sfs_client_path}, Controller={self.game_controller_path}"
        )

    # ── Status ───────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        """Check if GBoard has a valid actuator configured."""
        return self._initialized

    def status(self) -> dict:
        """Return current GBoard configuration status."""
        return {
            "initialized": self._initialized,
            "sfs_client_path": self.sfs_client_path,
            "game_controller_path": self.game_controller_path,
            "sfs_api_available": self.sfs_api_available,
        }
