"""
GBaloot Benchmark Runner — First empirical scorecard.

Runs GameComparator.compare_all_sessions() across all 68 processed sessions,
generates the scorecard, and prints a detailed breakdown.
"""
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gbaloot.core.comparator import GameComparator, generate_scorecard

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)

SESSIONS_DIR = Path(__file__).resolve().parent / "data" / "sessions"
OUTPUT_FILE = Path(__file__).resolve().parent / "data" / "benchmark_scorecard.json"


def main():
    print("=" * 60)
    print("  GBaloot Benchmark — First Run")
    print("=" * 60)
    print()

    if not SESSIONS_DIR.exists():
        print(f"ERROR: Sessions directory not found: {SESSIONS_DIR}")
        return

    session_files = sorted(SESSIONS_DIR.glob("*_processed.json"))
    print(f"Found {len(session_files)} processed session files")
    print()

    # Run comparator
    comparator = GameComparator()
    start = time.time()

    print("Running comparisons...")
    reports = comparator.compare_all_sessions(SESSIONS_DIR)
    elapsed = time.time() - start

    print(f"Completed in {elapsed:.2f}s")
    print()

    # Generate scorecard
    scorecard = generate_scorecard(reports)

    # Print summary
    print("=" * 60)
    print("  SCORECARD RESULTS")
    print("=" * 60)
    print()

    # Session-level stats
    total_sessions = len(reports)
    sessions_with_tricks = sum(1 for r in reports if r.total_tricks > 0)
    sessions_empty = total_sessions - sessions_with_tricks

    print(f"Sessions analyzed:      {total_sessions}")
    print(f"  With game data:       {sessions_with_tricks}")
    print(f"  Empty (no tricks):    {sessions_empty}")
    print()

    # Per-session breakdown for sessions with data
    if sessions_with_tricks > 0:
        print("-" * 60)
        print("  PER-SESSION BREAKDOWN")
        print("-" * 60)
        for r in reports:
            if r.total_tricks > 0:
                status = "✓" if r.winner_agreement_pct == 100.0 else "✗"
                fname = Path(r.session_path).stem.replace("_processed", "")
                print(
                    f"  {status} {fname}: "
                    f"{r.total_tricks} tricks, "
                    f"{r.rounds_compared} rounds, "
                    f"{r.winner_agreement_pct}% agreement, "
                    f"{r.total_divergences} divergences"
                )
                # Show point consistency if available
                if r.point_analyses:
                    print(f"      Point consistency: {r.point_consistency_pct}%")
                if r.extraction_warnings:
                    for w in r.extraction_warnings[:3]:
                        print(f"      ⚠ {w}")
        print()

    # Scorecard categories
    print("-" * 60)
    print("  CATEGORY SCORES")
    print("-" * 60)
    categories = [
        ("Trick Resolution", "trick_resolution"),
        ("Point Calculation", "point_calculation"),
        ("SUN Mode",         "sun_mode"),
        ("HOKUM Mode",       "hokum_mode"),
        ("Overall",          "overall"),
    ]
    for label, key in categories:
        cat = scorecard.get(key, {})
        pct = cat.get("agreement_pct", 0)
        badge = cat.get("badge", "?")
        total = cat.get("total", 0)
        correct = cat.get("correct", 0)
        badge_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(badge, "⚪")
        print(f"  {badge_icon} {label:20s}  {pct:6.1f}%  ({correct}/{total})")
    print()

    # Divergences
    divergences = comparator.get_divergences()
    print(f"Total divergences: {len(divergences)}")
    if divergences:
        print()
        print("-" * 60)
        print("  DIVERGENCE DETAILS")
        print("-" * 60)
        for div in divergences[:20]:  # Show first 20
            fname = Path(div.session_path).stem.replace("_processed", "")
            print(f"  [{div.severity}] {div.id} — Round {div.round_index}, "
                  f"Trick {div.trick_number}")
            print(f"    Mode: {div.game_mode}, Trump: {div.trump_suit}, "
                  f"Lead: {div.lead_suit}")
            print(f"    Source: {div.source_result}")
            print(f"    Engine: {div.engine_result}")
            cards_str = ", ".join(
                f"S{c['seat']}:{c['card']}" for c in div.cards_played
            )
            print(f"    Cards: {cards_str}")
            print(f"    Notes: {div.notes}")
            print()

    # Save scorecard
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
                "point_consistency_pct": r.point_consistency_pct,
                "warnings": r.extraction_warnings,
            }
            for r in reports
        ],
        "divergences": [d.to_dict() for d in divergences],
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2, ensure_ascii=False, default=str)

    print(f"Full scorecard saved to: {OUTPUT_FILE}")
    print()
    print("=" * 60)
    print("  BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
