"""
🎮 GBaloot Capture Session — Single-Command Game Data Capture

Usage:
    python gbaloot/capture_session.py --label hokum_aggressive_01
    python gbaloot/capture_session.py --label sun_defensive_02 --headless
    python gbaloot/capture_session.py --label practice --no-screenshots

Captures WebSocket traffic + periodic screenshots from the game platform.
On exit, automatically runs: decode → process → benchmark comparison.
"""
import argparse
import json
import re
import sys
import time
import signal
from datetime import datetime
from pathlib import Path

# ── Ensure project root is importable ────────────────────────────────
ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gbaloot.core.capturer import (
    WS_INTERCEPTOR_JS,
    collect_messages,
    save_capture,
    GameCapturer,
)
from gbaloot.core.event_types import SCREENSHOT_TRIGGERS

# ── Constants ────────────────────────────────────────────────────────
DEFAULT_URL = "https://kammelna.com/baloot/"
CAPTURES_DIR = ROOT / "data" / "captures"
SESSIONS_DIR = ROOT / "data" / "sessions"
SCREENSHOTS_DIR = ROOT / "data" / "captures" / "screenshots"

# Collect interval (seconds) — how often we pull WS messages
WS_COLLECT_INTERVAL = 10
# Autosave interval (seconds) — how often we persist to disk
AUTOSAVE_INTERVAL = 30
# Screenshot interval (seconds) — periodic background screenshots
SCREENSHOT_INTERVAL = 30


def parse_args():
    parser = argparse.ArgumentParser(
        description="GBaloot Capture Session — record live game data"
    )
    parser.add_argument(
        "--label", "-l",
        default=f"session_{datetime.now().strftime('%Y%m%d_%H%M')}",
        help="Session label (e.g. hokum_aggressive_01, sun_defensive_02)"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Game URL (default: {DEFAULT_URL})"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window)"
    )
    parser.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Disable periodic screenshots"
    )
    parser.add_argument(
        "--no-pipeline",
        action="store_true",
        help="Skip post-session auto-pipeline (decode + benchmark)"
    )
    parser.add_argument(
        "--screenshot-interval",
        type=int,
        default=SCREENSHOT_INTERVAL,
        help=f"Seconds between periodic screenshots (default: {SCREENSHOT_INTERVAL})"
    )
    parser.add_argument(
        "--collect-interval",
        type=int,
        default=WS_COLLECT_INTERVAL,
        help=f"Seconds between WS message collections (default: {WS_COLLECT_INTERVAL})"
    )
    parser.add_argument(
        "--autopilot",
        action="store_true",
        help="Enable autopilot mode (bot plays for you)"
    )
    parser.add_argument(
        "--username",
        type=str,
        default=None,
        help="Your Kammelna username (required for --autopilot seat detection)"
    )
    return parser.parse_args()


# ── Screenshot Helper ────────────────────────────────────────────────

