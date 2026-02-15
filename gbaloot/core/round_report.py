"""
Round Report — Unified per-round view combining bidding, tricks, and points
into a single coherent analysis.

Orchestrates all extractors and comparators to produce a SessionReport
that captures the complete story: who bid what, how tricks played, and
whether we agree on winners and points.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from gbaloot.core.bid_extractor import (
    extract_bids,
    ExtractedBidSequence,
    BidExtractionResult,
)
from gbaloot.core.bid_comparator import (
    compare_bid_sequence,
    BidComparison,
)
from gbaloot.core.comparator import (
    GameComparator,
    ComparisonReport,
    TrickComparison,
)
from gbaloot.core.point_tracker import (
    analyze_round_points,
    PointAnalysis,
)
from gbaloot.core.trick_extractor import (
    extract_tricks,
    ExtractedRound,
    ExtractionResult,
)
from gbaloot.core.card_mapping import map_game_mode, suit_idx_to_symbol

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class RoundReport:
    """Unified report for a single game round.

    @param round_index: 0-based round number.
    @param game_mode: 'SUN' or 'HOKUM'.
    @param trump_suit: Unicode suit symbol or None.
    @param dealer_seat: 0-indexed dealer seat.
    @param bid_sequence: Extracted bidding sequence (from G2), or None.
    @param bid_comparison: Engine bid comparison (from G2), or None.
    @param trick_comparisons: Per-trick engine comparisons.
    @param point_analysis: Per-round point analysis (from G3), or None.
    @param num_tricks: Number of tricks in this round.
    @param trick_agreement_pct: Percentage of tricks with winner agreement.
    @param screenshots: Correlated screenshots for this round.
    """
    round_index: int
    game_mode: str
    trump_suit: Optional[str]
    dealer_seat: int
    bid_sequence: Optional[ExtractedBidSequence] = None
    bid_comparison: Optional[BidComparison] = None
    trick_comparisons: list[TrickComparison] = field(default_factory=list)
    point_analysis: Optional[PointAnalysis] = None
    num_tricks: int = 0
    trick_agreement_pct: float = 0.0
    screenshots: list[dict] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """True if round has 8 tricks."""
        return self.num_tricks == 8

    @property
    def has_divergences(self) -> bool:
        """True if any trick has a disagreement."""
        return any(not tc.winner_agrees for tc in self.trick_comparisons)

    @property
    def has_bidding(self) -> bool:
        """True if bidding data was extracted."""
        return self.bid_sequence is not None and len(self.bid_sequence.bids) > 0

    @property
    def has_points(self) -> bool:
        """True if point analysis is available."""
        return self.point_analysis is not None

    @property
    def overall_status(self) -> str:
        """Quick status icon for the round.

        @returns '✅' if all agree, '⚠️' if minor issues, '❌' if divergences.
        """
        if self.has_divergences:
            return "❌"
        if self.is_complete and self.has_points and not self.point_analysis.card_points_consistent:
            return "⚠️"
        return "✅"


@dataclass
class SessionReport:
    """Unified report for an entire session.

    @param session_path: Source session file path.
    @param generated_at: ISO timestamp of report generation.
    @param rounds: Per-round unified reports.
    @param total_tricks: Sum of tricks across all rounds.
    @param total_rounds: Number of rounds.
    @param trick_agreement_pct: Overall trick winner agreement.
    @param rounds_with_bids: Number of rounds with bidding data.
    @param complete_rounds: Number of 8-trick rounds.
    @param point_consistent_rounds: Rounds where card points are correct.
    @param screenshot_count: Total correlated screenshots.
    @param comparison_report: The raw ComparisonReport (for backward compat).
    @param bid_result: The raw BidExtractionResult (for backward compat).
    """
    session_path: str
    generated_at: str
    rounds: list[RoundReport] = field(default_factory=list)
    total_tricks: int = 0
    total_rounds: int = 0
    trick_agreement_pct: float = 0.0
    rounds_with_bids: int = 0
    complete_rounds: int = 0
    point_consistent_rounds: int = 0
    screenshot_count: int = 0
    comparison_report: Optional[ComparisonReport] = None
    bid_result: Optional[BidExtractionResult] = None


# ── Builder ──────────────────────────────────────────────────────────

def build_session_report(
    session_events: list[dict],
    session_path: str = "",
    screenshots_dir: Optional[Path] = None,
) -> SessionReport:
    """Build a unified session report by orchestrating all extractors.

    Runs trick extraction, bidding extraction, engine comparison, and
    point analysis in sequence, then merges results per round.

    @param session_events: The 'events' list from a ProcessedSession.
    @param session_path: For identification in the report.
    @param screenshots_dir: Optional directory with session screenshots.
    @returns SessionReport with all per-round data unified.
    """
    # Step 1: Extract tricks (foundation for everything else)
    extraction = extract_tricks(session_events, session_path)

    # Step 2: Run engine comparison
    comparator = GameComparator()
    comparison = comparator.compare_session(session_events, session_path)

    # Step 3: Extract bids
    bid_result = None
    try:
        bid_result = extract_bids(session_events, session_path)
    except Exception as e:
        logger.warning("Bid extraction failed: %s", e)

    # Step 4: Build per-round lookup tables

    # Group trick comparisons by round
    tricks_by_round: dict[int, list[TrickComparison]] = {}
    for tc in comparison.trick_comparisons:
        tricks_by_round.setdefault(tc.round_index, []).append(tc)

    # Group bid sequences by round
    bids_by_round: dict[int, ExtractedBidSequence] = {}
    if bid_result:
        for seq in bid_result.sequences:
            bids_by_round[seq.round_index] = seq

    # Group point analyses by round
    points_by_round: dict[int, PointAnalysis] = {}
    for pa in comparison.point_analyses:
        points_by_round[pa.round_index] = pa

    # Correlate screenshots if available
    screenshots_by_round: dict[int, list[dict]] = {}
    total_screenshots = 0
    if screenshots_dir and screenshots_dir.exists():
        try:
            from gbaloot.tools.screenshot_diff import correlate_screenshots_with_events
            all_correlated = correlate_screenshots_with_events(
                screenshots_dir, extraction,
            )
            for sc in all_correlated:
                ri = sc.get("round_index", -1)
                if ri >= 0:
                    screenshots_by_round.setdefault(ri, []).append(sc)
                    total_screenshots += 1
        except Exception as e:
            logger.warning("Screenshot correlation failed: %s", e)

    # Step 5: Build unified round reports
    round_reports: list[RoundReport] = []
    for rnd in extraction.rounds:
        try:
            mode = map_game_mode(rnd.game_mode_raw)
        except ValueError:
            mode = "SUN"
        trump = (
            suit_idx_to_symbol(rnd.trump_suit_idx)
            if rnd.trump_suit_idx is not None
            else None
        )

        round_tricks = tricks_by_round.get(rnd.round_index, [])
        num_tricks = len(round_tricks)
        agrees = sum(1 for tc in round_tricks if tc.winner_agrees)
        agreement_pct = (agrees / num_tricks * 100.0) if num_tricks > 0 else 0.0

        # Bid comparison (requires hand bitmask from bid extractor)
        bid_seq = bids_by_round.get(rnd.round_index)
        bid_comp = None
        if bid_seq and bid_seq.face_card_idx >= 0:
            # We don't have reliable hand bitmask from the session data in this path.
            # The hand would come from the pcs field of a bidding event.
            # For now, leave bid_comp as None — the bid_sequence itself is useful.
            pass

        rr = RoundReport(
            round_index=rnd.round_index,
            game_mode=mode,
            trump_suit=trump,
            dealer_seat=rnd.dealer_seat,
            bid_sequence=bid_seq,
            bid_comparison=bid_comp,
            trick_comparisons=round_tricks,
            point_analysis=points_by_round.get(rnd.round_index),
            num_tricks=num_tricks,
            trick_agreement_pct=round(agreement_pct, 1),
            screenshots=screenshots_by_round.get(rnd.round_index, []),
        )
        round_reports.append(rr)

    # Step 6: Aggregate metrics
    total_tricks = sum(rr.num_tricks for rr in round_reports)
    total_agrees = sum(
        sum(1 for tc in rr.trick_comparisons if tc.winner_agrees)
        for rr in round_reports
    )
    overall_pct = (total_agrees / total_tricks * 100.0) if total_tricks > 0 else 0.0

    complete = [rr for rr in round_reports if rr.is_complete]
    point_ok = sum(
        1 for rr in complete
        if rr.point_analysis and rr.point_analysis.card_points_consistent
    )

    return SessionReport(
        session_path=session_path,
        generated_at=datetime.now().isoformat(),
        rounds=round_reports,
        total_tricks=total_tricks,
        total_rounds=len(round_reports),
        trick_agreement_pct=round(overall_pct, 1),
        rounds_with_bids=sum(1 for rr in round_reports if rr.has_bidding),
        complete_rounds=len(complete),
        point_consistent_rounds=point_ok,
        screenshot_count=total_screenshots,
        comparison_report=comparison,
        bid_result=bid_result,
    )
