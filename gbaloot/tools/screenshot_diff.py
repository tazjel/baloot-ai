"""
GBaloot Screenshot Diff — Visual comparison between capture screenshots and engine board state.

Compares screenshots from a capture session to identify visual differences.
Supports basic image comparison using structural similarity (SSIM) when scikit-image
is available, and falls back to simple pixel-level comparison otherwise.

Usage:
    python gbaloot/tools/screenshot_diff.py --session hokum_aggressive_01
    python gbaloot/tools/screenshot_diff.py --compare img1.png img2.png
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent


def pixel_diff(img_path_a: str, img_path_b: str) -> dict:
    """
    Compare two images using basic pixel-level difference.
    Returns a dict with the comparison metrics.
    Requires Pillow.
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return {"error": "Pillow not installed (pip install Pillow)"}

    img_a = Image.open(img_path_a).convert("RGB")
    img_b = Image.open(img_path_b).convert("RGB")

    # Resize to same dimensions if different
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.Resampling.LANCZOS)

    diff = ImageChops.difference(img_a, img_b)
    diff_data = list(diff.getdata())
    total_pixels = len(diff_data)
    changed_pixels = sum(1 for px in diff_data if sum(px) > 30)  # threshold
    similarity_pct = ((total_pixels - changed_pixels) / total_pixels) * 100

    # Save diff image
    diff_path = Path(img_path_a).parent / f"diff_{Path(img_path_a).stem}_vs_{Path(img_path_b).stem}.png"
    diff.save(str(diff_path))

    return {
        "image_a": str(img_path_a),
        "image_b": str(img_path_b),
        "total_pixels": total_pixels,
        "changed_pixels": changed_pixels,
        "similarity_pct": round(similarity_pct, 2),
        "diff_image": str(diff_path),
    }


def ssim_diff(img_path_a: str, img_path_b: str) -> dict:
    """
    Compare two images using Structural Similarity Index (SSIM).
    Requires scikit-image and Pillow.
    """
    try:
        from PIL import Image
        import numpy as np
        from skimage.metrics import structural_similarity as ssim
    except ImportError:
        return pixel_diff(img_path_a, img_path_b)

    img_a = np.array(Image.open(img_path_a).convert("L"))
    img_b = np.array(Image.open(img_path_b).convert("L"))

    # Resize if needed
    if img_a.shape != img_b.shape:
        from PIL import Image as PILImage
        img_b_pil = PILImage.open(img_path_b).convert("L").resize(
            (img_a.shape[1], img_a.shape[0]), PILImage.Resampling.LANCZOS
        )
        img_b = np.array(img_b_pil)

    score, diff_matrix = ssim(img_a, img_b, full=True)

    return {
        "image_a": str(img_path_a),
        "image_b": str(img_path_b),
        "ssim_score": round(score, 4),
        "similarity_pct": round(score * 100, 2),
        "method": "SSIM",
    }


def compare_session_screenshots(session_label: str) -> list[dict]:
    """
    Compare consecutive screenshots from a capture session to detect
    significant visual changes (board state transitions).
    """
    ss_dir = ROOT / "data" / "captures" / "screenshots" / session_label

    if not ss_dir.exists():
        print(f"❌ No screenshots found for session: {session_label}")
        return []

    screenshots = sorted(ss_dir.glob("*.png"))
    if len(screenshots) < 2:
        print(f"⚠️  Need at least 2 screenshots to compare (found {len(screenshots)})")
        return []

    results = []
    print(f"\n📸 Comparing {len(screenshots)} screenshots from session: {session_label}")
    print("=" * 60)

    for i in range(len(screenshots) - 1):
        a = screenshots[i]
        b = screenshots[i + 1]

        result = ssim_diff(str(a), str(b))
        result["index"] = i
        result["transition"] = f"{a.stem} → {b.stem}"
        results.append(result)

        similarity = result.get("similarity_pct", 0)
        indicator = "🟢" if similarity > 95 else "🟡" if similarity > 80 else "🔴"
        print(f"  {indicator} Frame {i:03d}→{i+1:03d}: {similarity:.1f}% similar")

    # Summary
    if results:
        avg_sim = sum(r.get("similarity_pct", 0) for r in results) / len(results)
        big_changes = [r for r in results if r.get("similarity_pct", 100) < 85]
        print(f"\n📊 Average similarity: {avg_sim:.1f}%")
        print(f"🔴 Significant transitions: {len(big_changes)}")

    return results


