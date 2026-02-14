"""
🎬 Capture Section — Launch and monitor game recordings.

Start Playwright, inject the WS interceptor, and record live game data.
"""
import streamlit as st
from pathlib import Path
from datetime import datetime
import json


def render():
    """Render the Capture section."""

    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(63, 185, 80, 0.1) 0%, rgba(22, 27, 34, 0.6) 100%);
        border: 1px solid rgba(63, 185, 80, 0.25);
        border-radius: 12px;
        padding: 20px 24px; margin-bottom: 20px;
    ">
        <h2 style="margin:0 0 4px 0; color: #3fb950;">🎬 Capture</h2>
        <p style="margin:0; color: #8b949e; font-size: 0.9rem;">
            Record live Baloot games — WebSocket traffic captured in real time
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Capture Status ───────────────────────────────────────────
    status = st.session_state.get("capture_status", {})

    if status.get("running"):
        st.success(
            f"🔴 **Recording** — "
            f"{status.get('messages', 0)} messages, "
            f"{status.get('duration', 0):.0f}s elapsed"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⏹ Stop Recording", type="primary", use_container_width=True):
                st.session_state["capture_status"] = {"running": False}
                st.rerun()
        with col2:
            if st.button("📊 Refresh Stats", use_container_width=True):
                st.rerun()
        with col3:
            st.metric("Messages", status.get("messages", 0))
    else:
        _render_start_form()

    # ── Capture Library ──────────────────────────────────────────
    st.markdown("---")
    _render_library()


def _render_start_form():
    """Form to start a new capture session."""
    st.subheader("🚀 Start New Capture")

    col1, col2 = st.columns([3, 1])
    with col1:
        label = st.text_input(
            "Session label",
            placeholder="e.g. hokum_aggressive_study",
            key="cap_label",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        start = st.button("▶️ Launch", type="primary", use_container_width=True, key="cap_start")

    with st.expander("⚙️ Capture Settings", expanded=False):
        game_url = st.text_input(
            "Game URL",
            value=st.session_state.get("game_url", ""),
            key="cap_url",
            help="The URL to navigate to for game capture"
        )
        headless = st.checkbox("Headless mode (no visible browser)", value=False, key="cap_headless")

    if start:
        st.info(
            "🔧 **Capture requires Playwright** — run the capture script in a terminal:\n\n"
            "```\npython tools/capture_archive.py\n```\n\n"
            "Captured files will appear in `captures/` and be available in the **Process** tab."
        )


def _render_library():
    """Show existing capture files."""
    st.subheader("📚 Capture Library")

    from ..core.models import CaptureSession

    captures_dir = Path(__file__).resolve().parents[1] / "data" / "captures"
    project_captures = Path(__file__).resolve().parents[2] / "captures"

    # Scan both directories
    capture_files = []
    for d in [captures_dir, project_captures]:
        if d.exists():
            capture_files.extend(sorted(d.glob("game_capture_*.json"), key=lambda p: p.stat().st_mtime, reverse=True))

    if not capture_files:
        st.info("No captures found. Run a capture session, or place `.json` files in `captures/`.")
        return

    st.caption(f"Found {len(capture_files)} capture files")

    for i, f in enumerate(capture_files[:20]):
        size_kb = f.stat().st_size / 1024
        mod_time = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

        with st.container():
            col_name, col_size, col_time = st.columns([3, 1, 1])
            with col_name:
                st.markdown(f"📄 **{f.name}**")
            with col_size:
                st.caption(f"{size_kb:.1f} KB")
            with col_time:
                st.caption(mod_time)
