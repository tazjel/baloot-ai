"""
Trick Extractor — Walk processed session events and extract structured
trick-by-trick data suitable for engine comparison.

The state machine detects trick boundaries via ``a_cards_eating`` events
and round boundaries via pcsCount resets or dealer changes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class ExtractedTrick:
    """One complete trick extracted from source session data.

    @param trick_number: 1-8 within the round.
    @param round_index: Which round this belongs to (0-based).
    @param cards_by_seat: Mapping of seat index (0-3) to source card index.
    @param winner_seat: 0-indexed seat that won the trick.
    @param lead_suit_idx: source suit index from the current_suit field.
    @param game_mode_raw: Raw gm value ('ashkal', 'hokom', etc.).
    @param trump_suit_idx: source suit index for trump; None for SUN.
    @param scores_snapshot: Per-seat score array at trick completion.
    @param timestamp: Epoch ms of the completing game_state event.
    """
    trick_number: int
    round_index: int
    cards_by_seat: dict[int, int]
    winner_seat: int
    lead_suit_idx: int
    game_mode_raw: str
    trump_suit_idx: Optional[int]
    scores_snapshot: list[int]
    timestamp: float


@dataclass
class ExtractedRound:
    """A full round (up to 8 tricks) from one deal.

    @param round_index: 0-based round number within the session.
    @param game_mode_raw: source mode string.
    @param trump_suit_idx: Trump suit for HOKUM; None for SUN.
    @param dealer_seat: 0-indexed dealer seat.
    @param tricks: Ordered list of ExtractedTrick for this round.
    @param scores_before: Per-seat score array at round start.
    @param scores_after: Per-seat score array at round end.
    @param bid_sequence: Optional extracted bidding sequence for this round (G2).
    """
    round_index: int
    game_mode_raw: str
    trump_suit_idx: Optional[int]
    dealer_seat: int
    tricks: list[ExtractedTrick] = field(default_factory=list)
    scores_before: list[int] = field(default_factory=list)
    scores_after: list[int] = field(default_factory=list)
    bid_sequence: Optional[object] = None  # ExtractedBidSequence (avoid circular import)


@dataclass
class ExtractionResult:
    """Complete extraction output from one session.

    @param session_path: Identification string for the source session.
    @param rounds: All detected rounds with their tricks.
    @param total_tricks: Sum of tricks across all rounds.
    @param total_events_scanned: Number of game_state payloads processed.
    @param extraction_warnings: Non-fatal issues encountered.
    """
    session_path: str
    rounds: list[ExtractedRound] = field(default_factory=list)
    total_tricks: int = 0
    total_events_scanned: int = 0
    extraction_warnings: list[str] = field(default_factory=list)


# ── Main Extraction Function ────────────────────────────────────────

def extract_tricks(
    session_events: list[dict],
    session_path: str = "",
) -> ExtractionResult:
    """Extract all tricks from a processed session's event list.

    Walks events sequentially, identifying game_state payloads and
    detecting trick boundaries via played_cards transitions.

    @param session_events: The 'events' list from a ProcessedSession.
    @param session_path: For identification in the result.
    @returns ExtractionResult with all detected rounds and tricks.
    """
    result_rounds: list[ExtractedRound] = []
    current_round_tricks: list[ExtractedTrick] = []
    round_index = 0
    trick_number = 0
    warnings: list[str] = []
    events_scanned = 0

    # Tracking state
    last_complete_state: Optional[dict] = None   # state where all 4 played_cards filled
    prev_state: Optional[dict] = None
    current_round_mode: Optional[str] = None
    current_round_trump: Optional[int] = None
    current_round_dealer: Optional[int] = None
    scores_at_round_start: list[int] = []

    for event in session_events:
        payload = _get_game_state_payload(event)
        if payload is None:
            continue
        events_scanned += 1

        played = payload.get("played_cards", [])
        last_action = payload.get("last_action", {})
        if not isinstance(last_action, dict):
            last_action = {}

        # ── Detect round boundary ────────────────────────────
        if prev_state and _detect_round_boundary(prev_state, payload):
            if current_round_tricks:
                result_rounds.append(ExtractedRound(
                    round_index=round_index,
                    game_mode_raw=current_round_mode or "",
                    trump_suit_idx=current_round_trump,
                    dealer_seat=current_round_dealer or 0,
                    tricks=current_round_tricks,
                    scores_before=scores_at_round_start,
                    scores_after=prev_state.get("ss", []),
                ))
                round_index += 1
                current_round_tricks = []
                trick_number = 0
            scores_at_round_start = list(payload.get("ss", []))
            current_round_mode = payload.get("gm")
            current_round_trump = payload.get("ts")
            current_round_dealer = payload.get("dealer")

        # ── Initialize round tracking ────────────────────────
        if current_round_mode is None:
            current_round_mode = payload.get("gm")
            current_round_trump = payload.get("ts")
            current_round_dealer = payload.get("dealer")
            scores_at_round_start = list(payload.get("ss", []))

        # ── Track full tricks ────────────────────────────────
        if len(played) == 4 and _is_trick_complete(played):
            last_complete_state = payload

        # ── Detect trick completion via a_cards_eating ───────
        if last_action.get("action") == "a_cards_eating" and last_complete_state:
            trick_number += 1
            # mover field in the eating state = next leader = trick winner
            # mover is 1-indexed: mover=1 → seat 0, mover=4 → seat 3
            mover_raw = payload.get("mover")
            if mover_raw is not None and isinstance(mover_raw, (int, float)):
                winner_seat = int(mover_raw) - 1
            else:
                # Fallback: use ap from last_action (also 1-indexed)
                winner_ap = last_action.get("ap", 1)
                winner_seat = (winner_ap - 1) if winner_ap > 0 else 0

            cards_by_seat: dict[int, int] = {}
            complete_played = last_complete_state.get("played_cards", [])
            for seat_idx, card_idx in enumerate(complete_played):
                if isinstance(card_idx, int) and card_idx >= 0:
                    cards_by_seat[seat_idx] = card_idx

            if len(cards_by_seat) == 4:
                trick = ExtractedTrick(
                    trick_number=trick_number,
                    round_index=round_index,
                    cards_by_seat=cards_by_seat,
                    winner_seat=winner_seat,
                    lead_suit_idx=last_complete_state.get("current_suit", -1),
                    game_mode_raw=last_complete_state.get("gm", current_round_mode or ""),
                    trump_suit_idx=last_complete_state.get("ts", current_round_trump),
                    scores_snapshot=list(payload.get("ss", [])),
                    timestamp=event.get("timestamp", 0.0),
                )
                current_round_tricks.append(trick)
            else:
                warnings.append(
                    f"Round {round_index} trick {trick_number}: "
                    f"only {len(cards_by_seat)} cards in played_cards"
                )

            last_complete_state = None  # Reset for next trick

        prev_state = payload

    # ── Finalize last round ──────────────────────────────────
    if current_round_tricks:
        result_rounds.append(ExtractedRound(
            round_index=round_index,
            game_mode_raw=current_round_mode or "",
            trump_suit_idx=current_round_trump,
            dealer_seat=current_round_dealer or 0,
            tricks=current_round_tricks,
            scores_before=scores_at_round_start,
            scores_after=prev_state.get("ss", []) if prev_state else [],
        ))

    total = sum(len(r.tricks) for r in result_rounds)

    return ExtractionResult(
        session_path=session_path,
        rounds=result_rounds,
        total_tricks=total,
        total_events_scanned=events_scanned,
        extraction_warnings=warnings,
    )


# ── Internal Helpers ─────────────────────────────────────────────────

def _get_game_state_payload(event: dict) -> Optional[dict]:
    """Extract the inner game state dict from a decoded event.

    source nests the state at ``fields.p.p`` for game_state events.
    Some events arrive under different action labels but share the same
    inner structure.

    @param event: A single event dict from ProcessedSession.events.
    @returns Inner dict with keys like ss, played_cards, gm, etc., or None.
    """
    action = event.get("action", "")
    fields = event.get("fields", {})
    if not isinstance(fields, dict):
        return None

    # Direct game_state or card_or_play actions
    p = fields.get("p", {})
    if not isinstance(p, dict):
        return None

    # Check for game_state marker in nested structure
    c_val = p.get("c")
    if action not in ("game_state", "card_or_play") and c_val != "game_state":
        return None

    inner = p.get("p")
    if not isinstance(inner, dict):
        return None

    # Validate it contains expected game state fields
    if "played_cards" not in inner and "pcsCount" not in inner:
        return None

    return inner


def _is_trick_complete(played_cards: list) -> bool:
    """Check if all 4 seats have non-negative card indices.

    @param played_cards: Array of 4 card indices (-1 = empty slot).
    @returns True if all slots are filled (no -1 values).
    """
    if len(played_cards) != 4:
        return False
    return all(isinstance(v, (int, float)) and v >= 0 for v in played_cards)


def _detect_round_boundary(prev_state: dict, curr_state: dict) -> bool:
    """Detect if a new round started between two consecutive states.

    Heuristics:
    - pcsCount resets to higher values (new deal)
    - dealer changes AND cards are back to full count
    - game mode changes

    @param prev_state: Previous game state inner dict.
    @param curr_state: Current game state inner dict.
    @returns True if a round boundary is detected.
    """
    prev_pcs = prev_state.get("pcsCount", [])
    curr_pcs = curr_state.get("pcsCount", [])

    # Cards dealt — pcsCount jumps back to high values
    if prev_pcs and curr_pcs and len(prev_pcs) == 4 and len(curr_pcs) == 4:
        prev_total = sum(prev_pcs)
        curr_total = sum(curr_pcs)
        # If previous state had fewer total cards and current resets to ~32
        # (or at least significantly more), it's a new deal
        if prev_total < 28 and curr_total >= 28:
            return True

    # Dealer change with full hand count
    prev_dealer = prev_state.get("dealer")
    curr_dealer = curr_state.get("dealer")
    if prev_dealer is not None and curr_dealer is not None:
        if prev_dealer != curr_dealer and curr_pcs and sum(curr_pcs) >= 28:
            return True

    return False
