"""
Terminal Tab — Interactive command runner and queue monitor.

Provides:
- Custom command input with live execution
- Preset command palette for common operations
- Command queue monitor (auto-executing agent commands)
- Command history with results
"""

import streamlit as st
import subprocess
import time
from datetime import datetime
from pathlib import Path
from .utils import get_redis_client
from . import cmd_queue

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])

# ── Preset Commands ──────────────────────────────────────────────

PRESETS = {
    "🧪 Testing": [
        ("Run All Tests", "pytest tests/ -v --tb=short"),
        ("Unit Tests Only", "pytest tests/unit/ -v"),
        ("Integration Tests", "pytest tests/integration/ -v"),
        ("Turbo Tests", "powershell -ExecutionPolicy Bypass -File ./scripts/test_turbo.ps1"),
        ("Test with Coverage", "pytest tests/ --cov=server --cov-report=term-missing"),
    ],
    "🚀 Server": [
        ("Launch Full Stack", "powershell -ExecutionPolicy Bypass -File ./scripts/launch/launch_ww.ps1"),
        ("Check Backend Port", "powershell Test-NetConnection -ComputerName localhost -Port 3005 -WarningAction SilentlyContinue"),
        ("Check Frontend Port", "powershell Test-NetConnection -ComputerName localhost -Port 5173 -WarningAction SilentlyContinue"),
    ],
    "🔍 Code Quality": [
        ("Flake8 Lint", "flake8 server/ --max-line-length=120 --count"),
        ("Git Status", "git status --short"),
        ("Git Diff (Staged)", "git diff --cached --stat"),
        ("Git Log (5)", "git log --oneline -5"),
    ],
    "🧹 Maintenance": [
        ("Redis Ping", "redis-cli ping"),
        ("Redis Info", "redis-cli info server"),
        ("Redis Keys Count", "redis-cli dbsize"),
        ("Pip List", "pip list --format=columns"),
        ("Docker PS", "docker ps --format \"table {{.Names}}\\t{{.Status}}\""),
    ],
}


def render_terminal_tab():
    st.header("⚡ Terminal")
    st.caption("Run commands directly • AI agents auto-execute via queue")

    r = get_redis_client()

    # ── Queue Monitor ────────────────────────────────────────────
    if r:
        queue_size = cmd_queue.get_queue_size(r)
        if queue_size > 0:
            st.info(f"📬 **{queue_size} command(s) in queue** — auto-executing...")
            # Process one command per page load to keep UI responsive
            result = cmd_queue.poll_and_execute(r)
            if result:
                _display_result(result)
                st.rerun()
        
        # Show active queue toggle
        auto_poll = st.toggle("🤖 Auto-Poll Queue", value=True, key="term_auto_poll",
                              help="When enabled, the dashboard automatically executes queued commands on every refresh")
        if auto_poll and queue_size > 0:
            time.sleep(2)
            st.rerun()

    # ── Custom Command ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("🖥️ Run Command")

    col_cmd, col_run = st.columns([5, 1])
    with col_cmd:
        custom_cmd = st.text_input(
            "Command",
            placeholder="e.g. pytest tests/unit/test_scoring.py -v",
            key="term_custom_cmd",
            label_visibility="collapsed",
        )
    with col_run:
        run_clicked = st.button("▶️ Run", type="primary", use_container_width=True, key="term_run")

    # Timeout setting
    timeout = st.slider("Timeout (seconds)", 10, 300, 120, step=10, key="term_timeout")

    if run_clicked and custom_cmd.strip():
        cmd = custom_cmd.strip()
        is_safe, reason = cmd_queue.is_command_safe(cmd)
        if not is_safe:
            st.error(f"🚫 **Blocked**: {reason}")
            st.caption("Add this command pattern to `ALLOW_PATTERNS` in `cmd_queue.py` if it's safe.")
        else:
            with st.spinner(f"Running: `{cmd}`..."):
                result = _execute_direct(cmd, timeout)
            _display_result(result)

    # ── Preset Palette ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("🎛️ Command Palette")

    palette_tabs = st.tabs(list(PRESETS.keys()))
    for tab, (category, commands) in zip(palette_tabs, PRESETS.items()):
        with tab:
            for label, cmd in commands:
                col_l, col_r = st.columns([4, 1])
                col_l.code(cmd, language="bash")
                btn_key = f"preset_{label.replace(' ', '_')}"
                if col_r.button(f"▶️ {label}", key=btn_key, use_container_width=True):
                    with st.spinner(f"Running: {label}..."):
                        result = _execute_direct(cmd, timeout=120)
                    _display_result(result)

    # ── Command History ──────────────────────────────────────────
    if r:
        st.markdown("---")
        st.subheader("📜 Command History")

        history = cmd_queue.get_recent_history(r, count=15)
        if not history:
            st.caption("No commands executed yet. Run something!")
        else:
            for entry in history:
                status = entry.get("status", "?")
                cmd = entry.get("cmd", "?")
                tag = entry.get("tag", "")
                duration = entry.get("duration", "?")
                ts = entry.get("finished_at", entry.get("started_at", ""))[:19]

                if status == "success":
                    icon = "✅"
                elif status == "failed":
                    icon = "❌"
                elif status == "blocked":
                    icon = "🚫"
                elif status == "timeout":
                    icon = "⏰"
                else:
                    icon = "❓"

                with st.expander(f"{icon} `{cmd}` — {duration}s ({ts})", expanded=False):
                    if entry.get("stdout"):
                        st.code(entry["stdout"], language="text")
                    if entry.get("stderr"):
                        st.error("stderr:")
                        st.code(entry["stderr"], language="text")
                    if entry.get("reason"):
                        st.warning(entry["reason"])

    # ── Push Command (for agents) ────────────────────────────────
    if r:
        st.markdown("---")
        with st.expander("🤖 Agent Command Queue — Push Interface"):
            st.caption("AI agents can push commands here. The dashboard auto-executes them.")
            agent_cmd = st.text_input("Command to queue", key="term_agent_cmd",
                                       placeholder="e.g. pytest tests/ --tb=short")
            agent_tag = st.text_input("Tag (optional)", key="term_agent_tag", placeholder="unit-tests")
            if st.button("📬 Push to Queue", key="term_push"):
                if agent_cmd.strip():
                    cmd_id = cmd_queue.push_command(r, agent_cmd.strip(), tag=agent_tag)
                    st.success(f"Queued: `{agent_cmd}` → ID: `{cmd_id}`")
                else:
                    st.warning("Enter a command first.")


