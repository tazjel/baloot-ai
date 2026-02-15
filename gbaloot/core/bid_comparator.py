"""
Bid Comparator — Compare captured bidding decisions against our engine's
bidding heuristics to detect strategic divergences.

Uses the same scoring thresholds as ai_worker/strategies/bidding.py:
  SUN:  hand_score >= 26 (with specific point values)
  HOKUM: hand_score >= 45 (with Jack bonus)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from game_engine.models.card import Card
from game_engine.models.constants import POINT_VALUES_SUN, POINT_VALUES_HOKUM, SUITS
from gbaloot.core.card_mapping import decode_hand_bitmask, suit_idx_to_symbol
from gbaloot.core.bid_extractor import ExtractedBidSequence

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class BidComparison:
    """Comparison of one bidding sequence between source and engine.

    @param round_index: 0-based round number.
    @param source_mode: Mode the source game settled on ('SUN', 'HOKUM', or '').
    @param source_trump_idx: Source trump suit index, or None.
    @param source_caller_seat: Seat that won the bid in the source.
    @param engine_sun_score: Our engine's SUN score for the hand.
    @param engine_hokum_scores: Our engine's best HOKUM score per suit.
    @param engine_would_bid_sun: Would our engine bid SUN?
    @param engine_best_hokum_suit: Best HOKUM suit (symbol), or None.
    @param engine_would_bid_hokum: Would our engine bid HOKUM?
    @param mode_agrees: Does the engine agree on the final mode?
    @param hand_cards: List of cards in the hand (for debugging).
    @param notes: Additional context.
    """
    round_index: int
    source_mode: str
    source_trump_idx: Optional[int]
    source_caller_seat: int
    engine_sun_score: float
    engine_hokum_scores: dict[str, float]
    engine_would_bid_sun: bool
    engine_best_hokum_suit: Optional[str]
    engine_would_bid_hokum: bool
    mode_agrees: bool
    hand_cards: list[str] = field(default_factory=list)
    notes: str = ""


# ── Engine Bidding Heuristics ────────────────────────────────────────
# Simplified versions of ai_worker/strategies/bidding.py thresholds.
# We mirror the core logic without importing the full strategy module
# (which requires BotContext).

SUN_THRESHOLD = 26
HOKUM_THRESHOLD = 45

# SUN scoring: A=11, 10=10, K=4, Q=3, J=2 (same as POINT_VALUES_SUN)
SUN_POINT_MAP = POINT_VALUES_SUN

# HOKUM scoring per card (trump suit gets boosted values)
HOKUM_TRUMP_POINTS = {
    "J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3, "8": 0, "7": 0,
}
HOKUM_SIDE_POINTS = {
    "A": 11, "10": 10, "K": 4, "Q": 3, "J": 2, "9": 0, "8": 0, "7": 0,
}


def compute_sun_score(hand: list[Card]) -> float:
    """Compute SUN bidding score for a hand.

    @param hand: List of Card objects (typically 5 during first bid round).
    @returns Estimated SUN score.
    """
    score = 0.0
    for card in hand:
        score += SUN_POINT_MAP.get(card.rank, 0)
    return score


def compute_hokum_score(hand: list[Card], trump_suit: str) -> float:
    """Compute HOKUM bidding score for a hand with a given trump suit.

    Trump suit cards use HOKUM_TRUMP_POINTS; others use HOKUM_SIDE_POINTS.
    Jack of trump gets +10 bonus (presence bonus).

    @param hand: List of Card objects.
    @param trump_suit: Unicode suit symbol for candidate trump.
    @returns HOKUM score for this trump choice.
    """
    score = 0.0
    trump_count = 0
    has_jack = False
    for card in hand:
        if card.suit == trump_suit:
            score += HOKUM_TRUMP_POINTS.get(card.rank, 0)
            trump_count += 1
            if card.rank == "J":
                has_jack = True
        else:
            score += HOKUM_SIDE_POINTS.get(card.rank, 0)

    # Jack bonus: having J of trump is very strong
    if has_jack:
        score += 10

    return score


def evaluate_hand_for_bidding(hand: list[Card]) -> dict:
    """Evaluate a hand's bidding potential across all modes.

    @param hand: List of Card objects (5 or 8 cards).
    @returns Dict with sun_score, hokum_scores, would_bid_sun, best_hokum_suit, etc.
    """
    sun_score = compute_sun_score(hand)
    would_bid_sun = sun_score >= SUN_THRESHOLD

    hokum_scores: dict[str, float] = {}
    for suit in SUITS:
        hokum_scores[suit] = compute_hokum_score(hand, suit)

    best_suit = max(hokum_scores, key=hokum_scores.get)  # type: ignore
    best_hokum = hokum_scores[best_suit]
    would_bid_hokum = best_hokum >= HOKUM_THRESHOLD

    return {
        "sun_score": sun_score,
        "would_bid_sun": would_bid_sun,
        "hokum_scores": hokum_scores,
        "best_hokum_suit": best_suit if would_bid_hokum else None,
        "best_hokum_score": best_hokum,
        "would_bid_hokum": would_bid_hokum,
    }


# ── Comparison Functions ─────────────────────────────────────────────

def compare_bid_sequence(
    sequence: ExtractedBidSequence,
    hand_bitmask: Optional[int],
) -> Optional[BidComparison]:
    """Compare one bidding sequence against our engine's heuristics.

    @param sequence: Extracted bid sequence from the source.
    @param hand_bitmask: 64-bit pcs bitmask, or None if not available.
    @returns BidComparison, or None if hand data unavailable.
    """
    if hand_bitmask is None or hand_bitmask <= 0:
        return None

    hand = decode_hand_bitmask(hand_bitmask)
    if not hand:
        return None

    eval_result = evaluate_hand_for_bidding(hand)

    source_mode = sequence.final_mode
    engine_would_sun = eval_result["would_bid_sun"]
    engine_would_hokum = eval_result["would_bid_hokum"]
    engine_best_suit = eval_result["best_hokum_suit"]

    # Determine if engine agrees with the actual outcome
    if source_mode == "SUN":
        mode_agrees = engine_would_sun
    elif source_mode == "HOKUM":
        mode_agrees = engine_would_hokum
    else:
        # All pass / unknown — engine would also pass if neither threshold met
        mode_agrees = (not engine_would_sun and not engine_would_hokum)

    hand_strs = [f"{c.rank}{c.suit}" for c in hand]

    notes = ""
    if not mode_agrees:
        if source_mode == "SUN" and not engine_would_sun:
            notes = f"Source bid SUN but engine score {eval_result['sun_score']:.0f} < {SUN_THRESHOLD}"
        elif source_mode == "HOKUM" and not engine_would_hokum:
            notes = f"Source bid HOKUM but engine best score {eval_result['best_hokum_score']:.0f} < {HOKUM_THRESHOLD}"
        elif source_mode == "" and (engine_would_sun or engine_would_hokum):
            if engine_would_sun:
                notes = f"Source passed but engine would bid SUN (score {eval_result['sun_score']:.0f})"
            else:
                notes = f"Source passed but engine would bid HOKUM (score {eval_result['best_hokum_score']:.0f})"

    return BidComparison(
        round_index=sequence.round_index,
        source_mode=source_mode,
        source_trump_idx=sequence.final_trump_idx,
        source_caller_seat=sequence.caller_seat,
        engine_sun_score=eval_result["sun_score"],
        engine_hokum_scores=eval_result["hokum_scores"],
        engine_would_bid_sun=engine_would_sun,
        engine_best_hokum_suit=engine_best_suit,
        engine_would_bid_hokum=engine_would_hokum,
        mode_agrees=mode_agrees,
        hand_cards=hand_strs,
        notes=notes,
    )


def compare_session_bids(
    sequences: list[ExtractedBidSequence],
    hand_bitmasks: dict[int, int],
) -> list[BidComparison]:
    """Compare all bidding sequences in a session.

    @param sequences: Extracted bid sequences from bid_extractor.
    @param hand_bitmasks: Mapping of round_index → pcs bitmask for our seat.
    @returns List of BidComparison (one per sequence with hand data).
    """
    comparisons: list[BidComparison] = []
    for seq in sequences:
        bitmask = hand_bitmasks.get(seq.round_index)
        comp = compare_bid_sequence(seq, bitmask)
        if comp is not None:
            comparisons.append(comp)
    return comparisons
