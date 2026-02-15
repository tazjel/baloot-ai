"""
Point Tracker — Per-round point analysis comparing engine-computed card
points against expected totals.

Since the source WebSocket protocol does NOT broadcast cumulative match scores
(the ``ss`` field is a seat status code, not a score), point tracking is
engine-only: we compute raw Abnat from extracted tricks, apply the same
rounding formula as the game engine, and verify internal consistency.

Scoring formulas (from game_engine/logic/scoring_engine.py):
  SUN:  GP = round_custom(raw_abnat * 2 / 10)  — rounds up at >= 0.5
  HOKUM: GP = round_custom(raw_abnat / 10)      — rounds up only at > 0.5
  Target GP: SUN = 26, HOKUM = 16
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from game_engine.models.card import Card
from game_engine.models.constants import (
    POINT_VALUES_SUN,
    POINT_VALUES_HOKUM,
)
from gbaloot.core.card_mapping import index_to_card, suit_idx_to_symbol
from gbaloot.core.trick_extractor import ExtractedRound, ExtractionResult

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────

EXPECTED_CARD_ABNAT_SUN = 120    # Total card points (no last trick bonus)
EXPECTED_CARD_ABNAT_HOKUM = 152
LAST_TRICK_BONUS = 10
TARGET_GP_SUN = 26
TARGET_GP_HOKUM = 16


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class TrickPointDetail:
    """Point breakdown for a single trick.

    @param trick_number: 1-8 within the round.
    @param winner_seat: 0-indexed trick winner.
    @param card_points: Total card Abnat in this trick.
    @param winning_team: 'team_02' or 'team_13'.
    @param is_last_trick: True if this is trick 8.
    """
    trick_number: int
    winner_seat: int
    card_points: int
    winning_team: str
    is_last_trick: bool = False


@dataclass
class PointAnalysis:
    """Per-round point analysis.

    @param round_index: 0-based round number.
    @param game_mode: 'SUN' or 'HOKUM'.
    @param trick_details: Per-trick point breakdown.
    @param raw_abnat_team_02: Total card Abnat won by team 0+2.
    @param raw_abnat_team_13: Total card Abnat won by team 1+3.
    @param last_trick_team: Which team won the last trick (for bonus).
    @param total_abnat_team_02: Raw + last trick bonus for team 0+2.
    @param total_abnat_team_13: Raw + last trick bonus for team 1+3.
    @param gp_team_02: Game Points for team 0+2 after rounding.
    @param gp_team_13: Game Points for team 1+3 after rounding.
    @param card_points_consistent: Do raw card points sum to expected total?
    @param gp_sum_matches_target: Do GP sum to target (26 SUN / 16 HOKUM)?
    @param is_complete_round: True if 8 tricks present.
    @param notes: Additional context.
    """
    round_index: int
    game_mode: str
    trick_details: list[TrickPointDetail] = field(default_factory=list)
    raw_abnat_team_02: int = 0
    raw_abnat_team_13: int = 0
    last_trick_team: str = ""
    total_abnat_team_02: int = 0
    total_abnat_team_13: int = 0
    gp_team_02: int = 0
    gp_team_13: int = 0
    card_points_consistent: bool = False
    gp_sum_matches_target: bool = False
    is_complete_round: bool = False
    notes: str = ""


# ── Rounding Formulas ────────────────────────────────────────────────

def round_sun(raw_abnat: int) -> int:
    """Apply SUN rounding: GP = round_up_at_half(raw * 2 / 10).

    SUN rounds up at >= 0.5 (standard rounding).

    @param raw_abnat: Raw Abnat (card points + last trick bonus).
    @returns Game Points.
    """
    val = (raw_abnat * 2) / 10.0
    decimal_part = val % 1
    if decimal_part >= 0.5:
        return int(val) + 1
    return int(val)


def round_hokum(raw_abnat: int) -> int:
    """Apply HOKUM rounding: GP = round_up_at_strict_half(raw / 10).

    HOKUM rounds up only at > 0.5 (strict).

    @param raw_abnat: Raw Abnat (card points + last trick bonus).
    @returns Game Points.
    """
    val = raw_abnat / 10.0
    decimal_part = val % 1
    if decimal_part > 0.5:
        return int(val) + 1
    return int(val)


# ── Core Analysis Functions ──────────────────────────────────────────

def get_card_points(card: Card, game_mode: str, trump_suit: Optional[str]) -> int:
    """Calculate point value for a single card.

    @param card: Card object.
    @param game_mode: 'SUN' or 'HOKUM'.
    @param trump_suit: Trump suit symbol for HOKUM.
    @returns Point value (0-20).
    """
    if game_mode == "SUN":
        return POINT_VALUES_SUN.get(card.rank, 0)
    else:
        if trump_suit and card.suit == trump_suit:
            return POINT_VALUES_HOKUM.get(card.rank, 0)
        return POINT_VALUES_SUN.get(card.rank, 0)


def analyze_round_points(
    extracted_round: ExtractedRound,
    game_mode: str,
    trump_suit: Optional[str],
) -> PointAnalysis:
    """Analyze point distribution for a single extracted round.

    Accumulates card points by trick WINNER (not by who played the card).
    Adds last trick bonus to trick 8 winner's team.

    @param extracted_round: Round with tricks from trick_extractor.
    @param game_mode: 'SUN' or 'HOKUM'.
    @param trump_suit: Unicode suit symbol or None.
    @returns PointAnalysis with full breakdown.
    """
    trick_details: list[TrickPointDetail] = []
    raw_abnat_02 = 0
    raw_abnat_13 = 0
    num_tricks = len(extracted_round.tricks)
    is_complete = (num_tricks == 8)

    for trick in extracted_round.tricks:
        # Calculate total card points in this trick
        trick_pts = 0
        for seat, cidx in trick.cards_by_seat.items():
            card = index_to_card(cidx)
            if card is not None:
                trick_pts += get_card_points(card, game_mode, trump_suit)

        # Assign points to winning team
        winner = trick.winner_seat
        winning_team = "team_02" if winner in (0, 2) else "team_13"
        is_last = (trick.trick_number == num_tricks and is_complete)

        if winning_team == "team_02":
            raw_abnat_02 += trick_pts
        else:
            raw_abnat_13 += trick_pts

        trick_details.append(TrickPointDetail(
            trick_number=trick.trick_number,
            winner_seat=winner,
            card_points=trick_pts,
            winning_team=winning_team,
            is_last_trick=is_last,
        ))

    # Last trick bonus (only for complete rounds)
    last_trick_team = ""
    total_02 = raw_abnat_02
    total_13 = raw_abnat_13

    if is_complete and trick_details:
        last_detail = trick_details[-1]
        last_trick_team = last_detail.winning_team
        if last_trick_team == "team_02":
            total_02 += LAST_TRICK_BONUS
        else:
            total_13 += LAST_TRICK_BONUS

    # Check card point consistency
    expected = EXPECTED_CARD_ABNAT_SUN if game_mode == "SUN" else EXPECTED_CARD_ABNAT_HOKUM
    card_pts_total = raw_abnat_02 + raw_abnat_13
    card_consistent = (card_pts_total == expected) if is_complete else True  # Skip check for incomplete

    # Apply rounding
    if game_mode == "SUN":
        gp_02 = round_sun(total_02)
        gp_13 = round_sun(total_13)
        target_gp = TARGET_GP_SUN
    else:
        gp_02 = round_hokum(total_02)
        gp_13 = round_hokum(total_13)
        target_gp = TARGET_GP_HOKUM

    gp_matches = (gp_02 + gp_13 == target_gp) if is_complete else True

    notes = ""
    if is_complete and not card_consistent:
        notes += f"Card points sum {card_pts_total} != expected {expected}. "
    if is_complete and not gp_matches:
        notes += f"GP sum {gp_02 + gp_13} != target {target_gp}. "

    return PointAnalysis(
        round_index=extracted_round.round_index,
        game_mode=game_mode,
        trick_details=trick_details,
        raw_abnat_team_02=raw_abnat_02,
        raw_abnat_team_13=raw_abnat_13,
        last_trick_team=last_trick_team,
        total_abnat_team_02=total_02,
        total_abnat_team_13=total_13,
        gp_team_02=gp_02,
        gp_team_13=gp_13,
        card_points_consistent=card_consistent,
        gp_sum_matches_target=gp_matches,
        is_complete_round=is_complete,
        notes=notes.strip(),
    )


def analyze_session_points(
    extraction: ExtractionResult,
    mode_map: Optional[dict[int, tuple[str, Optional[str]]]] = None,
) -> list[PointAnalysis]:
    """Analyze points for all rounds in an extraction result.

    @param extraction: Full extraction result from trick_extractor.
    @param mode_map: Optional mapping of round_index → (game_mode, trump_suit).
                     If not provided, uses the round's own game_mode_raw and trump_suit_idx.
    @returns List of PointAnalysis, one per round.
    """
    from gbaloot.core.card_mapping import map_game_mode

    analyses: list[PointAnalysis] = []
    for rnd in extraction.rounds:
        if mode_map and rnd.round_index in mode_map:
            mode, trump = mode_map[rnd.round_index]
        else:
            try:
                mode = map_game_mode(rnd.game_mode_raw)
            except ValueError:
                mode = "SUN"
            trump = (
                suit_idx_to_symbol(rnd.trump_suit_idx)
                if rnd.trump_suit_idx is not None
                else None
            )

        analysis = analyze_round_points(rnd, mode, trump)
        analyses.append(analysis)

    return analyses
