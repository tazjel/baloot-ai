"""
Bid Extractor — Walk processed session events and extract structured
bidding sequences for each round.

The state machine detects bidding phases via ``gStg=1`` in game_state payloads
and tracks the ``last_action`` field to reconstruct the full bid sequence.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class ExtractedBid:
    """A single bid action from one player.

    @param seat: 0-indexed seat of the bidding player.
    @param action: Normalized bid type (PASS, SUN, HOKOM, THANY, WALA, etc.).
    @param raw_bt: Raw ``bt`` string from source (e.g. 'pass', 'sun', 'hokom2').
    @param bidding_round: Which bidding round (1, 2, or 3).
    @param timestamp: Epoch ms of the event.
    """
    seat: int
    action: str
    raw_bt: str
    bidding_round: int
    timestamp: float


@dataclass
class ExtractedBidSequence:
    """Complete bidding sequence for one game round.

    @param round_index: 0-based round number within the session.
    @param bids: Ordered list of bids in the sequence.
    @param final_mode: Resolved game mode ('SUN', 'HOKUM', or '' if all pass).
    @param final_trump_idx: Source suit index for trump (HOKUM); None for SUN.
    @param dealer_seat: 0-indexed dealer seat.
    @param caller_seat: 0-indexed seat of the player who won the bid; -1 if unknown.
    @param face_card_idx: Source card index of the face-up card during dealing; -1 if unknown.
    """
    round_index: int
    bids: list[ExtractedBid] = field(default_factory=list)
    final_mode: str = ""
    final_trump_idx: Optional[int] = None
    dealer_seat: int = -1
    caller_seat: int = -1
    face_card_idx: int = -1


@dataclass
class BidExtractionResult:
    """Complete bid extraction output from one session.

    @param session_path: Identification string for the source session.
    @param sequences: All detected bidding sequences.
    @param total_bids: Sum of individual bids across all sequences.
    @param total_events_scanned: Number of game_state payloads processed.
    @param extraction_warnings: Non-fatal issues encountered.
    """
    session_path: str
    sequences: list[ExtractedBidSequence] = field(default_factory=list)
    total_bids: int = 0
    total_events_scanned: int = 0
    extraction_warnings: list[str] = field(default_factory=list)


# ── Bid Type Normalization ──────────────────────────────────────────

# Map raw bt values to normalized action strings
BID_ACTION_MAP: dict[str, str] = {
    "pass": "PASS",
    "sun": "SUN",
    "hokom": "HOKOM",
    "hokom2": "HOKOM2",
    "hokomclose": "HOKOM_CLOSE",
    "thany": "THANY",
    "wala": "WALA",
    "waraq": "WARAQ",
    # Suit selections (HOKUM)
    "clubs": "CLUBS",
    "diamonds": "DIAMONDS",
    "hearts": "HEARTS",
    "spades": "SPADES",
}

# Mode-determining bid types
MODE_BID_TYPES: set[str] = {"sun", "hokom", "hokom2"}

# Suit selection bid types (trump selection)
SUIT_BID_TYPES: dict[str, int] = {
    "clubs": 2,
    "diamonds": 3,
    "hearts": 1,
    "spades": 0,
}

# Game mode from gm field
GM_TO_MODE: dict[str, str] = {
    "sun": "SUN",
    "ashkal": "SUN",
    "hokom": "HOKUM",
    "hokum": "HOKUM",
}


# ── Main Extraction Function ────────────────────────────────────────

def extract_bids(
    session_events: list[dict],
    session_path: str = "",
) -> BidExtractionResult:
    """Extract all bidding sequences from a processed session's event list.

    Walks events sequentially, identifying game_state payloads with gStg=1
    (bidding phase) and tracking last_action transitions.

    @param session_events: The 'events' list from a ProcessedSession.
    @param session_path: For identification in the result.
    @returns BidExtractionResult with all detected bidding sequences.
    """
    sequences: list[ExtractedBidSequence] = []
    warnings: list[str] = []
    events_scanned = 0

    current_seq: Optional[ExtractedBidSequence] = None
    round_index = 0
    last_bid_key: Optional[str] = None  # Dedup key to avoid double-counting

    for event in session_events:
        payload = _get_bidding_payload(event)
        if payload is None:
            # Check if we transitioned out of bidding (gStg != 1)
            playing_payload = _get_any_game_state_payload(event)
            if playing_payload is not None:
                events_scanned += 1
                gStg = playing_payload.get("gStg")
                if gStg is not None and gStg != 1 and current_seq is not None:
                    # Bidding ended — finalize the sequence from playing state
                    gm = playing_payload.get("gm")
                    if gm and not current_seq.final_mode:
                        current_seq.final_mode = GM_TO_MODE.get(gm, gm.upper())
                    ts = playing_payload.get("ts")
                    if ts is not None and current_seq.final_trump_idx is None:
                        current_seq.final_trump_idx = ts
                    sequences.append(current_seq)
                    current_seq = None
                    round_index += 1
                    last_bid_key = None
            continue

        events_scanned += 1
        gStg = payload.get("gStg")
        if gStg != 1:
            continue  # Not in bidding phase

        # ── Initialize new sequence if needed ────────────
        if current_seq is None:
            dealer_raw = payload.get("dealer")
            dealer = (dealer_raw - 1) if isinstance(dealer_raw, (int, float)) and dealer_raw > 0 else 0
            fc = payload.get("fc", -1)
            current_seq = ExtractedBidSequence(
                round_index=round_index,
                dealer_seat=dealer,
                face_card_idx=fc if isinstance(fc, int) else -1,
            )
            last_bid_key = None

        # ── Extract bid from last_action ─────────────────
        last_action = payload.get("last_action", {})
        if not isinstance(last_action, dict):
            continue

        if last_action.get("action") != "a_bid":
            continue

        bt = last_action.get("bt", "")
        ap = last_action.get("ap")  # 1-indexed acting player
        if not bt or ap is None:
            continue

        # Build dedup key to avoid processing same bid twice
        bid_key = f"{ap}:{bt}:{event.get('timestamp', 0)}"
        if bid_key == last_bid_key:
            continue
        last_bid_key = bid_key

        seat = (int(ap) - 1) if isinstance(ap, (int, float)) and ap > 0 else 0
        action = BID_ACTION_MAP.get(bt.lower(), bt.upper())
        rb = payload.get("rb", 1)
        if not isinstance(rb, int):
            rb = 1

        bid = ExtractedBid(
            seat=seat,
            action=action,
            raw_bt=bt,
            bidding_round=rb,
            timestamp=event.get("timestamp", 0.0),
        )
        current_seq.bids.append(bid)

        # ── Track mode and trump from state ──────────────
        gm = payload.get("gm")
        if gm and not current_seq.final_mode:
            current_seq.final_mode = GM_TO_MODE.get(gm, gm.upper())

        ts = payload.get("ts")
        if ts is not None and current_seq.final_trump_idx is None:
            current_seq.final_trump_idx = ts

        # Track caller from suit bids or mode-determining bids
        if bt.lower() in SUIT_BID_TYPES:
            current_seq.final_trump_idx = SUIT_BID_TYPES[bt.lower()]
            current_seq.caller_seat = seat
        elif bt.lower() in MODE_BID_TYPES:
            current_seq.caller_seat = seat

    # ── Finalize last sequence ────────────────────────────
    if current_seq is not None and current_seq.bids:
        sequences.append(current_seq)

    total_bids = sum(len(s.bids) for s in sequences)

    return BidExtractionResult(
        session_path=session_path,
        sequences=sequences,
        total_bids=total_bids,
        total_events_scanned=events_scanned,
        extraction_warnings=warnings,
    )


# ── Internal Helpers ─────────────────────────────────────────────────

def _get_bidding_payload(event: dict) -> Optional[dict]:
    """Extract game state payload if it's a bidding-phase event (gStg=1).

    @param event: A single event dict from ProcessedSession.events.
    @returns Inner dict if gStg=1, else None.
    """
    payload = _get_any_game_state_payload(event)
    if payload is None:
        return None
    if payload.get("gStg") != 1:
        return None
    return payload


def _get_any_game_state_payload(event: dict) -> Optional[dict]:
    """Extract the inner game state dict from a decoded event (any gStg).

    @param event: A single event dict from ProcessedSession.events.
    @returns Inner dict with keys like gStg, gm, ts, etc., or None.
    """
    action = event.get("action", "")
    fields = event.get("fields", {})
    if not isinstance(fields, dict):
        return None

    p = fields.get("p", {})
    if not isinstance(p, dict):
        return None

    # Accept game_state and card_or_play actions, or inner c=game_state marker
    c_val = p.get("c")
    if action not in ("game_state", "card_or_play", "bid_event") and c_val != "game_state":
        return None

    inner = p.get("p")
    if not isinstance(inner, dict):
        return None

    return inner
