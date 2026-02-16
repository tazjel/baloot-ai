"""
GBaloot Archive Benchmark Runner -- Compare 109 source platform mobile archive
sessions against our game engine's trick resolution logic.

Usage:
    python -m gbaloot.tools.run_archive_benchmark
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gbaloot.core.card_mapping import map_game_mode, suit_idx_to_symbol
from gbaloot.core.comparator import (
    GameComparator,
    ComparisonReport,
    TrickComparison,
    generate_scorecard,
)
from gbaloot.core.trick_extractor import ExtractionResult
from gbaloot.tools.archive_parser import parse_archive, ArchiveGame
from gbaloot.tools.archive_trick_extractor import extract_tricks_from_archive

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)

ARCHIVE_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "archive_captures"
    / "mobile_export"
    / "savedGames"
)

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "archive_benchmark_scorecard.json"
)


# ── Compare Extraction Against Engine ────────────────────────────────

def compare_extraction(
    extraction: ExtractionResult,
    comparator: GameComparator,
) -> ComparisonReport:
    """Feed an ExtractionResult through the comparator.

    The comparator normally extracts tricks itself from session events.
    Here we bypass that by directly comparing extracted tricks.

    @param extraction: Tricks extracted from archive.
    @param comparator: GameComparator instance.
    @returns ComparisonReport with per-trick results.
    """
    from datetime import datetime

    comparisons: list[TrickComparison] = []
    points_team_02 = 0
    points_team_13 = 0

    for rnd in extraction.rounds:
        try:
            mode = map_game_mode(rnd.game_mode_raw)
        except ValueError:
            mode = "SUN"

        trump_suit = (
            suit_idx_to_symbol(rnd.trump_suit_idx)
            if rnd.trump_suit_idx is not None
            else None
        )

        for trick in rnd.tricks:
            tc = comparator._compare_trick(
                trick, mode, trump_suit, extraction.session_path
            )
            comparisons.append(tc)

            for card_info in tc.cards:
                seat = card_info["seat"]
                pts = card_info.get("points", 0)
                if seat in (0, 2):
                    points_team_02 += pts
                else:
                    points_team_13 += pts

    total = len(comparisons)
    agrees = sum(1 for c in comparisons if c.winner_agrees)
    pct = (agrees / total * 100.0) if total > 0 else 0.0

    divergence_breakdown: dict[str, int] = {}
    for c in comparisons:
        if c.divergence_type:
            divergence_breakdown[c.divergence_type] = (
                divergence_breakdown.get(c.divergence_type, 0) + 1
            )

    return ComparisonReport(
        session_path=extraction.session_path,
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
    )


# ── Main ─────────────────────────────────────────────────────────────

def main():
    """Run the archive benchmark."""
    print("=" * 65)
    print("  GBaloot Archive Benchmark -- 109 source platform Mobile Sessions")
    print("=" * 65)
    print()

    if not ARCHIVE_DIR.exists():
        print(f"ERROR: Archive directory not found: {ARCHIVE_DIR}")
        return

    archive_files = sorted(ARCHIVE_DIR.glob("*.json"))
    print(f"Found {len(archive_files)} archive files")
    print()

    comparator = GameComparator()
    reports: list[ComparisonReport] = []
    parse_errors: list[str] = []
    start = time.time()

    print("Running comparisons...")
    for i, archive_file in enumerate(archive_files):
        try:
            extraction = extract_tricks_from_archive(archive_file)
            if extraction.total_tricks == 0:
                parse_errors.append(f"{archive_file.name}: 0 tricks extracted")
                continue
            report = compare_extraction(extraction, comparator)
            reports.append(report)

            # Progress indicator
            if (i + 1) % 20 == 0:
                print(f"  Processed {i + 1}/{len(archive_files)}...")

        except Exception as e:
            parse_errors.append(f"{archive_file.name}: {e}")

    elapsed = time.time() - start
    print(f"Completed in {elapsed:.2f}s")
    print()

    # Generate scorecard
    scorecard = generate_scorecard(reports)

    # ── Print Summary ────────────────────────────────────────────────
    print("=" * 65)
    print("  SCORECARD RESULTS")
    print("=" * 65)
    print()

    total_sessions = len(reports)
    sessions_perfect = sum(
        1 for r in reports if r.winner_agreement_pct == 100.0
    )

    print(f"Sessions analyzed:      {total_sessions}")
    print(f"  Perfect (100%):       {sessions_perfect}")
    print(f"  With divergences:     {total_sessions - sessions_perfect}")
    if parse_errors:
        print(f"  Parse errors:         {len(parse_errors)}")
    print()

    # ── Per-session breakdown ────────────────────────────────────────
    print("-" * 65)
    print("  PER-SESSION BREAKDOWN")
    print("-" * 65)

    # Show non-perfect sessions first, then perfect ones summarized
    imperfect = [r for r in reports if r.winner_agreement_pct < 100.0]
    perfect = [r for r in reports if r.winner_agreement_pct == 100.0]

    if imperfect:
        for r in imperfect:
            fname = Path(r.session_path).stem[:40]
            print(
                f"  X {fname}: "
                f"{r.total_tricks} tricks, "
                f"{r.rounds_compared} rounds, "
                f"{r.winner_agreement_pct}% agreement, "
                f"{r.total_divergences} div"
            )
            if r.extraction_warnings:
                for w in r.extraction_warnings[:2]:
                    print(f"      ! {w}")
        print()

    print(f"  + {len(perfect)} sessions with 100% agreement")
    print()

    # ── Category Scores ──────────────────────────────────────────────
    print("-" * 65)
    print("  CATEGORY SCORES")
    print("-" * 65)
    categories = [
        ("Trick Resolution", "trick_resolution"),
        ("Point Calculation", "point_calculation"),
        ("SUN Mode", "sun_mode"),
        ("HOKUM Mode", "hokum_mode"),
        ("Overall", "overall"),
    ]
    for label, key in categories:
        cat = scorecard.get(key, {})
        pct = cat.get("agreement_pct", 0)
        badge = cat.get("badge", "?")
        total = cat.get("total", 0)
        correct = cat.get("correct", 0)
        icon = {"green": "+", "yellow": "~", "red": "-"}.get(badge, "?")
        print(f"  [{icon}] {label:20s}  {pct:6.1f}%  ({correct}/{total})")
    print()

    # ── Divergence Details ───────────────────────────────────────────
    divergences = comparator.get_divergences()
    print(f"Total divergences: {len(divergences)}")
    if divergences:
        print()
        print("-" * 65)
        print("  DIVERGENCE DETAILS (first 30)")
        print("-" * 65)
        for div in divergences[:30]:
            fname = Path(div.session_path).stem[:30]
            print(
                f"  [{div.severity}] {div.id} -- {fname}"
            )
            print(
                f"    Round {div.round_index}, Trick {div.trick_number} | "
                f"Mode: {div.game_mode}, Trump: {div.trump_suit}, "
                f"Lead: {div.lead_suit}"
            )
            print(f"    Source: {div.source_result}")
            print(f"    Engine: {div.engine_result}")
            cards_str = ", ".join(
                f"S{c['seat']}:{c['card']}" for c in div.cards_played
            )
            print(f"    Cards: {cards_str}")
            if div.notes:
                print(f"    Notes: {div.notes}")
            print()

    # ── Parse Errors ─────────────────────────────────────────────────
    if parse_errors:
        print("-" * 65)
        print(f"  PARSE ERRORS ({len(parse_errors)})")
        print("-" * 65)
        for err in parse_errors[:20]:
            print(f"  ! {err}")
        print()

    # ── Save Full Results ────────────────────────────────────────────
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    full_output = {
        "scorecard": scorecard,
        "session_summaries": [
            {
                "session": r.session_path,
                "rounds": r.rounds_compared,
                "tricks": r.total_tricks,
                "agreement_pct": r.winner_agreement_pct,
                "divergences": r.total_divergences,
                "warnings": r.extraction_warnings[:5],
            }
            for r in reports
        ],
        "divergences": [d.to_dict() for d in divergences],
        "parse_errors": parse_errors,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2, ensure_ascii=False, default=str)

    print(f"Full results saved to: {OUTPUT_FILE}")
    print()
    print("=" * 65)
    print("  BENCHMARK COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    main()
