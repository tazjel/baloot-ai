"""
Capture Engine — Playwright-powered game session recorder.

Manages headed browser sessions for playing Kammelna while recording
video, taking screenshots, and logging game actions.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from . import signalr_interceptor

# Lazy import playwright to avoid crashing if not installed
_playwright_mod = None
_sync_playwright = None


def _ensure_playwright():
    """Lazy-load playwright only when needed."""
    global _playwright_mod, _sync_playwright
    if _playwright_mod is None:
        from playwright.sync_api import sync_playwright
        _sync_playwright = sync_playwright
    return _sync_playwright


# ── Paths ────────────────────────────────────────────────────────

CAPTURES_DIR = Path(__file__).resolve().parent.parent / "captures"
SESSIONS_DIR = CAPTURES_DIR / "sessions"
SCREENSHOTS_DIR = CAPTURES_DIR / "screenshots"
LOGS_DIR = CAPTURES_DIR / "logs"
ANNOTATIONS_DIR = CAPTURES_DIR / "annotations"

for d in [SESSIONS_DIR, SCREENSHOTS_DIR, LOGS_DIR, ANNOTATIONS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

KAMMELNA_URL = "***REDACTED_URL***"
KAMMELNA_LOGIN_URL = "***REDACTED_URL***"
import logging
logger = logging.getLogger(__name__)

# ── Session State (module-level singleton) ───────────────────────

_active_session = {
    "id": None,
    "name": None,
    "playwright": None,
    "browser": None,
    "context": None,
    "page": None,
    "started_at": None,
    "screenshots": [],
    "actions": [],
    "video_dir": None,
}


def is_session_active() -> bool:
    """Check if a capture session is currently running."""
    return _active_session["page"] is not None


def get_session_info() -> dict:
    """Get info about the active session."""
    if not is_session_active():
        return {"active": False}
    return {
        "active": True,
        "id": _active_session["id"],
        "name": _active_session["name"],
        "started_at": _active_session["started_at"],
        "screenshot_count": len(_active_session["screenshots"]),
        "action_count": len(_active_session["actions"]),
    }


def start_session(name: str = None, url: str = None,
                  email: str = None, password: str = None) -> dict:
    """Start a new capture session.
    
    Opens a headed browser to Kammelna with video recording enabled.
    If email/password are provided, auto-logs in via the main website first.
    Returns session info dict.
    """
    if is_session_active():
        return {"error": "Session already active. Stop it first."}

    sync_pw = _ensure_playwright()
    
    # Generate session ID
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"{ts}_{name or 'session'}"
    session_name = name or f"session_{ts}"
    
    # Video output directory for this session
    video_dir = SESSIONS_DIR / session_id
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Log file
    log_file = LOGS_DIR / f"{session_id}.jsonl"
    
    try:
        pw = sync_pw().__enter__()
        browser = pw.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1280, "height": 720},
            locale="ar-SA",
            timezone_id="Asia/Riyadh",
        )
        page = context.new_page()
        
        # ── Auto-login if credentials provided ──────────────────
        if email and password:
            try:
                logger.info("Auto-login: navigating to login page...")
                page.goto(KAMMELNA_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
                
                # Fill login form
                page.fill("#email", email)
                page.fill("#password", password)
                page.click("#login-button")
                
                # Wait for login to complete (redirect or page change)
                page.wait_for_load_state("networkidle", timeout=15000)
                logger.info("Auto-login: login submitted, navigating to game...")
            except Exception as e:
                logger.warning(f"Auto-login failed: {e}. Continuing to game page...")
        
        # Navigate to game page
        target_url = url or KAMMELNA_URL
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        
        # Inject SignalR interceptor hooks before game connects
        signalr_interceptor.inject_interceptor(page)
        
        # SignalR message log file
        signalr_log = LOGS_DIR / f"{session_id}_signalr.jsonl"
        
        # Store session state
        _active_session.update({
            "id": session_id,
            "name": session_name,
            "playwright": pw,
            "browser": browser,
            "context": context,
            "page": page,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "screenshots": [],
            "actions": [],
            "video_dir": str(video_dir),
            "log_file": str(log_file),
            "signalr_log": str(signalr_log),
        })
        
        # Log session start
        _log_action("session_start", {
            "url": target_url,
            "name": session_name,
        })
        
        return {
            "success": True,
            "session_id": session_id,
            "name": session_name,
            "video_dir": str(video_dir),
            "message": f"Browser opened to {target_url}. Play your game!",
        }
        
    except Exception as e:
        # Cleanup on failure
        try:
            if 'browser' in dir() and browser:
                browser.close()
            if 'pw' in dir() and pw:
                pw.__exit__(None, None, None)
        except:
            pass
        return {"error": f"Failed to start session: {e}"}


def take_screenshot(annotation: str = "") -> dict:
    """Take a screenshot of the current page.
    
    Returns screenshot path and metadata.
    """
    if not is_session_active():
        return {"error": "No active session"}
    
    page = _active_session["page"]
    session_id = _active_session["id"]
    idx = len(_active_session["screenshots"]) + 1
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Screenshot file
    filename = f"{session_id}_shot{idx:03d}_{ts}.png"
    filepath = SCREENSHOTS_DIR / filename
    
    try:
        page.screenshot(path=str(filepath), full_page=False)
        
        # Metadata
        meta = {
            "session_id": session_id,
            "index": idx,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "annotation": annotation,
            "file": filename,
            "page_url": page.url,
            "page_title": page.title(),
        }
        
        # Save metadata alongside screenshot
        meta_path = filepath.with_suffix(".json")
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        
        _active_session["screenshots"].append(meta)
        _log_action("screenshot", {"file": filename, "annotation": annotation})
        
        return {
            "success": True,
            "path": str(filepath),
            "meta": meta,
        }
        
    except Exception as e:
        return {"error": f"Screenshot failed: {e}"}


def log_action(action_type: str, details: str = "") -> dict:
    """Log a game action/observation.
    
    action_type: e.g., "bid", "play_card", "trump_call", "observation", "strategy"
    details: free-text description
    """
    if not is_session_active():
        return {"error": "No active session"}
    
    _log_action(action_type, {"details": details})
    return {"success": True, "action_type": action_type}


def capture_messages() -> dict:
    """Collect SignalR messages mid-session and save to log.
    
    Returns message count and connection status.
    """
    if not is_session_active():
        return {"error": "No active session"}
    
    page = _active_session["page"]
    signalr_log = _active_session.get("signalr_log")
    
    # Collect messages from the browser buffer
    messages = signalr_interceptor.collect_messages(page)
    
    # Save to JSONL file
    saved = 0
    if messages and signalr_log:
        saved = signalr_interceptor.save_messages_to_file(messages, signalr_log)
    
    # Get connection status
    status = signalr_interceptor.get_connection_status(page)
    
    return {
        "success": True,
        "messages_collected": len(messages),
        "messages_saved": saved,
        "connection": status,
        "messages": messages[-20:],  # Return last 20 for UI display
    }


def get_signalr_status() -> dict:
    """Get SignalR connection status without collecting messages."""
    if not is_session_active():
        return {"connected": False, "active": False}
    
    page = _active_session["page"]
    status = signalr_interceptor.get_connection_status(page)
    status["active"] = True
    return status


def stop_session() -> dict:
    """Stop the current capture session.
    
    Closes browser, finalizes video, saves session summary.
    """
    if not is_session_active():
        return {"error": "No active session"}
    
    session_id = _active_session["id"]
    session_name = _active_session["name"]
    started = _active_session["started_at"]
    screenshot_count = len(_active_session["screenshots"])
    action_count = len(_active_session["actions"])
    video_dir = _active_session["video_dir"]
    signalr_log = _active_session.get("signalr_log")
    
    # Flush remaining SignalR messages before closing
    signalr_count = 0
    try:
        page = _active_session["page"]
        remaining = signalr_interceptor.collect_messages(page)
        if remaining and signalr_log:
            signalr_count = signalr_interceptor.save_messages_to_file(remaining, signalr_log)
    except Exception:
        pass
    
    _log_action("session_end", {
        "screenshots": screenshot_count,
        "actions": action_count,
        "signalr_messages_flushed": signalr_count,
    })
    
    # Close browser
    try:
        if _active_session["context"]:
            _active_session["context"].close()
        if _active_session["browser"]:
            _active_session["browser"].close()
        if _active_session["playwright"]:
            _active_session["playwright"].__exit__(None, None, None)
    except Exception:
        pass
    
    # Count total SignalR messages saved
    total_signalr = 0
    if signalr_log and Path(signalr_log).exists():
        total_signalr = sum(1 for line in Path(signalr_log).read_text(encoding="utf-8").strip().split("\n") if line)
    
    # Save session summary
    summary = {
        "session_id": session_id,
        "name": session_name,
        "started_at": started,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "screenshot_count": screenshot_count,
        "action_count": action_count,
        "signalr_message_count": total_signalr,
        "video_dir": video_dir,
        "signalr_log": signalr_log,
        "screenshots": _active_session["screenshots"],
    }
    
    summary_path = LOGS_DIR / f"{session_id}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # Reset state
    _active_session.update({
        "id": None, "name": None, "playwright": None,
        "browser": None, "context": None, "page": None,
        "started_at": None, "screenshots": [], "actions": [],
        "video_dir": None, "log_file": None, "signalr_log": None,
    })
    
    return {
        "success": True,
        "session_id": session_id,
        "screenshots": screenshot_count,
        "actions": action_count,
        "signalr_messages": total_signalr,
        "video_dir": video_dir,
        "summary_path": str(summary_path),
    }


def _log_action(action_type: str, data: dict):
    """Append an action to the session log file."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action_type,
        **data,
    }
    _active_session["actions"].append(entry)
    
    log_file = _active_session.get("log_file")
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


# ── Library Functions (for browsing past captures) ───────────────

def list_sessions() -> list[dict]:
    """List all saved capture sessions."""
    sessions = []
    for f in sorted(LOGS_DIR.glob("*_summary.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append(data)
        except Exception:
            continue
    return sessions


def list_screenshots(session_id: str = None) -> list[dict]:
    """List screenshots, optionally filtered by session."""
    shots = []
    for f in sorted(SCREENSHOTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if session_id and data.get("session_id") != session_id:
                continue
            data["_meta_path"] = str(f)
            data["_image_path"] = str(f.with_suffix(".png"))
            shots.append(data)
        except Exception:
            continue
    return shots


def get_session_log(session_id: str) -> list[dict]:
    """Read the action log for a session."""
    log_file = LOGS_DIR / f"{session_id}.jsonl"
    if not log_file.exists():
        return []
    actions = []
    for line in log_file.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            try:
                actions.append(json.loads(line))
            except Exception:
                continue
    return actions


def get_session_videos(session_id: str) -> list[str]:
    """Get video file paths for a session."""
    video_dir = SESSIONS_DIR / session_id
    if not video_dir.exists():
        return []
    return [str(f) for f in video_dir.glob("*.webm")]
