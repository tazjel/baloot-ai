"""
Game Comparator — Dual-engine comparison between source captured state
and our game engine's TrickResolver logic.

Feeds the same card plays through both engines, detecting divergences
to validate engine correctness across real game sessions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from game_engine.models.card import Card
from game_engine.models.constants import (
    ORDER_SUN,
    ORDER_HOKUM,
    POINT_VALUES_SUN,
    POINT_VALUES_HOKUM,
)
from gbaloot.core.card_mapping import (
    index_to_card,
    suit_idx_to_symbol,
    map_game_mode,
    VALID_BALOOT_INDICES,
)
from gbaloot.core.trick_extractor import (
    extract_tricks,
    ExtractedTrick,
    ExtractionResult,
)

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class TrickComparison:
    """Per-trick comparison between source and our engine.

    @param trick_number: Trick number within the round (1-8).
    @param round_index: 0-based round number.
    @param cards: Human-readable cards per seat.
    @param lead_suit: Unicode suit symbol for the lead.
    @param game_mode: 'SUN' or 'HOKUM'.
    @param trump_suit: Unicode suit for HOKUM, None for SUN.
    @param source_winner_seat: Seat that source says won.
    @param engine_winner_seat: Seat that our engine says should win.
    @param engine_points: Sum of card points for this trick.
    @param winner_agrees: True if both engines agree on winner.
    @param divergence_type: None or 'TRICK_WINNER'.
    @param notes: Additional context.
    """
    trick_number: int
    round_index: int
    cards: list[dict]
    lead_suit: str
    game_mode: str
    trump_suit: Optional[str]
    source_winner_seat: int
    engine_winner_seat: int
    engine_points: int
    winner_agrees: bool
    divergence_type: Optional[str] = None
    notes: str = ""


@dataclass
class Divergence:
    """A single engine disagreement for the edge case collector.

    @param id: Unique identifier (e.g., 'div_0001').
    @param session_path: Source session file path.
    @param round_index: 0-based round number.
    @param trick_number: Trick number within round.
    @param divergence_type: Category of disagreement.
    @param severity: 'HIGH', 'MEDIUM', or 'LOW'.
    @param game_mode: 'SUN' or 'HOKUM'.
    @param trump_suit: Trump suit symbol or None.
    @param cards_played: Human-readable card list.
    @param lead_suit: Lead suit symbol.
    @param source_result: String description of source's verdict.
    @param engine_result: String description of our engine's verdict.
    @param notes: Additional context.
    """
    id: str
    session_path: str
    round_index: int
    trick_number: int
    divergence_type: str
    severity: str
    game_mode: str
    trump_suit: Optional[str]
    cards_played: list[dict]
    lead_suit: str
    source_result: str
    engine_result: str
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialize to plain dict for JSON export."""
        return asdict(self)


@dataclass
class ComparisonReport:
    """Full comparison report for one session.

    @param session_path: Source session identification.
    @param generated_at: ISO timestamp of report generation.
    @param rounds_compared: Number of rounds processed.
    @param total_tricks: Total tricks analyzed.
    @param trick_comparisons: Per-trick comparison results.
    @param winner_agreement_pct: Percentage of tricks where engines agree.
    @param total_divergences: Count of disagreements.
    @param divergence_breakdown: Counts by divergence type.
    @param engine_points_team_02: Points for seats 0+2 team.
    @param engine_points_team_13: Points for seats 1+3 team.
    @param extraction_warnings: Warnings from trick extraction.
    @param point_analyses: Per-round point analysis (G3).
    @param point_consistency_pct: Percentage of complete rounds with correct card point totals.
    """
    session_path: str
    generated_at: str
    rounds_compared: int
    total_tricks: int
    trick_comparisons: list[TrickComparison]
    winner_agreement_pct: float
    total_divergences: int
    divergence_breakdown: dict[str, int]
    engine_points_team_02: int
    engine_points_team_13: int
    extraction_warnings: list[str]
    point_analyses: list = field(default_factory=list)
    point_consistency_pct: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return asdict(self)


# ── Core Comparison Engine ───────────────────────────────────────────

