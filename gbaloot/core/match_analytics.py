"""
Match Analytics — Cross-session trend analysis and divergence patterns.

Provides:
- MatchProgression: cumulative GP per team across rounds
- DivergenceHeatmap: round_position x mode divergence density matrix
- TrendAnalysis: per-mode accuracy, per-round accuracy, top divergence patterns

All functions are pure — they take comparison data and return analysis results.

Usage::

    from gbaloot.core.match_analytics import (
        build_match_progression,
        build_divergence_heatmap,
        analyze_trends,
    )

    progression = build_match_progression(report)
    heatmap = build_divergence_heatmap(divergences)
    trends = analyze_trends(reports)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from gbaloot.core.comparator import ComparisonReport, TrickComparison, Divergence

logger = logging.getLogger(__name__)


# ── Data Models ───────────────────────────────────────────────────────

@dataclass
class RoundProgression:
    """State after one round in a match.

    @param round_index: 0-based round number.
    @param mode: SUN or HOKUM for this round.
    @param tricks_played: Number of tricks in this round.
    @param tricks_agreed: Number of tricks where engines agreed.
    @param agreement_pct: Percentage agreement for this round.
    """
    round_index: int = 0
    mode: str = ""
    tricks_played: int = 0
    tricks_agreed: int = 0
    agreement_pct: float = 0.0


@dataclass
class MatchProgression:
    """Cumulative match data built from a ComparisonReport.

    @param rounds: Per-round breakdown.
    @param total_tricks: Total tricks across all rounds.
    @param total_agreed: Total tricks with agreement.
    @param overall_agreement: Overall agreement percentage.
    """
    rounds: list[RoundProgression] = field(default_factory=list)
    total_tricks: int = 0
    total_agreed: int = 0
    overall_agreement: float = 0.0


@dataclass
class HeatmapCell:
    """One cell in the divergence heatmap.

    @param trick_position: 1-based trick number within the round.
    @param mode: SUN or HOKUM.
    @param divergence_count: Number of divergences at this position.
    @param total_tricks: Total tricks at this position across sessions.
    @param divergence_rate: Divergence rate (0.0 - 1.0).
    """
    trick_position: int = 0
    mode: str = ""
    divergence_count: int = 0
    total_tricks: int = 0
    divergence_rate: float = 0.0


@dataclass
class DivergenceHeatmap:
    """Grid of divergence rates by trick position and mode.

    @param cells: List of HeatmapCell objects.
    @param max_trick_position: Maximum trick position observed.
    @param modes: Set of modes present.
    """
    cells: list[HeatmapCell] = field(default_factory=list)
    max_trick_position: int = 0
    modes: list[str] = field(default_factory=list)


@dataclass
class TrendAnalysis:
    """Cross-session trend analysis.

    @param per_mode_accuracy: {mode: agreement_pct}.
    @param per_mode_count: {mode: total_tricks}.
    @param sessions_analyzed: Number of sessions analyzed.
    @param total_tricks: Total tricks across all sessions.
    @param total_divergences: Total divergences across all sessions.
    @param top_divergence_patterns: Most common divergence descriptions.
    """
    per_mode_accuracy: dict[str, float] = field(default_factory=dict)
    per_mode_count: dict[str, int] = field(default_factory=dict)
    sessions_analyzed: int = 0
    total_tricks: int = 0
    total_divergences: int = 0
    top_divergence_patterns: list[tuple[str, int]] = field(default_factory=list)


# ── Build Functions ───────────────────────────────────────────────────

def build_match_progression(report: ComparisonReport) -> MatchProgression:
    """Build round-by-round match progression from a comparison report.

    @param report: ComparisonReport from the comparator module.
    @returns MatchProgression with per-round breakdown.
    """
    if not report or not report.trick_comparisons:
        return MatchProgression()

    # Group tricks by round
    rounds_map: dict[int, list[TrickComparison]] = defaultdict(list)
    for tc in report.trick_comparisons:
        rounds_map[tc.round_index].append(tc)

    rounds: list[RoundProgression] = []
    total_tricks = 0
    total_agreed = 0

    for round_idx in sorted(rounds_map.keys()):
        tricks = rounds_map[round_idx]
        played = len(tricks)
        agreed = sum(1 for t in tricks if t.winner_agrees)
        pct = (agreed / played * 100) if played > 0 else 0.0
        mode = tricks[0].game_mode if tricks else ""

        rounds.append(RoundProgression(
            round_index=round_idx,
            mode=mode,
            tricks_played=played,
            tricks_agreed=agreed,
            agreement_pct=pct,
        ))
        total_tricks += played
        total_agreed += agreed

    overall = (total_agreed / total_tricks * 100) if total_tricks > 0 else 0.0

    return MatchProgression(
        rounds=rounds,
        total_tricks=total_tricks,
        total_agreed=total_agreed,
        overall_agreement=overall,
    )


def build_divergence_heatmap(
    divergences: list[Divergence],
    trick_comparisons: list[TrickComparison] | None = None,
) -> DivergenceHeatmap:
    """Build a trick_position x mode divergence heatmap.

    @param divergences: List of Divergence objects from one or more sessions.
    @param trick_comparisons: Optional list of all TrickComparisons for totals.
    @returns DivergenceHeatmap with divergence rates per cell.
    """
    if not divergences:
        return DivergenceHeatmap()

    # Count divergences per (trick_position, mode)
    div_counts: dict[tuple[int, str], int] = defaultdict(int)
    total_counts: dict[tuple[int, str], int] = defaultdict(int)
    modes_seen: set[str] = set()
    max_pos = 0

    for d in divergences:
        key = (d.trick_number, d.game_mode)
        div_counts[key] += 1
        modes_seen.add(d.game_mode)
        max_pos = max(max_pos, d.trick_number)

    # Count total tricks at each position (if data available)
    if trick_comparisons:
        for tc in trick_comparisons:
            key = (tc.trick_number, tc.game_mode)
            total_counts[key] += 1
            modes_seen.add(tc.game_mode)
            max_pos = max(max_pos, tc.trick_number)

    cells: list[HeatmapCell] = []
    for key, count in sorted(div_counts.items()):
        trick_pos, mode = key
        total = total_counts.get(key, count)
        rate = count / total if total > 0 else 0.0
        cells.append(HeatmapCell(
            trick_position=trick_pos,
            mode=mode,
            divergence_count=count,
            total_tricks=total,
            divergence_rate=rate,
        ))

    return DivergenceHeatmap(
        cells=cells,
        max_trick_position=max_pos,
        modes=sorted(modes_seen),
    )


def analyze_trends(
    reports: list[ComparisonReport],
    all_divergences: list[Divergence] | None = None,
) -> TrendAnalysis:
    """Analyze trends across multiple session comparison reports.

    @param reports: List of ComparisonReport objects.
    @param all_divergences: Optional list of all Divergence objects across sessions.
    @returns TrendAnalysis with per-mode accuracy and top patterns.
    """
    if not reports:
        return TrendAnalysis()

    mode_tricks: dict[str, int] = defaultdict(int)
    mode_agreed: dict[str, int] = defaultdict(int)
    total_tricks = 0
    total_divergences = 0
    pattern_counts: dict[str, int] = defaultdict(int)

    for report in reports:
        for tc in report.trick_comparisons:
            mode_tricks[tc.game_mode] += 1
            if tc.winner_agrees:
                mode_agreed[tc.game_mode] += 1
            total_tricks += 1

        # Count divergences from report metadata
        total_divergences += report.total_divergences

    # Analyze divergence patterns if provided
    if all_divergences:
        for d in all_divergences:
            pattern = f"{d.game_mode} T{d.trick_number}: {d.notes}"
            pattern_counts[pattern] += 1

    per_mode_accuracy: dict[str, float] = {}
    for mode, count in mode_tricks.items():
        agreed = mode_agreed.get(mode, 0)
        per_mode_accuracy[mode] = (agreed / count * 100) if count > 0 else 0.0

    top_patterns = sorted(pattern_counts.items(), key=lambda x: -x[1])[:10]

    return TrendAnalysis(
        per_mode_accuracy=per_mode_accuracy,
        per_mode_count=dict(mode_tricks),
        sessions_analyzed=len(reports),
        total_tricks=total_tricks,
        total_divergences=total_divergences,
        top_divergence_patterns=top_patterns,
    )
