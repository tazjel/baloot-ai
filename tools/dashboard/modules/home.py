"""
🏠 Home — Mission Control Dashboard Landing Page

Gives an instant overview of project health:
  - Git status (branch, dirty files)
  - Service health (Redis, Backend, Frontend)
  - Roadmap progress (parsed from ROADMAP.md)
  - Last test run summary
  - Quick action buttons
"""
import streamlit as st
import subprocess
import json
import re
import socket
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HISTORY_FILE = Path(__file__).parent.parent / "test_history.json"
ROADMAP_FILE = PROJECT_ROOT / "ROADMAP.md"


# =============================================================================
#  HELPERS
# =============================================================================

def _run_cmd(cmd, timeout=5):
    """Run a shell command and return stdout."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, shell=True,
                           cwd=str(PROJECT_ROOT), timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def _check_port(port):
    """Check if a port is listening on localhost."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def _parse_roadmap():
    """Parse ROADMAP.md for mission progress."""
    if not ROADMAP_FILE.exists():
        return []
    missions = []
    current = None
    try:
        with open(str(ROADMAP_FILE), "r", encoding="utf-8") as f:
            for line in f:
                # Match ## Mission N: Title
                m = re.match(r"^## (Mission \d+: .+?)(?:\s*\(.*\))?\s*$", line)
                if m:
                    if current:
                        missions.append(current)
                    current = {"name": m.group(1), "done": 0, "total": 0}
                    continue
                # Match - [x] or - [ ] items
                if current and re.match(r"^- \[[ x/]\]", line):
                    current["total"] += 1
                    if line.startswith("- [x]"):
                        current["done"] += 1
        if current:
            missions.append(current)
    except Exception:
        pass
    return missions


def _load_last_test():
    """Load the last test run from history."""
    if not HISTORY_FILE.exists():
        return None
    try:
        with open(str(HISTORY_FILE), "r", encoding="utf-8") as f:
            history = json.load(f)
        return history[-1] if history else None
    except Exception:
        return None


# =============================================================================
#  RENDER
# =============================================================================

def render_home_tab():
    st.header("🏠 Mission Control")
    st.caption("Instant project health overview — your daily launchpad.")

    # ── Row 1: Git + Services ───────────────────────────
    col_git, col_svc = st.columns(2)

    with col_git:
        st.subheader("📂 Git Status")
        branch = _run_cmd("git rev-parse --abbrev-ref HEAD")
        dirty = _run_cmd("git status --short")
        last_commit = _run_cmd("git log -1 --format=%s")
        last_author = _run_cmd("git log -1 --format=%an")
        last_time = _run_cmd("git log -1 --format=%ar")

        dirty_count = len([l for l in dirty.splitlines() if l.strip()]) if dirty else 0
        status_icon = "🟢" if dirty_count == 0 else "🟡"

        st.markdown(f"""
        <div style="background:#111827; padding:16px; border-radius:8px; border:1px solid #374151;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:1.1em;">🌿 <b>{branch or 'unknown'}</b></span>
                <span>{status_icon} {dirty_count} dirty file{'s' if dirty_count != 1 else ''}</span>
            </div>
            <div style="color:#9CA3AF; font-size:0.85em;">
                Last: <b>{last_commit or 'N/A'}</b><br/>
                by {last_author or '?'} · {last_time or '?'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_svc:
        st.subheader("🩺 Service Health")
        services = [
            ("Redis", 6379, "🔴"),
            ("Backend", 3005, "🌐"),
            ("Frontend", 5173, "⚛️"),
        ]

        svc_html = ""
        for name, port, icon in services:
            alive = _check_port(port)
            color = "#22c55e" if alive else "#ef4444"
            badge = "● ONLINE" if alive else "○ OFFLINE"
            svc_html += f"""
            <div style="display:flex; justify-content:space-between; padding:8px 12px;
                        border-bottom:1px solid #1f2937;">
                <span>{icon} <b>{name}</b> <span style="color:#6B7280;">:{port}</span></span>
                <span style="color:{color}; font-weight:600;">{badge}</span>
            </div>
            """

        st.markdown(f"""
        <div style="background:#111827; border-radius:8px; border:1px solid #374151; overflow:hidden;">
            {svc_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Row 2: Roadmap Progress ─────────────────────────
    st.subheader("🗺️ Roadmap Progress")
    missions = _parse_roadmap()

    if missions:
        # Summary metrics
        total_items = sum(m["total"] for m in missions)
        done_items = sum(m["done"] for m in missions)
        overall_pct = round(done_items / max(total_items, 1) * 100)

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Total Tasks", total_items)
        mc2.metric("Completed", done_items)
        mc3.metric("Overall", f"{overall_pct}%")

        # Per-mission progress bars
        for m in missions:
            pct = round(m["done"] / max(m["total"], 1) * 100)
            if pct == 100:
                color = "#22c55e"
                icon = "✅"
            elif pct > 0:
                color = "#3b82f6"
                icon = "🔵"
            else:
                color = "#6B7280"
                icon = "⬜"

            st.markdown(f"""
            <div style="margin-bottom:6px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                    <span>{icon} <b>{m['name']}</b></span>
                    <span>{m['done']}/{m['total']} ({pct}%)</span>
                </div>
                <div style="background:#1f2937; border-radius:4px; height:10px; overflow:hidden;">
                    <div style="width:{min(pct, 100)}%; background:{color}; height:100%;
                                border-radius:4px; transition:width 0.3s;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("ROADMAP.md not found or empty.")

    st.markdown("---")

    # ── Row 3: Last Test Run ────────────────────────────
    st.subheader("🧪 Last Test Run")
    last = _load_last_test()

    if last:
        tc1, tc2, tc3, tc4, tc5 = st.columns(5)
        passed = last.get("passed", 0)
        failed = last.get("failed", 0)
        total = last.get("total", 0)
        rate = round(passed / max(total, 1) * 100, 1)

        result_icon = "✅" if failed == 0 else "❌"
        tc1.metric(f"{result_icon} Result", f"{rate}% pass")
        tc2.metric("✅ Passed", passed)
        tc3.metric("❌ Failed", failed)
        tc4.metric("⏱️ Duration", f"{last.get('duration', 0)}s")
        cov = last.get("coverage")
        tc5.metric("🛡️ Coverage", f"{cov}%" if cov else "N/A")

        ts = last.get("timestamp", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                st.caption(f"Run at: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception:
                st.caption(f"Run at: {ts}")
    else:
        st.info("No test history yet. Run tests from the 🧪 Test Manager tab.")

    st.markdown("---")

    # ── Row 4: Quick Actions ────────────────────────────
    st.subheader("⚡ Quick Actions")
    qa1, qa2, qa3, qa4 = st.columns(4)

    with qa1:
        if st.button("🧪 Run All Tests", type="primary", use_container_width=True):
            st.session_state["_navigate_to_tests"] = True
            st.info("Switch to the 🧪 Test Manager tab and click Run Tests.")

    with qa2:
        if st.button("🧹 Flush Redis", use_container_width=True):
            from .utils import get_redis_client
            r = get_redis_client()
            if r:
                r.flushall()
                st.success("Redis flushed! ✅")
            else:
                st.error("Redis not connected.")

    with qa3:
        if st.button("📋 Deep Scan Report", use_container_width=True):
            from .reports import generate_deep_diagnostic_report
            with st.spinner("Generating..."):
                report = generate_deep_diagnostic_report()
            st.session_state["agent_report"] = report
            st.success("Report ready! Check 📈 Reports tab.")

    with qa4:
        if st.button("🔄 Refresh All", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