class GameComparator:
    """Dual-engine comparison between source state and our TrickResolver."""

    def __init__(self):
        self.divergences: list[Divergence] = []
        self._div_counter: int = 0

    def compare_session(
        self,
        session_events: list[dict],
        session_path: str = "",
    ) -> ComparisonReport:
        """Run full comparison for one processed session.

        @param session_events: The 'events' list from a ProcessedSession.
        @param session_path: Identification string.
        @returns ComparisonReport with all per-trick results and metrics.
        """
        extraction = extract_tricks(session_events, session_path)

        comparisons: list[TrickComparison] = []
        points_team_02 = 0
        points_team_13 = 0

        for rnd in extraction.rounds:
            try:
                mode = map_game_mode(rnd.game_mode_raw)
            except ValueError:
                mode = "SUN"  # Default fallback
            trump_suit = (
                suit_idx_to_symbol(rnd.trump_suit_idx)
                if rnd.trump_suit_idx is not None
                else None
            )

            for trick in rnd.tricks:
                tc = self._compare_trick(trick, mode, trump_suit, session_path)
                comparisons.append(tc)

                # Accumulate team points
                for card_info in tc.cards:
                    seat = card_info["seat"]
                    pts = card_info.get("points", 0)
                    if seat in (0, 2):
                        points_team_02 += pts
                    else:
                        points_team_13 += pts

        # Aggregate metrics
        total = len(comparisons)
        agrees = sum(1 for c in comparisons if c.winner_agrees)
        pct = (agrees / total * 100.0) if total > 0 else 0.0

        divergence_breakdown: dict[str, int] = {}
        for c in comparisons:
            if c.divergence_type:
                divergence_breakdown[c.divergence_type] = (
                    divergence_breakdown.get(c.divergence_type, 0) + 1
                )

        # G3: Point analysis per round
        point_analyses = []
        point_consistency_pct = 0.0
        try:
            from gbaloot.core.point_tracker import analyze_session_points
            point_analyses = analyze_session_points(extraction)
            complete = [pa for pa in point_analyses if pa.is_complete_round]
            if complete:
                consistent = sum(1 for pa in complete if pa.card_points_consistent)
                point_consistency_pct = round(consistent / len(complete) * 100.0, 1)
        except Exception as e:
            logger.warning("Point analysis failed: %s", e)

        return ComparisonReport(
            session_path=session_path,
            generated_at=datetime.now().isoformat(),
            rounds_compared=len(extraction.rounds),
            total_tricks=total,
            trick_comparisons=comparisons,
            winner_agreement_pct=round(pct, 1),
            total_divergences=total - agrees,
            divergence_breakdown=divergence_breakdown,
            engine_points_team_02=points_team_02,
            engine_points_team_13=points_team_13,
            extraction_warnings=extraction.extraction_warnings,
            point_analyses=point_analyses,
            point_consistency_pct=point_consistency_pct,
        )

    def compare_session_file(self, session_file: Path) -> ComparisonReport:
        """Load a ProcessedSession from disk and compare it.

        @param session_file: Path to a *_processed.json file.
        @returns ComparisonReport.
        """
        from gbaloot.core.models import ProcessedSession

        session = ProcessedSession.load(session_file)
        return self.compare_session(session.events, str(session_file))

    def compare_all_sessions(self, sessions_dir: Path) -> list[ComparisonReport]:
        """Compare all processed session files in a directory.

        @param sessions_dir: Directory containing *_processed.json files.
        @returns List of ComparisonReport, one per session.
        """
        reports: list[ComparisonReport] = []
        files = sorted(sessions_dir.glob("*_processed.json"))

        for f in files:
            try:
                report = self.compare_session_file(f)
                reports.append(report)
            except Exception as e:
                logger.warning("Failed to compare session %s: %s", f.name, e)

        return reports

    def get_divergences(self) -> list[Divergence]:
        """Return all divergences accumulated across all comparisons."""
        return list(self.divergences)

    # ── Internal Methods ─────────────────────────────────────────

    def _compare_trick(
        self,
        trick: ExtractedTrick,
        game_mode: str,
        trump_suit: Optional[str],
        session_path: str,
    ) -> TrickComparison:
        """Compare a single trick against our engine logic.

        @param trick: ExtractedTrick from trick_extractor.
        @param game_mode: 'SUN' or 'HOKUM'.
        @param trump_suit: Unicode suit symbol or None.
        @param session_path: For divergence recording.
        @returns TrickComparison with full comparison results.
        """
        lead_suit = suit_idx_to_symbol(trick.lead_suit_idx)

        # Convert card indices to Card objects
        cards_by_seat: dict[int, Card] = {}
        cards_info: list[dict] = []
        for seat in sorted(trick.cards_by_seat):
            cidx = trick.cards_by_seat[seat]
            card = index_to_card(cidx)
            if card is None:
                continue
            cards_by_seat[seat] = card
            pts = _get_card_points(card, game_mode, trump_suit)
            cards_info.append({
                "seat": seat,
                "index": cidx,
                "card": f"{card.rank}{card.suit}",
                "points": pts,
            })

        # Compute our engine's trick winner
        engine_winner = _compute_winner_locally(
            cards_by_seat, lead_suit, game_mode, trump_suit
        )
        engine_points = sum(c.get("points", 0) for c in cards_info)

        # Compare
        winner_agrees = engine_winner == trick.winner_seat
        divergence_type = None if winner_agrees else "TRICK_WINNER"

        notes = ""
        if not winner_agrees:
            notes = (
                f"Engine: seat {engine_winner} "
                f"({cards_by_seat.get(engine_winner, '?')}), "
                f"source: seat {trick.winner_seat} "
                f"({cards_by_seat.get(trick.winner_seat, '?')})"
            )

        tc = TrickComparison(
            trick_number=trick.trick_number,
            round_index=trick.round_index,
            cards=cards_info,
            lead_suit=lead_suit,
            game_mode=game_mode,
            trump_suit=trump_suit,
            source_winner_seat=trick.winner_seat,
            engine_winner_seat=engine_winner,
            engine_points=engine_points,
            winner_agrees=winner_agrees,
            divergence_type=divergence_type,
            notes=notes,
        )

        if not winner_agrees:
            self._record_divergence(trick, tc, session_path)

        return tc

    def _record_divergence(
        self,
        trick: ExtractedTrick,
        comparison: TrickComparison,
        session_path: str,
    ) -> None:
        """Create a Divergence record and append to the collection."""
        self._div_counter += 1
        div = Divergence(
            id=f"div_{self._div_counter:04d}",
            session_path=session_path,
            round_index=comparison.round_index,
            trick_number=comparison.trick_number,
            divergence_type=comparison.divergence_type or "UNKNOWN",
            severity=_classify_severity(comparison),
            game_mode=comparison.game_mode,
            trump_suit=comparison.trump_suit,
            cards_played=comparison.cards,
            lead_suit=comparison.lead_suit,
            source_result=f"winner=seat{comparison.source_winner_seat}",
            engine_result=f"winner=seat{comparison.engine_winner_seat}",
            notes=comparison.notes,
        )
        self.divergences.append(div)


