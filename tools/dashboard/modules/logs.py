"""
📜 Logs — Enhanced System Log Viewer

Features:
  - Regex-aware filtering (not just string match)
  - Severity-based color coding (ERROR=red, WARNING=yellow)
  - Game ID extraction and filtering
  - Auto-refresh toggle
"""
import streamlit as st
import re
import time
from .utils import read_last_lines


LOG_FILES = {
    "Backend (Headless)": "logs/server_headless.out.log",
    "Backend (Stdout)": "logs/server_stdout.log",
    "Frontend (Headless)": "logs/frontend_headless.out.log",
    "Backend (Error)": "logs/server_headless.err.log",
    "Turbo Test Log": "logs/last_test_execution.log",
}

# Severity patterns
SEVERITY_COLORS = {
    "CRITICAL": "#dc2626",  # bright red
    "ERROR": "#ef4444",     # red
    "WARNING": "#eab308",   # yellow
    "WARN": "#eab308",      # yellow
    "INFO": "#60a5fa",      # blue
    "DEBUG": "#9CA3AF",     # gray
}


def _extract_game_ids(lines):
    """Extract unique game IDs from log lines."""
    ids = set()
    for line in lines:
        # Match common patterns: game_id=xxx, game:xxx:, "game_id": "xxx"
        for m in re.finditer(r'(?:game_id[=:"\s]+|game:)([a-zA-Z0-9_-]{4,})', line):
            ids.add(m.group(1))
    return sorted(ids)


def _colorize_line(line):
    """Return HTML for a color-coded log line."""
    # Strip trailing whitespace
    clean = line.rstrip()

    # Determine severity color
    color = "#d1d5db"  # default light gray
    for level, c in SEVERITY_COLORS.items():
        if level in clean.upper():
            color = c
            break

    # Escape HTML chars
    import html
    escaped = html.escape(clean)
    return f'<span style="color:{color};">{escaped}</span>'


def render_logs_tab():
    st.header("📜 System Logs")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        selected_log = st.selectbox("Select Log File", list(LOG_FILES.keys()))
    with col2:
        line_count = st.number_input("Lines to show", min_value=50, max_value=2000,
                                     value=200, step=50, key="log_line_count")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        auto_refresh = st.toggle("Auto-Refresh", value=False)

    # Read raw lines
    path = LOG_FILES[selected_log]
    lines = read_last_lines(path, n=line_count)

    # Game ID filter
    game_ids = _extract_game_ids(lines)
    if game_ids:
        game_filter = st.selectbox(
            "Filter by Game ID", ["All Games"] + game_ids,
            key="log_game_filter"
        )
    else:
        game_filter = "All Games"

    # Text/Regex filter
    filter_text = st.text_input(
        "🔍 Filter (supports regex)",
        placeholder="e.g. error|warning|TRICK_WIN",
        key="log_filter_input"
    )

    # Apply filters
    filtered = lines[:]

    # Game ID filter
    if game_filter != "All Games":
        filtered = [l for l in filtered if game_filter in l]

    # Regex / text filter
    if filter_text:
        try:
            pattern = re.compile(filter_text, re.IGNORECASE)
            filtered = [l for l in filtered if pattern.search(l)]
        except re.error:
            # Fallback to plain text if regex is invalid
            filtered = [l for l in filtered if filter_text.lower() in l.lower()]
            st.caption("⚠️ Invalid regex — using plain text match.")

    # Stats bar
    severity_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for l in filtered:
        upper = l.upper()
        if "ERROR" in upper or "CRITICAL" in upper:
            severity_counts["ERROR"] += 1
        elif "WARNING" in upper or "WARN" in upper:
            severity_counts["WARNING"] += 1
        elif "INFO" in upper:
            severity_counts["INFO"] += 1

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("📄 Lines", len(filtered))
    sc2.metric("🔴 Errors", severity_counts["ERROR"])
    sc3.metric("🟡 Warnings", severity_counts["WARNING"])
    sc4.metric("🔵 Info", severity_counts["INFO"])

    # Render options
    view_mode = st.radio("View Mode", ["Color-Coded", "Raw Text"], horizontal=True,
                         key="log_view_mode")

    if view_mode == "Color-Coded":
        # Build colorized HTML
        if filtered:
            html_lines = [_colorize_line(l) for l in filtered]
            html_content = "<br>".join(html_lines)
            st.markdown(f"""
            <div style="background:#0d1117; padding:16px; border-radius:8px;
                        font-family:'Cascadia Code','Fira Code',monospace; font-size:12px;
                        line-height:1.6; max-height:600px; overflow-y:auto;
                        border:1px solid #21262d;">
                {html_content}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No matching log lines.")
    else:
        log_text = "".join(filtered)
        st.code(log_text if log_text else "No matching log lines.", language="text")

    # Auto-refresh
    if auto_refresh:
        time.sleep(3)
        st.rerun()