def generate_diff_report(session_label: str, results: list[dict]) -> Path:
    """Save a JSON report of the screenshot comparisons."""
    report_dir = ROOT / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "session_label": session_label,
        "generated_at": datetime.now().isoformat(),
        "total_comparisons": len(results),
        "comparisons": results,
    }

    report_path = report_dir / f"screenshot_diff_{session_label}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"💾 Report saved: {report_path.name}")
    return report_path


def correlate_screenshots_with_events(
    screenshots_dir: Path,
    extraction,
) -> list[dict]:
    """Correlate screenshots with game events by timestamp matching.

    Each screenshot filename encodes its capture timestamp (from the
    ``ss_{label}_{reason}_{timestamp}.png`` naming pattern). This function
    matches each screenshot to the closest game round and trick by comparing
    timestamps.

    @param screenshots_dir: Path to session screenshots directory.
    @param extraction: ExtractionResult from trick_extractor (has rounds with tricks).
    @returns List of dicts with screenshot path, matched round/trick, and metadata.
    """
    if not screenshots_dir.exists():
        return []

    screenshots = sorted(screenshots_dir.glob("*.png"))
    if not screenshots:
        return []

    # Build a timeline of trick timestamps for matching
    trick_timeline: list[dict] = []
    for rnd in extraction.rounds:
        for trick in rnd.tricks:
            trick_timeline.append({
                "round_index": rnd.round_index,
                "trick_number": trick.trick_number,
                "timestamp": trick.timestamp,
                "game_mode": rnd.game_mode_raw,
            })

    if not trick_timeline:
        # No trick data to match against — assign all to round -1
        return [
            {
                "path": str(ss),
                "filename": ss.name,
                "round_index": -1,
                "trick_number": -1,
                "timestamp_delta_ms": 0,
                "reason": _parse_screenshot_reason(ss.name),
            }
            for ss in screenshots
        ]

    correlated: list[dict] = []
    for ss in screenshots:
        ss_ts = _parse_screenshot_timestamp(ss.name)
        reason = _parse_screenshot_reason(ss.name)

        # Find the closest trick by timestamp
        best_match = None
        best_delta = float("inf")
        for entry in trick_timeline:
            delta = abs(ss_ts - entry["timestamp"])
            if delta < best_delta:
                best_delta = delta
                best_match = entry

        correlated.append({
            "path": str(ss),
            "filename": ss.name,
            "round_index": best_match["round_index"] if best_match else -1,
            "trick_number": best_match["trick_number"] if best_match else -1,
            "timestamp_delta_ms": round(best_delta, 1) if best_match else 0,
            "game_mode": best_match["game_mode"] if best_match else "",
            "reason": reason,
        })

    return correlated


def _parse_screenshot_timestamp(filename: str) -> float:
    """Extract epoch timestamp from screenshot filename.

    Expected patterns:
    - ``ss_{label}_{reason}_{timestamp}.png``
    - ``screenshot_{timestamp}.png``
    - If parsing fails, returns 0.0.

    @param filename: Screenshot filename (stem + extension).
    @returns Epoch milliseconds, or 0.0 if unparseable.
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    # Try the last numeric part as timestamp
    for part in reversed(parts):
        try:
            ts = float(part)
            if ts > 1_000_000_000:  # Looks like epoch ms or seconds
                return ts if ts > 1_000_000_000_000 else ts * 1000
        except ValueError:
            continue
    return 0.0


def _parse_screenshot_reason(filename: str) -> str:
    """Extract capture reason from screenshot filename.

    @param filename: Screenshot filename.
    @returns Reason string (e.g., 'periodic', 'a_card_played'), or 'unknown'.
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    # Pattern: ss_{label}_{reason}_{timestamp}
    if len(parts) >= 3 and parts[0] == "ss":
        # Reason is everything between label and timestamp
        # Try to reconstruct: parts[2:-1] if last part is numeric
        try:
            float(parts[-1])
            reason_parts = parts[2:-1]
            if reason_parts:
                return "_".join(reason_parts)
        except ValueError:
            pass
    return "unknown"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GBaloot Screenshot Diff")
    parser.add_argument("--session", "-s", help="Session label to compare screenshots for")
    parser.add_argument("--compare", "-c", nargs=2, metavar=("IMG_A", "IMG_B"),
                        help="Compare two specific images")
    args = parser.parse_args()

    if args.compare:
        result = ssim_diff(args.compare[0], args.compare[1])
        print(json.dumps(result, indent=2))
    elif args.session:
        results = compare_session_screenshots(args.session)
        if results:
            generate_diff_report(args.session, results)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