# ── Pure Helper Functions ────────────────────────────────────────────

def _compute_winner_locally(
    cards_by_seat: dict[int, Card],
    lead_suit: str,
    game_mode: str,
    trump_suit: Optional[str],
) -> int:
    """Determine trick winner using the same logic as TrickResolver.

    Directly computes strength per card and returns the winning seat index.
    Mirrors ``game_engine.logic.trick_resolver.TrickResolver.get_trick_winner``.

    @param cards_by_seat: Mapping of seat (0-3) to Card object.
    @param lead_suit: Unicode suit symbol of the lead.
    @param game_mode: 'SUN' or 'HOKUM'.
    @param trump_suit: Unicode suit symbol for HOKUM; None for SUN.
    @returns 0-indexed seat of the trick winner.
    """
    best_seat = -1
    best_strength = -1

    for seat, card in cards_by_seat.items():
        strength = -1
        if game_mode == "SUN":
            if card.suit == lead_suit:
                strength = ORDER_SUN.index(card.rank)
        else:  # HOKUM
            if trump_suit and card.suit == trump_suit:
                strength = 100 + ORDER_HOKUM.index(card.rank)
            elif card.suit == lead_suit:
                strength = ORDER_SUN.index(card.rank)

        if strength > best_strength:
            best_strength = strength
            best_seat = seat

    return best_seat


