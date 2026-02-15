"""
GameReconstructor — Rebuild game board state from real SFS2X session events.

Parses the ``fields.p.p`` nesting used by the source protocol and maps real
field names (gStg, dealer, mover, pcs, played_cards, gm, ts, last_action)
into BoardState / PlayerState snapshots suitable for the Review tab's visual
board.

Source field reference:
    gStg        → game stage: 1=BIDDING, 2=PLAYING, 3=TRICK_COMPLETE
    dealer      → 1-indexed dealer seat
    mover       → 1-indexed current player seat
    pcs         → 64-bit bitmask encoding the hand of the captured player
    played_cards→ 4-element array of card indices (-1 = empty)
    gm          → game mode: 'ashkal'/'sun'='SUN', 'hokom'/'hokum'='HOKUM'
    ts          → trump suit index (0=♠, 1=♥, 2=♣, 3=♦)
    last_action → {action, ap, bt} dict for the most recent player action
    ss          → 4-element score array
    pcsCount    → 4-element array of cards remaining per seat
    current_suit→ suit index of the trick lead
    mn          → trick number within the round
    rb          → round number
    fc          → face-up card index during dealing
"""
from __future__ import annotations

import copy
import logging
from typing import Optional

from .card_mapping import (
    decode_hand_bitmask,
    index_to_card,
    suit_idx_to_symbol,
    MODE_MAP,
)
from .models import GameEvent, BoardState, PlayerState
from .trick_extractor import _get_game_state_payload

logger = logging.getLogger(__name__)


# ── Stage mapping ─────────────────────────────────────────────────────

GSTG_TO_PHASE: dict[int, str] = {
    1: "BIDDING",
    2: "PLAYING",
    3: "TRICK_COMPLETE",
}


# ── GameReconstructor ─────────────────────────────────────────────────