def take_screenshot(page, output_dir: Path, label: str, reason: str = "periodic") -> Path:
    """Take a timestamped screenshot and return the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ss_{label}_{reason}_{timestamp}.png"
    filepath = output_dir / filename
    try:
        page.screenshot(path=str(filepath), full_page=False)
        return filepath
    except Exception as e:
        print(f"  [!] Screenshot failed: {e}")
        return None


def _is_keyword_match(keyword: str, data_str: str) -> bool:
    """R4: Match keyword as a distinct token (not bare substring).

    Uses delimiters common in JSON/SFS2X text to avoid false positives
    like 'pass' matching 'password' or 'eating' matching 'creating'.
    """
    pattern = r'(?:^|["\s,{:])' + re.escape(keyword) + r'(?:["\s,}:]|$)'
    return bool(re.search(pattern, data_str, re.IGNORECASE))


def detect_game_events(messages: list) -> list[str]:
    """
    Scan WS messages for game-relevant actions that should trigger screenshots.
    Returns list of action names detected.
    """
    detected = []
    for msg in messages:
        data_str = msg.get("data", "")
        if not isinstance(data_str, str):
            continue
        # R4: Use delimiter-aware matching instead of bare substring
        # R5: Use unified SCREENSHOT_TRIGGERS from event_types.py
        for action in SCREENSHOT_TRIGGERS:
            if _is_keyword_match(action, data_str):
                detected.append(action)
                break
    return detected


def _autosave_rotating(all_ws: list, output_dir: Path, label: str):
    """R7: Save to a single rotating autosave file (overwrite, not accumulate).

    Prevents storage pollution from creating a new file every 30 seconds.
    The _final file supersedes this on clean exit.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    autosave_path = output_dir / f"game_capture_{label}_autosave.json"
    try:
        with open(autosave_path, "w", encoding="utf-8") as f:
            json.dump({
                "captured_at": datetime.now().isoformat(),
                "label": f"{label}_autosave",
                "ws_messages": len(all_ws),
                "xhr_requests": 0,
                "websocket_traffic": all_ws,
                "http_traffic": [],
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [!] Autosave failed: {e}")


def _update_manifest(capture_file: Path, label: str, session, report=None):
    """R11: Append session metadata to the manifest index.

    Creates or updates gbaloot/data/manifest.json with per-session
    metadata for fast lookup without scanning directories.
    """
    manifest_path = ROOT / "data" / "manifest.json"
    try:
        # Load existing manifest
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        else:
            manifest = {"sessions": []}

        # Build session entry
        entry = {
            "label": label,
            "capture_file": capture_file.name,
            "captured_at": datetime.now().isoformat(),
            "ws_count": len(session.events) if session else 0,
        }

        if report:
            entry["tricks_extracted"] = report.total_tricks
            entry["agreement_pct"] = report.winner_agreement_pct
            entry["divergences"] = report.total_divergences

        # Deduplicate by label (update existing or append)
        existing_idx = next(
            (i for i, s in enumerate(manifest["sessions"]) if s.get("label") == label),
            None
        )
        if existing_idx is not None:
            manifest["sessions"][existing_idx] = entry
        else:
            manifest["sessions"].append(entry)

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [!] Manifest update failed: {e}")


# ── Live Status Display ──────────────────────────────────────────────

class StatusDisplay:
    """Minimal terminal status display for capture sessions."""

    def __init__(self, label: str):
        self.label = label
        self.start_time = time.time()
        self.ws_count = 0
        self.screenshot_count = 0
        self.autosave_count = 0
        self.last_event = ""

    def update(self, ws_count: int, screenshot_count: int, autosave_count: int, last_event: str = ""):
        self.ws_count = ws_count
        self.screenshot_count = screenshot_count
        self.autosave_count = autosave_count
        if last_event:
            self.last_event = last_event

        elapsed = time.time() - self.start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)

        status = (
            f"\r📡 [{self.label}] "
            f"{mins:02d}:{secs:02d} | "
            f"WS: {self.ws_count} | "
            f"📸: {self.screenshot_count} | "
            f"💾: {self.autosave_count}"
        )
        if self.last_event:
            status += f" | 🎮 {self.last_event}"

        # Pad to clear previous line
        print(status.ljust(100), end="", flush=True)


# ── Post-Session Pipeline ────────────────────────────────────────────

def run_post_pipeline(capture_file: Path, label: str):
    """Run decode → process → benchmark comparison on the capture file."""
    print(f"\n\n{'='*60}")
    print(f"🔄 POST-SESSION PIPELINE")
    print(f"{'='*60}")

    # ── Step 1: Decode ───────────────────────────────────────────
    print("\n⚙️  Step 1/3: Decoding binary SFS2X traffic...")
    try:
        from gbaloot.core.decoder import GameDecoder
        from gbaloot.core.models import ProcessedSession

        decoder = GameDecoder(str(capture_file))
        decoder.load()
        decoder.decode_all()

        if not decoder.events:
            print("   ⚠️  No events decoded (session may have no game data)")
            return

        print(f"   ✅ Decoded {len(decoder.events)} events")

        # Build and save ProcessedSession (same pattern as process.py)
        session = ProcessedSession(
            capture_path=str(capture_file),
            captured_at=decoder.capture.get("captured_at", ""),
            label=label,
            stats=decoder.stats,
            events=[
                {
                    "timestamp": ev.timestamp,
                    "direction": ev.direction,
                    "action": ev.action,
                    "fields": ev.fields,
                    "raw_size": ev.raw_size,
                    "decode_errors": ev.decode_errors,
                }
                for ev in decoder.events
            ],
            timeline=decoder.get_game_timeline(),
        )
        out_path = session.save(SESSIONS_DIR)
        print(f"   💾 Saved: {out_path.name}")
    except Exception as e:
        print(f"   ❌ Decode failed: {e}")
        return

    # ── Step 2: Extract tricks ───────────────────────────────────
    print("\n🔍 Step 2/3: Extracting tricks from session...")
    try:
        from gbaloot.core.trick_extractor import extract_tricks
        extraction = extract_tricks(session.events, session_path=str(capture_file))
        print(f"   ✅ Extracted {extraction.total_tricks} tricks from {len(extraction.rounds)} rounds")
        if extraction.extraction_warnings:
            for w in extraction.extraction_warnings[:3]:
                print(f"   ⚠️  {w}")
    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        return

    # ── Step 3: Benchmark comparison ─────────────────────────────
    print("\n📊 Step 3/3: Running engine comparison...")
    try:
        from gbaloot.core.comparator import GameComparator
        comparator = GameComparator()
        report = comparator.compare_session(session.events, session_path=str(capture_file))
        print(f"   ✅ Compared {report.total_tricks} tricks")
        print(f"   🎯 Winner agreement: {report.winner_agreement_pct:.1f}%")
        print(f"   ⚡ Divergences: {report.total_divergences}")
        if report.total_divergences > 0:
            print(f"   📋 Breakdown: {report.divergence_breakdown}")

        # R10: Persist comparison report to disk
        reports_dir = ROOT / "data" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"comparison_{label}_{timestamp}.json"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False, default=str)
            print(f"   💾 Report saved: {report_path.name}")
        except Exception as e:
            print(f"   ⚠️  Could not save report: {e}")

    except Exception as e:
        print(f"   ❌ Comparison failed: {e}")

    # ── R11: Update session manifest ─────────────────────────────
    _update_manifest(capture_file, label, session, locals().get('report'))

    print(f"\n{'='*60}")
    print(f"✅ PIPELINE COMPLETE")
    print(f"{'='*60}\n")


