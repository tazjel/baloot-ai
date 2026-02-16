"""
Archive Trick Extractor -- Convert source platform mobile archive events into
ExtractedTrick / ExtractedRound / ExtractionResult objects for the
GBaloot comparison pipeline.

This is a dedicated extractor that goes directly from the mobile JSON
format to our standard extraction dataclasses, bypassing the SFS2X
ProcessedSession format entirely.

Key insight (validated against 1095 rounds, 100% consistency):
- The ``e=6`` event's ``p`` field does NOT indicate the trick winner.
  It is used only as a trick boundary marker.
- The trick winner is computed from the cards using our engine's
  trick resolution logic (ORDER_SUN / ORDER_HOKUM).
- For HOKUM trump determination: use explicit suit bid (clubs/diamonds/
  hearts/spades) if present, otherwise use the ``fc`` (first card) suit
  from the ``e=1`` round start event.
- ``gm=3`` (ashkal) maps to SUN mode.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM

from gbaloot.core.card_mapping import (
    index_to_card,
    SUIT_SYMBOL_TO_IDX,
    VALID_BALOOT_INDICES,
)
from gbaloot.core.trick_extractor import (
    ExtractedTrick,
    ExtractedRound,
    ExtractionResult,
)
from gbaloot.tools.archive_parser import (
    parse_archive,
    ArchiveGame,
    ArchiveRound,
    EVT_CARD_PLAYED,
    EVT_TRICK_WON,
    EVT_KABOOT,
    EVT_ROUND_RESULT,
    EVT_ROUND_START,
    EVT_BID,
)

logger = logging.getLogger(__name__)

# Explicit suit bid actions -> suit symbol
BID_SUIT_MAP: dict[str, str] = {
    "clubs": "♣",
    "diamonds": "♦",
    "hearts": "♥",
    "spades": "♠",
}


# ── Main Extraction Function ────────────────────────────────────────

def extract_tricks_from_archive(
    archive_path: Path,
) -> ExtractionResult:
    """Extract all tricks from a source platform mobile archive file.

    Parses the archive, walks each round's event stream, collects card
    plays in groups of 4, and computes trick winners using the engine.

    @param archive_path: Path to a ``*.json`` archive file.
    @returns ExtractionResult with all detected rounds and tricks.
    """
    game = parse_archive(archive_path)
    return extract_tricks_from_game(game)


def extract_tricks_from_game(game: ArchiveGame) -> ExtractionResult:
    """Extract tricks from an already-parsed ArchiveGame.

    @param game: Parsed archive game object.
    @returns ExtractionResult with all rounds and tricks.
    """
    result_rounds: list[ExtractedRound] = []
    all_warnings: list[str] = list(game.warnings)
    total_events = 0

    for arch_round in game.rounds:
        extracted, events_scanned, round_warnings = _extract_round(
            arch_round, game.file_path
        )
        if extracted is not None:
            result_rounds.append(extracted)
        total_events += events_scanned
        all_warnings.extend(round_warnings)

    total_tricks = sum(len(r.tricks) for r in result_rounds)

    return ExtractionResult(
        session_path=game.file_path,
        rounds=result_rounds,
        total_tricks=total_tricks,
        total_events_scanned=total_events,
        extraction_warnings=all_warnings,
    )


# ── Round Extraction ────────────────────────────────────────────────

def _extract_round(
    arch_round: ArchiveRound,
    session_path: str,
) -> tuple[Optional[ExtractedRound], int, list[str]]:
    """Extract tricks from a single archive round.

    Walks the event stream, collecting e=4 (card played) events into
    groups.  When e=6 (trick boundary) appears, the accumulated cards
    form one complete trick.  The winner is computed from the engine's
    trick resolution logic, NOT from the e=6 p field.

    Trump suit determination for HOKUM:
    1. If an explicit suit bid exists (clubs/diamonds/hearts/spades),
       use that suit.
    2. Otherwise, use the suit of the first card (fc) from e=1.

    @param arch_round: Parsed ArchiveRound with events and metadata.
    @param session_path: For warning messages.
    @returns (ExtractedRound or None, events_scanned, warnings).
    """
    ri = arch_round.round_index
    warnings: list[str] = []
    events_scanned = 0

    game_mode_raw = _mode_to_raw(arch_round.game_mode)
    game_mode = arch_round.game_mode or "SUN"

    # Resolve trump suit for HOKUM
    trump_symbol = _resolve_trump(arch_round.events, game_mode)
    trump_suit_idx = SUIT_SYMBOL_TO_IDX.get(trump_symbol) if trump_symbol else None

    # Determine dealer
    dealer_seat = _find_dealer(arch_round.events)

    tricks: list[ExtractedTrick] = []
    trick_number = 0

    # Accumulate card plays for the current trick
    # Store as (player_1indexed, card_index) to preserve play order
    current_plays: list[tuple[int, int]] = []

    # Track cumulative scores from round result
    scores_snapshot: list[int] = [0, 0, 0, 0]

    for evt in arch_round.events:
        etype = evt.get("e")
        events_scanned += 1

        if etype == EVT_CARD_PLAYED:
            player_1idx = evt.get("p", 0)
            card_idx = evt.get("c", -1)

            if player_1idx < 1 or player_1idx > 4:
                warnings.append(
                    f"Round {ri}: invalid player seat {player_1idx} in card play"
                )
                continue

            if card_idx not in VALID_BALOOT_INDICES:
                warnings.append(
                    f"Round {ri}: invalid card index {card_idx} "
                    f"from P{player_1idx}"
                )
                continue

            current_plays.append((player_1idx, card_idx))

        elif etype == EVT_TRICK_WON:
            # e=6 is a trick boundary marker only; p field is NOT the winner
            if len(current_plays) != 4:
                if current_plays:
                    warnings.append(
                        f"Round {ri} trick {trick_number + 1}: "
                        f"only {len(current_plays)} cards before trick boundary"
                    )
                current_plays.clear()
                continue

            trick_number += 1

            # Build cards_by_seat (0-indexed)
            cards_by_seat: dict[int, int] = {}
            for p1idx, cidx in current_plays:
                seat = p1idx - 1
                cards_by_seat[seat] = cidx

            if len(cards_by_seat) != 4:
                warnings.append(
                    f"Round {ri} trick {trick_number}: "
                    f"duplicate seat in card plays, "
                    f"{len(cards_by_seat)} unique seats"
                )
                current_plays.clear()
                continue

            # Lead suit from the first card played in this trick
            lead_card = index_to_card(current_plays[0][1])
            if lead_card is not None:
                lead_suit_idx = SUIT_SYMBOL_TO_IDX.get(lead_card.suit, -1)
            else:
                lead_suit_idx = -1

            # Compute winner using engine logic
            winner_seat = _compute_winner(
                current_plays, game_mode, trump_symbol
            )

            trick = ExtractedTrick(
                trick_number=trick_number,
                round_index=ri,
                cards_by_seat=cards_by_seat,
                winner_seat=winner_seat,
                lead_suit_idx=lead_suit_idx,
                game_mode_raw=game_mode_raw,
                trump_suit_idx=trump_suit_idx,
                scores_snapshot=list(scores_snapshot),
                timestamp=0.0,
            )
            tricks.append(trick)
            current_plays.clear()

        elif etype == EVT_KABOOT:
            current_plays.clear()

        elif etype == EVT_ROUND_RESULT:
            rs = evt.get("rs", {})
            if isinstance(rs, dict):
                s1 = rs.get("s1", 0) or 0
                s2 = rs.get("s2", 0) or 0
                scores_snapshot = [s1, s2, s1, s2]

    if current_plays:
        warnings.append(
            f"Round {ri}: {len(current_plays)} leftover cards after all events"
        )

    if not tricks:
        return None, events_scanned, warnings

    scores_before: list[int] = [0, 0, 0, 0]
    scores_after: list[int] = list(scores_snapshot)

    if arch_round.result:
        rs = arch_round.result
        s1_after = rs.get("s1", 0) or 0
        s2_after = rs.get("s2", 0) or 0
        scores_after = [s1_after, s2_after, s1_after, s2_after]

    extracted_round = ExtractedRound(
        round_index=ri,
        game_mode_raw=game_mode_raw,
        trump_suit_idx=trump_suit_idx,
        dealer_seat=dealer_seat,
        tricks=tricks,
        scores_before=scores_before,
        scores_after=scores_after,
    )

    return extracted_round, events_scanned, warnings


# ── Helpers ──────────────────────────────────────────────────────────

def _compute_winner(
    plays: list[tuple[int, int]],
    game_mode: str,
    trump_symbol: Optional[str],
) -> int:
    """Compute the trick winner using our engine's resolution logic.

    @param plays: List of (player_1indexed, card_index) in play order.
    @param game_mode: 'SUN' or 'HOKUM'.
    @param trump_symbol: Trump suit symbol for HOKUM, None for SUN.
    @returns 0-indexed seat of the winner.
    """
    lead_card = index_to_card(plays[0][1])
    if lead_card is None:
        return plays[0][0] - 1
    lead_suit = lead_card.suit

    best_seat = plays[0][0] - 1
    best_strength = -1

    for p1idx, cidx in plays:
        card = index_to_card(cidx)
        if card is None:
            continue

        strength = -1
        if game_mode == "HOKUM" and trump_symbol and card.suit == trump_symbol:
            strength = 100 + ORDER_HOKUM.index(card.rank)
        elif card.suit == lead_suit:
            strength = ORDER_SUN.index(card.rank)

        if strength > best_strength:
            best_strength = strength
            best_seat = p1idx - 1

    return best_seat


def _resolve_trump(
    events: list[dict],
    game_mode: str,
) -> Optional[str]:
    """Determine trump suit for a round.

    For SUN mode, returns None.
    For HOKUM mode:
    1. If an explicit suit bid exists (clubs/diamonds/hearts/spades),
       use that suit.
    2. Otherwise, use the suit of the first card (fc) from e=1.

    @param events: Raw event list for one round.
    @param game_mode: 'SUN' or 'HOKUM'.
    @returns Suit symbol string, or None for SUN.
    """
    if game_mode != "HOKUM":
        return None

    # Check for explicit suit bid
    for evt in events:
        if evt.get("e") == EVT_BID:
            b = evt.get("b", "")
            suit = BID_SUIT_MAP.get(b)
            if suit is not None:
                return suit

    # Fall back to fc (first card) suit
    for evt in events:
        if evt.get("e") == EVT_ROUND_START:
            fc = evt.get("fc")
            if fc is not None:
                fc_card = index_to_card(fc)
                if fc_card is not None:
                    return fc_card.suit

    return None


def _mode_to_raw(mode: Optional[str]) -> str:
    """Convert our mode string to a raw mode string for ExtractedTrick.

    The comparator's map_game_mode() handles: sun->SUN, hokom->HOKUM.

    @param mode: 'SUN' or 'HOKUM' or None.
    @returns Raw mode string compatible with map_game_mode().
    """
    if mode == "SUN":
        return "sun"
    elif mode == "HOKUM":
        return "hokom"
    return "sun"


def _find_dealer(events: list[dict]) -> int:
    """Find the dealer seat from round start event (e=1).

    @param events: Raw event list for one round.
    @returns 0-indexed dealer seat (defaults to 0 if not found).
    """
    for evt in events:
        if evt.get("e") == EVT_ROUND_START:
            p = evt.get("p", 1)
            if isinstance(p, int) and 1 <= p <= 4:
                return (p - 2) % 4
    return 0