class GameReconstructor:
    """Maintains a rolling game state by applying sequential SFS2X events.

    Usage::

        rc = GameReconstructor()
        for event in session.events:
            rc.apply_event(GameEvent(**event))
            snapshot = rc.get_snapshot()
    """

    def __init__(self) -> None:
        self.state = BoardState()
        self.reset()

    def reset(self) -> None:
        """Reset state to initial empty values."""
        self.state = BoardState(
            players=[
                PlayerState(seat=i, position=_seat_position(i))
                for i in range(4)
            ],
            center_cards=[],
            scores=[0, 0, 0, 0],
        )

    def apply_event(self, event: GameEvent) -> None:
        """Update internal state based on a decoded session event.

        Extracts the inner game-state dict via the same path that
        trick_extractor uses (``fields.p.p``), then maps all SFS2X fields
        to the BoardState model.
        """
        self.state.event_index += 1

        # Try to extract the inner game state payload
        event_dict = {
            "action": event.action,
            "fields": event.fields,
            "timestamp": event.timestamp,
        }
        inner = _get_game_state_payload(event_dict)

        if inner is None:
            # Not a game_state event — record the action name only
            self.state.last_action_desc = event.action
            return

        self._apply_game_state(inner, event.action)

    def _apply_game_state(self, gs: dict, action_name: str) -> None:
        """Apply a parsed game-state inner dict to the board.

        @param gs: The inner dict from ``fields.p.p``.
        @param action_name: Top-level action label for the event.
        """
        # ── Phase ──────────────────────────────────────────
        gStg = gs.get("gStg")
        if gStg is not None:
            self.state.phase = GSTG_TO_PHASE.get(gStg, "WAITING")

        # ── Game mode ──────────────────────────────────────
        gm = gs.get("gm")
        if gm:
            self.state.game_mode = MODE_MAP.get(gm.lower(), gm.upper())

        # ── Trump suit ─────────────────────────────────────
        ts = gs.get("ts")
        if ts is not None and isinstance(ts, (int, float)):
            self.state.trump_suit = suit_idx_to_symbol(int(ts))

        # ── Dealer (1-indexed → 0-indexed) ─────────────────
        dealer_raw = gs.get("dealer")
        if dealer_raw is not None and isinstance(dealer_raw, (int, float)):
            self.state.dealer_seat = int(dealer_raw) - 1
            for p in self.state.players:
                p.is_dealer = (p.seat == self.state.dealer_seat)

        # ── Current player / mover (1-indexed → 0-indexed) ─
        mover_raw = gs.get("mover")
        if mover_raw is not None and isinstance(mover_raw, (int, float)):
            self.state.current_player_seat = int(mover_raw) - 1

        # ── Scores ─────────────────────────────────────────
        ss = gs.get("ss")
        if isinstance(ss, list) and len(ss) == 4:
            self.state.scores = list(ss)

        # ── Trick / round numbers ──────────────────────────
        mn = gs.get("mn")
        if mn is not None and isinstance(mn, (int, float)):
            self.state.trick_number = int(mn)

        rb = gs.get("rb")
        if rb is not None and isinstance(rb, (int, float)):
            self.state.round_number = int(rb)

        # ── Lead suit ──────────────────────────────────────
        cs = gs.get("current_suit")
        if cs is not None and isinstance(cs, (int, float)):
            self.state.lead_suit = suit_idx_to_symbol(int(cs))

        # ── Cards remaining per seat ───────────────────────
        pcsCount = gs.get("pcsCount")
        if isinstance(pcsCount, list) and len(pcsCount) == 4:
            for i, cnt in enumerate(pcsCount):
                if i < len(self.state.players):
                    self.state.players[i].cards_remaining = cnt

        # ── Hand (bitmask for captured player) ─────────────
        pcs = gs.get("pcs")
        if pcs is not None and isinstance(pcs, (int, float)):
            cards = decode_hand_bitmask(int(pcs))
            # Assign to player 0 (the captured perspective) —
            # source only sends pcs for the local player.
            if self.state.players:
                self.state.players[0].hand = [
                    f"{c.rank}{c.suit}" for c in sorted(
                        cards, key=lambda c: (c.suit, c.rank)
                    )
                ]

        # ── Center cards (played_cards array) ──────────────
        played = gs.get("played_cards")
        if isinstance(played, list) and len(played) == 4:
            center: list[tuple[int, str]] = []
            for seat_idx, card_idx in enumerate(played):
                if isinstance(card_idx, (int, float)) and int(card_idx) >= 0:
                    card = index_to_card(int(card_idx))
                    if card is not None:
                        center.append((seat_idx, f"{card.rank}{card.suit}"))
            self.state.center_cards = center

        # ── Bidding from last_action ───────────────────────
        last_action = gs.get("last_action")
        if isinstance(last_action, dict):
            la_action = last_action.get("action", "")
            la_ap = last_action.get("ap")
            la_bt = last_action.get("bt")

            # Build human-readable description
            if la_action == "a_bid" and la_bt:
                seat = (int(la_ap) - 1) if la_ap else -1
                self.state.last_action_desc = f"Seat {seat} bid: {la_bt}"
                self.state.bidding_history.append({
                    "seat": seat,
                    "bid": la_bt,
                })
            elif la_action == "a_card_played":
                seat = (int(la_ap) - 1) if la_ap else -1
                self.state.last_action_desc = f"Seat {seat} played a card"
            elif la_action == "a_cards_eating":
                self.state.last_action_desc = "Trick collected"
            else:
                self.state.last_action_desc = la_action or action_name
        else:
            self.state.last_action_desc = action_name

    def get_snapshot(self) -> BoardState:
        """Return a deep copy of the current state."""
        return copy.deepcopy(self.state)


# ── Module-level convenience function ─────────────────────────────────

def reconstruct_timeline(events: list[GameEvent]) -> list[BoardState]:
    """Rebuild a full timeline of board states from a sequence of events.

    Only game_state / card_or_play events produce meaningful state
    changes; other events are still applied (incrementing event_index
    and recording the action name).

    @param events: Ordered list of GameEvent objects.
    @returns List of BoardState snapshots, one per input event.
    """
    reconstructor = GameReconstructor()
    timeline: list[BoardState] = []
    for event in events:
        reconstructor.apply_event(event)
        timeline.append(reconstructor.get_snapshot())
    return timeline


# ── Helpers ───────────────────────────────────────────────────────────

def _seat_position(seat: int) -> str:
    """Map a 0-indexed seat to a visual board position.

    @param seat: 0-3 seat index.
    @returns Position string for CSS layout.
    """
    return {0: "BOTTOM", 1: "RIGHT", 2: "TOP", 3: "LEFT"}.get(seat, "BOTTOM")