def _execute_direct(cmd: str, timeout: int = 120) -> dict:
    """Execute a command directly and return a result dict."""
    started = datetime.utcnow()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            cwd=PROJECT_ROOT,
            timeout=timeout,
        )
        duration = round((datetime.utcnow() - started).total_seconds(), 2)
        result = {
            "cmd": cmd,
            "status": "success" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "stdout": proc.stdout[-5000:] if len(proc.stdout) > 5000 else proc.stdout,
            "stderr": proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr,
            "duration": duration,
        }
    except subprocess.TimeoutExpired:
        result = {"cmd": cmd, "status": "timeout", "reason": f"Exceeded {timeout}s"}
    except Exception as e:
        result = {"cmd": cmd, "status": "error", "reason": str(e)}

    # Also store in Redis history if available
    r = get_redis_client()
    if r:
        import json, uuid
        result["id"] = str(uuid.uuid4())[:8]
        result["tag"] = cmd.split()[0] if cmd.split() else "cmd"
        result["finished_at"] = datetime.utcnow().isoformat()
        cmd_queue._store_result(r, result["id"], result)

    return result


def _display_result(result: dict):
    """Display a command execution result."""
    status = result.get("status", "?")
    cmd = result.get("cmd", "?")
    duration = result.get("duration", "?")

    if status == "success":
        st.success(f"✅ `{cmd}` completed in {duration}s")
    elif status == "failed":
        st.error(f"❌ `{cmd}` failed (exit {result.get('returncode', '?')})")
    elif status == "blocked":
        st.error(f"🚫 `{cmd}` — {result.get('reason', 'Blocked by safety rules')}")
        return
    elif status == "timeout":
        st.warning(f"⏰ `{cmd}` — {result.get('reason', 'Timed out')}")
        return
    else:
        st.warning(f"❓ `{cmd}` — {status}")

    if result.get("stdout"):
        st.code(result["stdout"], language="text")
    if result.get("stderr"):
        with st.expander("⚠️ stderr", expanded=False):
            st.code(result["stderr"], language="text")
