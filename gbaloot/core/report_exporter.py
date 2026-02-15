"""
Report Exporter — JSON and Markdown export for analysis results.

Provides persistent, shareable reports that survive page refresh.
Supports session reports, scorecards, and divergence collections.

Usage::

    from gbaloot.core.report_exporter import (
        export_session_report,
        export_scorecard,
        export_divergences,
    )

    path = export_session_report(session_report, reports_dir, "json")
    path = export_scorecard(scorecard, reports_dir)
    path = export_divergences(divergences, reports_dir)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _ensure_dir(directory: Path) -> Path:
    """Ensure directory exists, return it."""
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _timestamp_slug() -> str:
    """Return a filesystem-safe timestamp slug."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Session Report Export ─────────────────────────────────────────────

def session_report_to_dict(session_report) -> dict:
    """Convert a SessionReport to a plain dict for JSON serialization.

    @param session_report: A SessionReport instance from round_report.py.
    @returns Plain dict suitable for json.dumps().
    """
    rounds = []
    for rr in session_report.rounds:
        round_data = {
            "round_index": rr.round_index,
            "game_mode": rr.game_mode,
            "trump_suit": rr.trump_suit,
            "dealer_seat": rr.dealer_seat,
            "num_tricks": rr.num_tricks,
            "trick_agreement_pct": rr.trick_agreement_pct,
            "is_complete": rr.is_complete,
            "has_divergences": rr.has_divergences,
            "overall_status": rr.overall_status,
        }

        # Trick comparisons
        round_data["trick_comparisons"] = [
            {
                "trick_number": tc.trick_number,
                "cards": tc.cards,
                "lead_suit": tc.lead_suit,
                "game_mode": tc.game_mode,
                "trump_suit": tc.trump_suit,
                "source_winner_seat": tc.source_winner_seat,
                "engine_winner_seat": tc.engine_winner_seat,
                "engine_points": tc.engine_points,
                "winner_agrees": tc.winner_agrees,
                "divergence_type": tc.divergence_type,
                "notes": tc.notes,
            }
            for tc in rr.trick_comparisons
        ]

        # Bidding
        if rr.bid_sequence:
            round_data["bidding"] = {
                "final_mode": rr.bid_sequence.final_mode,
                "caller_seat": rr.bid_sequence.caller_seat,
                "dealer_seat": rr.bid_sequence.dealer_seat,
                "bid_count": len(rr.bid_sequence.bids),
                "bids": [
                    {
                        "seat": b.seat,
                        "action": b.action,
                        "bidding_round": b.bidding_round,
                    }
                    for b in rr.bid_sequence.bids
                ],
            }

        # Point analysis
        if rr.point_analysis:
            pa = rr.point_analysis
            round_data["point_analysis"] = {
                "round_index": pa.round_index,
                "is_complete_round": pa.is_complete_round,
                "raw_abnat_team_02": pa.raw_abnat_team_02,
                "raw_abnat_team_13": pa.raw_abnat_team_13,
                "card_points_consistent": pa.card_points_consistent,
            }

        rounds.append(round_data)

    return {
        "session_path": session_report.session_path,
        "generated_at": session_report.generated_at,
        "total_tricks": session_report.total_tricks,
        "total_rounds": session_report.total_rounds,
        "trick_agreement_pct": session_report.trick_agreement_pct,
        "rounds_with_bids": session_report.rounds_with_bids,
        "complete_rounds": session_report.complete_rounds,
        "point_consistent_rounds": session_report.point_consistent_rounds,
        "screenshot_count": session_report.screenshot_count,
        "rounds": rounds,
    }


