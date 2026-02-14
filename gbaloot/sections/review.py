"""
🔍 Review Section — Deep analysis of decoded game sessions.

Event timeline, action charts, cross-session comparison, and pattern detection.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from ..core.decoder import GameDecoder, decode_card
from ..core.models import ProcessedSession

ACTION_COLORS = {
    "a_card_played": "#58a6ff", "a_cards_eating": "#f0883e",
    "a_accept_next_move": "#8b949e", "a_bid": "#f778ba",
    "hokom": "#d29922", "sira": "#7ee787", "signalr": "#484f58",
    "ws_connect": "#3fb950", "unknown": "#30363d", "<decode_error>": "#f85149",
}

def render():
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(88,166,255,0.1) 0%, rgba(22,27,34,0.6) 100%);
        border: 1px solid rgba(88,166,255,0.25); border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;">
        <h2 style="margin:0 0 4px 0; color: #58a6ff;">🔍 Review</h2>
        <p style="margin:0; color: #8b949e; font-size: 0.9rem;">Analyze decoded events, find patterns, compare sessions</p>
    </div>""", unsafe_allow_html=True)

    sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"
    session_files = _get_sessions(sessions_dir)

    # Also allow direct decode from captures
    capture_files = _get_captures()

    tab_session, tab_live = st.tabs(["📂 Processed Sessions", "🔓 Live Decode"])

    with tab_session:
        if not session_files:
            st.info("No processed sessions. Use **Process** tab first.")
            return
        selected = st.selectbox("Select Session", [f.name for f in session_files], key="rev_session")
        sel_path = next(f for f in session_files if f.name == selected)
        session = ProcessedSession.load(sel_path)
        _render_session_review(session)

    with tab_live:
        if not capture_files:
            st.info("No capture files found.")
            return
        selected_cap = st.selectbox("Select Capture", [f.name for f in capture_files], key="rev_capture")
        sel_cap = next(f for f in capture_files if f.name == selected_cap)
        if st.button("🔓 Decode & Review", type="primary", key="rev_decode"):
            with st.spinner("Decoding..."):
                decoder = GameDecoder(str(sel_cap))
                decoder.load()
                decoder.decode_all()
                session = ProcessedSession(
                    capture_path=str(sel_cap),
                    captured_at=decoder.capture.get("captured_at", ""),
                    label=decoder.capture.get("label", ""),
                    stats=decoder.stats,
                    events=[{"timestamp": e.timestamp, "direction": e.direction,
                             "action": e.action, "fields": e.fields,
                             "raw_size": e.raw_size, "decode_errors": e.decode_errors}
                            for e in decoder.events],
                    timeline=decoder.get_game_timeline(),
                )
                st.session_state["rev_live_session"] = session
                st.rerun()
        if "rev_live_session" in st.session_state:
            _render_session_review(st.session_state["rev_live_session"])


def _render_session_review(session: ProcessedSession):
    stats = session.stats or {}
    events = session.events or []

    # Stats
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", stats.get("total_messages", 0))
    c2.metric("Decoded", stats.get("decoded_ok", 0))
    c3.metric("Errors", stats.get("decode_errors", 0))
    dur = 0
    if events and len(events) > 1:
        dur = (events[-1].get("timestamp", 0) - events[0].get("timestamp", 0)) / 1000
    c4.metric("Duration", f"{dur:.0f}s")

    # Action breakdown
    actions = stats.get("actions_found", {})
    if actions:
        st.markdown("##### 🎯 Action Distribution")
        import pandas as pd
        df = pd.DataFrame(sorted(actions.items(), key=lambda x: -x[1]), columns=["Action", "Count"]).set_index("Action")
        st.bar_chart(df, color="#58a6ff")

    # Timeline
    st.markdown("---")
    st.markdown("##### ⏱️ Event Timeline")
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        dir_filter = st.selectbox("Direction", ["All", "SEND", "RECV", "CONNECT"], key="rev_dir")
    with fcol2:
        action_opts = ["All"] + sorted(set(e.get("action", "") for e in events))
        action_filter = st.selectbox("Action", action_opts, key="rev_action")
    with fcol3:
        search = st.text_input("🔍 Search", key="rev_search")

    filtered = events
    if dir_filter != "All":
        filtered = [e for e in filtered if e.get("direction") == dir_filter]
    if action_filter != "All":
        filtered = [e for e in filtered if e.get("action") == action_filter]
    if search:
        sl = search.lower()
        filtered = [e for e in filtered if sl in json.dumps(e.get("fields", {}), default=str).lower()]

    st.caption(f"Showing {len(filtered)} of {len(events)} events")

    page_size = 50
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page = st.number_input("Page", 1, total_pages, 1, key="rev_page")
    start = (page - 1) * page_size

    for ev in filtered[start:start + page_size]:
        ts = _fmt(ev.get("timestamp", 0))
        d = ev.get("direction", "")
        a = ev.get("action", "unknown")
        icon = "⬆️" if d == "SEND" else "⬇️" if d == "RECV" else "🔌"
        errs = ev.get("decode_errors", [])
        with st.expander(f"`{ts}` {icon} **{a}** ({ev.get('raw_size', 0)}B){'⚠️' if errs else ''}"):
            st.code(json.dumps(ev.get("fields", {}), indent=2, ensure_ascii=False, default=str), language="json")
            if errs:
                for err in errs:
                    st.warning(err)


def _get_sessions(d: Path) -> list[Path]:
    if not d.exists():
        return []
    return sorted(d.glob("*_processed.json"), key=lambda p: p.stat().st_mtime, reverse=True)

def _get_captures() -> list[Path]:
    sources = [
        Path(__file__).resolve().parents[1] / "data" / "captures",
        Path(__file__).resolve().parents[2] / "captures",
    ]
    files = []
    for d in sources:
        if d.exists():
            files.extend(d.glob("game_capture_*.json"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

def _fmt(epoch_ms: float) -> str:
    if epoch_ms <= 0:
        return "—"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000).strftime("%H:%M:%S.%f")[:-3]
    except Exception:
        return str(epoch_ms)