def _get_card_points(card: Card, game_mode: str, trump_suit: Optional[str]) -> int:
    """Calculate point value for a single card.

    Mirrors ``TrickResolver.get_card_points`` logic.

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


def _classify_severity(comparison: TrickComparison) -> str:
    """Classify divergence severity based on impact.

    @param comparison: The TrickComparison with the divergence.
    @returns 'HIGH', 'MEDIUM', or 'LOW'.
    """
    # High: disagreement on a high-point trick
    if comparison.engine_points >= 20:
        return "HIGH"
    # Medium: any HOKUM trick (trump resolution is critical)
    if comparison.game_mode == "HOKUM":
        return "MEDIUM"
    # Low: low-point SUN trick
    return "LOW"


# ── Scorecard Generation ────────────────────────────────────────────

def generate_scorecard(reports: list[ComparisonReport]) -> dict:
    """Compute per-category engine correctness from comparison reports.

    Categories:
      - trick_resolution: Winner agreement across all tricks.
      - point_calculation: Internal consistency (round point totals).
      - sun_mode: Winner agreement for SUN-mode tricks only.
      - hokum_mode: Winner agreement for HOKUM-mode tricks only.
      - overall: Combined across all categories.

    Badge thresholds: green >= 95%, yellow >= 80%, red < 80%.

    @param reports: List of ComparisonReport from compare_all_sessions().
    @returns Dict with per-category results and metadata.
    """
    total_tricks = 0
    total_agree = 0
    sun_tricks = 0
    sun_agree = 0
    hokum_tricks = 0
    hokum_agree = 0

    # Point consistency: per-round, check if engine points sum
    # to expected total for the mode
    round_groups: dict[tuple, list[TrickComparison]] = {}

    for report in reports:
        for tc in report.trick_comparisons:
            total_tricks += 1
            if tc.winner_agrees:
                total_agree += 1

            if tc.game_mode == "SUN":
                sun_tricks += 1
                if tc.winner_agrees:
                    sun_agree += 1
            elif tc.game_mode == "HOKUM":
                hokum_tricks += 1
                if tc.winner_agrees:
                    hokum_agree += 1

            key = (report.session_path, tc.round_index)
            round_groups.setdefault(key, []).append(tc)

    # G3: Use real point analysis from reports when available
    rounds_checked = 0
    rounds_points_ok = 0

    has_point_analyses = any(report.point_analyses for report in reports)
    if has_point_analyses:
        for report in reports:
            for pa in report.point_analyses:
                if pa.is_complete_round:
                    rounds_checked += 1
                    if pa.card_points_consistent:
                        rounds_points_ok += 1
    else:
        # Fallback: legacy self-check (sum per-trick engine_points)
        for _key, tricks in round_groups.items():
            if len(tricks) != 8:
                continue
            rounds_checked += 1
            total_pts = sum(tc.engine_points for tc in tricks)
            mode = tricks[0].game_mode
            expected = 120 if mode == "SUN" else 152
            if total_pts == expected:
                rounds_points_ok += 1

    def _make_category(correct: int, total: int) -> dict:
        pct = (correct / total * 100.0) if total > 0 else 0.0
        badge = "green" if pct >= 95 else "yellow" if pct >= 80 else "red"
        return {
            "agreement_pct": round(pct, 1),
            "badge": badge,
            "total": total,
            "correct": correct,
        }

    return {
        "trick_resolution": _make_category(total_agree, total_tricks),
        "point_calculation": _make_category(rounds_points_ok, rounds_checked),
        "sun_mode": _make_category(sun_agree, sun_tricks),
        "hokum_mode": _make_category(hokum_agree, hokum_tricks),
        "overall": _make_category(total_agree, total_tricks),
        "sessions_analyzed": len(reports),
        "total_tricks": total_tricks,
        "generated_at": datetime.now().isoformat(),
    }