def session_report_to_markdown(session_report) -> str:
    """Convert a SessionReport to human-readable Markdown.

    @param session_report: A SessionReport instance from round_report.py.
    @returns Markdown string.
    """
    lines = [
        f"# Session Report",
        f"",
        f"- **Session**: `{session_report.session_path}`",
        f"- **Generated**: {session_report.generated_at}",
        f"- **Total Rounds**: {session_report.total_rounds}",
        f"- **Total Tricks**: {session_report.total_tricks}",
        f"- **Trick Agreement**: {session_report.trick_agreement_pct:.1f}%",
        f"- **Rounds with Bids**: {session_report.rounds_with_bids}",
        f"- **Complete Rounds**: {session_report.complete_rounds}",
        f"- **Point-Consistent Rounds**: {session_report.point_consistent_rounds}",
        f"",
    ]

    for rr in session_report.rounds:
        mode_str = rr.game_mode
        trump_str = f" (Trump: {rr.trump_suit})" if rr.trump_suit else ""
        lines.append(f"## Round {rr.round_index + 1}: {mode_str}{trump_str}")
        lines.append(f"")
        lines.append(
            f"- Status: {rr.overall_status} | "
            f"Tricks: {rr.num_tricks} | "
            f"Agreement: {rr.trick_agreement_pct:.0f}%"
        )

        if rr.bid_sequence and rr.bid_sequence.bids:
            lines.append(f"- Bidding: {len(rr.bid_sequence.bids)} bids, "
                         f"final mode: {rr.bid_sequence.final_mode}")

        if rr.trick_comparisons:
            lines.append(f"")
            lines.append(f"| Trick | Cards | Lead | Src | Eng | Pts | Status |")
            lines.append(f"|-------|-------|------|-----|-----|-----|--------|")
            for tc in rr.trick_comparisons:
                cards = ", ".join(c.get("card", "?") for c in tc.cards)
                status = "OK" if tc.winner_agrees else "DIVERGE"
                lines.append(
                    f"| {tc.trick_number} | {cards} | {tc.lead_suit} | "
                    f"S{tc.source_winner_seat} | S{tc.engine_winner_seat} | "
                    f"{tc.engine_points} | {status} |"
                )

        lines.append(f"")

    return "\n".join(lines)


def export_session_report(
    session_report,
    reports_dir: Path,
    fmt: str = "json",
) -> Path:
    """Export a SessionReport to a file.

    @param session_report: A SessionReport instance.
    @param reports_dir: Directory to save the report.
    @param fmt: 'json' or 'markdown'.
    @returns Path to the saved file.
    """
    _ensure_dir(reports_dir)
    slug = _timestamp_slug()

    if fmt == "markdown":
        content = session_report_to_markdown(session_report)
        out_path = reports_dir / f"session_report_{slug}.md"
        out_path.write_text(content, encoding="utf-8")
    else:
        data = session_report_to_dict(session_report)
        out_path = reports_dir / f"session_report_{slug}.json"
        out_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    logger.info("Exported session report to %s", out_path)
    return out_path


# ── Scorecard Export ──────────────────────────────────────────────────

def export_scorecard(scorecard: dict, reports_dir: Path) -> Path:
    """Export a scorecard dict to JSON.

    @param scorecard: Dict from generate_scorecard().
    @param reports_dir: Directory to save.
    @returns Path to the saved file.
    """
    _ensure_dir(reports_dir)
    slug = _timestamp_slug()
    out_path = reports_dir / f"scorecard_{slug}.json"
    out_path.write_text(
        json.dumps(scorecard, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Exported scorecard to %s", out_path)
    return out_path


# ── Divergences Export ────────────────────────────────────────────────

def export_divergences(divergences: list, reports_dir: Path) -> Path:
    """Export a list of Divergence objects to JSON.

    @param divergences: List of Divergence dataclass instances.
    @param reports_dir: Directory to save.
    @returns Path to the saved file.
    """
    _ensure_dir(reports_dir)
    slug = _timestamp_slug()
    out_path = reports_dir / f"divergences_{slug}.json"
    data = [d.to_dict() for d in divergences]
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Exported %d divergences to %s", len(divergences), out_path)
    return out_path


# ── List Saved Reports ───────────────────────────────────────────────

def list_saved_reports(reports_dir: Path) -> list[dict]:
    """List all saved reports in a directory.

    @param reports_dir: Directory to scan.
    @returns List of dicts with 'filename', 'type', 'size_kb', 'modified'.
    """
    if not reports_dir.exists():
        return []

    entries = []
    for f in sorted(reports_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not f.is_file():
            continue
        if f.suffix not in (".json", ".md"):
            continue

        # Determine type from filename prefix
        if f.name.startswith("session_report_"):
            rtype = "Session Report"
        elif f.name.startswith("scorecard_"):
            rtype = "Scorecard"
        elif f.name.startswith("divergences_"):
            rtype = "Divergences"
        else:
            rtype = "Other"

        entries.append({
            "filename": f.name,
            "type": rtype,
            "format": f.suffix[1:],
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "path": str(f),
        })

    return entries