# ── Main Capture Loop ────────────────────────────────────────────────

def main():
    args = parse_args()

    # Validate label format
    label = args.label.replace(" ", "_").replace("-", "_").lower()

    # Validate autopilot args
    if args.autopilot and not args.username:
        print("❌ --autopilot requires --username (your Kammelna username)")
        sys.exit(1)

    autopilot_label = '✅ Enabled' if args.autopilot else '❌ Disabled'
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  🎮  GBaloot Capture Session                            ║
╠══════════════════════════════════════════════════════════╣
║  Label:        {label:<40s} ║
║  URL:          {args.url:<40s} ║
║  Screenshots:  {'❌ Disabled' if args.no_screenshots else '✅ Enabled':<40s} ║
║  SS Interval:  {str(args.screenshot_interval) + 's':<40s} ║
║  Auto-Pipeline:{'❌ Disabled' if args.no_pipeline else '✅ Enabled':<40s} ║
║  Autopilot:    {autopilot_label:<40s} ║
╚══════════════════════════════════════════════════════════╝
""")

    # ── Setup directories ────────────────────────────────────────
    for d in [CAPTURES_DIR, SESSIONS_DIR, SCREENSHOTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # Session-specific screenshot dir
    ss_dir = SCREENSHOTS_DIR / label
    ss_dir.mkdir(parents=True, exist_ok=True)

    # ── Launch Playwright ────────────────────────────────────────
    print("🚀 Launching browser...", flush=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    capturer = GameCapturer(CAPTURES_DIR)
    capturer.is_running = True
    capturer.start_time = time.time()
    status = StatusDisplay(label)
    screenshot_count = 0
    autosave_count = 0
    last_autosave = time.time()
    last_screenshot = time.time()
    last_collect = time.time()
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        running = False
        print("\n\n⏹  Stopping capture...", flush=True)

    signal.signal(signal.SIGINT, signal_handler)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=args.headless,
            channel="chrome",  # Use real installed Chrome (native zoom)
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Inject WS interceptor BEFORE navigation
        page.add_init_script(WS_INTERCEPTOR_JS)

        print(f"🌐 Navigating to {args.url}...", flush=True)
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"⚠️  Navigation warning (may still work): {e}")

        # Also inject after load (in case it wasn't caught)
        try:
            page.evaluate(WS_INTERCEPTOR_JS)
        except Exception:
            pass

        # Take initial screenshot
        if not args.no_screenshots:
            ss_path = take_screenshot(page, ss_dir, label, "initial")
            if ss_path:
                screenshot_count += 1
                print(f"📸 Initial screenshot saved", flush=True)

        # ── Autopilot mode ─────────────────────────────────────
        autopilot = None
        if args.autopilot:
            from gbaloot.autopilot import AutopilotSession
            print(f"🤖 AUTOPILOT MODE — Bot will play as '{args.username}'")
            print(f"   Kill switch: create gbaloot/.pause to pause\n")
            autopilot = AutopilotSession(page, username=args.username)
            # Don't call autopilot.start() — it would block.
            # Instead, we integrate into the capture loop below.
            # Inject interceptor & run recon
            try:
                autopilot.gboard.initialize_sync()
            except Exception as e:
                print(f"   ⚠️  GBoard recon: {e}")

        if autopilot:
            print(f"\n🎮 AUTOPILOT ACTIVE — Bot is playing! Press Ctrl+C to stop.\n")
        else:
            print(f"\n🎮 CAPTURE ACTIVE — Play your games! Press Ctrl+C to stop.\n")

        # ── Main capture loop (R3: KeyboardInterrupt as primary) ──
        try:
            while running:
                now = time.time()

                # Collect WS messages periodically
                if now - last_collect >= args.collect_interval:
                    new_msgs = capturer.collect_from_page(page)
                    last_collect = now

                    # Feed messages to autopilot (if active)
                    if autopilot and new_msgs > 0:
                        recent = capturer.all_ws[-new_msgs:]
                        for msg in recent:
                            try:
                                autopilot._process_message(msg)
                            except Exception:
                                pass
                        # Check if it's our turn
                        if (autopilot.state_builder.is_my_turn()
                                and autopilot.gboard.is_ready):
                            try:
                                autopilot._act()
                            except Exception as e:
                                print(f"\n  [!] Autopilot action error: {e}")

                    # Check for game events that should trigger screenshots
                    if new_msgs > 0 and not args.no_screenshots:
                        recent = capturer.all_ws[-new_msgs:]
                        events = detect_game_events(recent)
                        if events:
                            reason = events[0]  # Use first detected event as reason
                            ss_path = take_screenshot(page, ss_dir, label, reason)
                            if ss_path:
                                screenshot_count += 1
                                # R9: Reset periodic timer after event screenshot
                                last_screenshot = now
                                status.update(
                                    capturer.message_count, screenshot_count,
                                    autosave_count, reason
                                )

                # Periodic screenshots (independent of events)
                if (not args.no_screenshots
                        and now - last_screenshot >= args.screenshot_interval):
                    ss_path = take_screenshot(page, ss_dir, label, "periodic")
                    if ss_path:
                        screenshot_count += 1
                    last_screenshot = now

                # R7: Autosave to single rotating file (overwrite, not accumulate)
                if now - last_autosave >= AUTOSAVE_INTERVAL:
                    if capturer.message_count > 0:
                        autosave_count += 1
                        _autosave_rotating(capturer.all_ws, CAPTURES_DIR, label)
                    last_autosave = now

                # Update status display
                status.update(
                    capturer.message_count, screenshot_count,
                    autosave_count, ""
                )

                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            running = False
            print("\n\n⏹  Stopping capture...", flush=True)

        # ── Save final capture ───────────────────────────────────
        print("\n💾 Saving final capture...", flush=True)

        # Final screenshot
        if not args.no_screenshots:
            take_screenshot(page, ss_dir, label, "final")
            screenshot_count += 1

        # Save all WS data
        final_label = f"{label}_final"
        final_path = capturer.save(final_label)
        print(f"   ✅ Saved: {final_path.name}")
        print(f"   📊 Total WS messages: {capturer.message_count}")
        print(f"   📸 Total screenshots: {screenshot_count}")
        print(f"   ⏱  Duration: {capturer.duration_sec:.0f}s")

        # R7: Clean up rotating autosave (final file supersedes it)
        autosave_path = CAPTURES_DIR / f"game_capture_{label}_autosave.json"
        if autosave_path.exists():
            try:
                autosave_path.unlink()
            except Exception:
                pass

        # ── Cleanup browser (R2: timeout guard) ─────────────────
        try:
            browser.close()
        except Exception:
            pass  # Browser already gone or hung

    # ── Post-session pipeline ────────────────────────────────────
    if not args.no_pipeline and capturer.message_count > 0:
        run_post_pipeline(final_path, label)
    elif capturer.message_count == 0:
        print("\n⚠️  No WS messages captured. Skipping pipeline.")

    # ── Summary ──────────────────────────────────────────────────
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  📋  SESSION SUMMARY                                    ║
╠══════════════════════════════════════════════════════════╣
║  Label:        {label:<40s} ║
║  Duration:     {capturer.duration_sec:.0f}s{' '*(38 - len(f'{capturer.duration_sec:.0f}s'))} ║
║  WS Messages:  {str(capturer.message_count):<40s} ║
║  Screenshots:  {str(screenshot_count):<40s} ║
║  Autosaves:    {str(autosave_count):<40s} ║
║  Final File:   {final_path.name:<40s} ║
╚══════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
