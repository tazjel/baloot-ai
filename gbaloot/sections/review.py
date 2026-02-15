"""
🔍 Review Section — Deep analysis of decoded game sessions.

Event timeline, action charts, cross-session comparison, and pattern detection.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from ..core.decoder import GameDecoder, decode_card
from ..core.models import ProcessedSession, GameEvent, BoardState
from ..core.reconstructor import reconstruct_timeline
from ..core.session_manifest import load_manifest, get_entry_by_filename, HEALTH_ICONS

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
        manifest = load_manifest(sessions_dir)
        def _rev_label(name: str) -> str:
            if manifest:
                entry = get_entry_by_filename(manifest, name)
                if entry:
                    return f"{HEALTH_ICONS.get(entry.health, '')} {name}"
            return name
        selected = st.selectbox("Select Session", [f.name for f in session_files], format_func=_rev_label, key="rev_session")
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
    events_data = session.events or []
    
    # 1. Reconstruct Timeline
    @st.cache_data
    def _get_timeline(data):
        events = [GameEvent(**e) for e in data]
        return reconstruct_timeline(events)
    
    timeline = _get_timeline(events_data)
    
    # Header stats
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", stats.get("total_messages", 0))
    c2.metric("Decoded", stats.get("decoded_ok", 0))
    c3.metric("Errors", stats.get("decode_errors", 0))
    dur = 0
    if events_data and len(events_data) > 1:
        dur = (events_data[-1].get("timestamp", 0) - events_data[0].get("timestamp", 0)) / 1000
    c4.metric("Duration", f"{dur:.0f}s")

    # 2. Playback Control
    st.markdown("---")
    st.markdown("##### 🏎️ Visual Playback")
    
    if not timeline:
        st.warning("No timeline data to visualize.")
    else:
        idx = st.slider("Scrub Timeline", 0, len(timeline)-1, 0, key="rev_scrub")
        current_state = timeline[idx]
        _render_visual_board(current_state)

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

def _render_visual_board(state: BoardState):
    """Renders a CSS-based game board."""
    st.markdown("""
    <style>
    .baloot-board {
        display: grid;
        grid-template-areas:
            ". top ."
            "left center right"
            ". bottom .";
        grid-template-columns: 1fr 2fr 1fr;
        grid-template-rows: 1fr 2fr 1fr;
        gap: 15px;
        background-color: #1a4a1a;
        padding: 24px;
        border-radius: 12px;
        border: 4px solid #3d2b1f;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        color: white;
        font-family: 'Inter', sans-serif;
    }
    .player-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        padding: 10px;
    }
    .p-top { grid-area: top; }
    .p-bottom { grid-area: bottom; border-color: #58a6ff; background: rgba(88,166,255,0.1); }
    .p-left { grid-area: left; }
    .p-right { grid-area: right; }
    .p-center { 
        grid-area: center; 
        background: rgba(0,0,0,0.3); 
        border: 2px dashed rgba(255,255,255,0.2);
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        align-items: center;
    }
    .card {
        width: 45px;
        height: 65px;
        background: white;
        border-radius: 4px;
        margin: 2px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: black;
        font-weight: bold;
        font-size: 0.8rem;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }
    .suit-H { color: #f85149; }
    .suit-D { color: #f85149; }
    .suit-C { color: black; }
    .suit-S { color: black; }
    </style>
    """, unsafe_allow_html=True)

    # Prepare player boxes
    slots = {"TOP": "p-top", "BOTTOM": "p-bottom", "LEFT": "p-left", "RIGHT": "p-right"}
    players_html = ""
    for p in state.players:
        cls = slots.get(p.position, "p-bottom")
        dealer_tag = " <span style='color:#f8e3a1'>💎</span>" if p.is_dealer else ""
        active_style = "border: 2px solid #58a6ff;" if p.id == state.current_player_id else ""
        
        # Hand display
        hand_html = '<div style="display:flex; flex-wrap:wrap; justify-content:center; margin-top:5px;">'
        for card in p.hand:
            c_val, c_suit = _parse_card(card)
            hand_html += f'<div class="card suit-{c_suit}">{c_val}{c_suit}</div>'
        hand_html += '</div>'
        
        players_html += f"""
        <div class="player-box {cls}" style="{active_style}">
            <div style="font-size:0.8rem; opacity:0.8;">{p.name}{dealer_tag}</div>
            {hand_html}
        </div>"""

    # Center cards — now (seat, card_string) tuples
    center_html = ""
    for item in state.center_cards:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            seat, card_str = item
            c_val, c_suit = _parse_card(card_str)
            label = f"S{seat}"
            center_html += f'<div class="card suit-{c_suit}"><div style="font-size:0.5rem;opacity:0.5">{label}</div>{c_val}{c_suit}</div>'
        else:
            c_val, c_suit = _parse_card(str(item))
            center_html += f'<div class="card suit-{c_suit}">{c_val}{c_suit}</div>'

    board_html = f"""
    <div class="baloot-board">
        {players_html}
        <div class="player-box p-center">
            {center_html}
        </div>
    </div>
    """
    st.markdown(board_html, unsafe_allow_html=True)

    # Status bar — use new field names
    mode_label = state.game_mode or "—"
    trump_label = state.trump_suit or "—"
    scores = state.scores if isinstance(state.scores, list) else [0, 0, 0, 0]
    score_str = f"T1 {scores[0]+scores[2]} — T2 {scores[1]+scores[3]}" if len(scores) == 4 else "—"
    st.write(f"**Phase:** {state.phase} | **Mode:** {mode_label} | **Trump:** {trump_label} | **Trick:** {state.trick_number} | **Round:** {state.round_number} | **Score:** {score_str}")

SUIT_CSS: dict[str, str] = {"♥": "H", "♦": "D", "♣": "C", "♠": "S"}

def _parse_card(card_str: str) -> tuple[str, str]:
    """Parse a card string like ``'A♠'`` or ``'10♥'`` into (rank, CSS-class-letter).

    Returns ('?', '?') for unparsable input.
    """
    if not card_str:
        return "?", "?"
    # Unicode suit is always the last character
    suit_char = card_str[-1]
    css = SUIT_CSS.get(suit_char)
    if css:
        return card_str[:-1], css
    # Fallback: old format like "7H"
    if len(card_str) >= 2 and card_str[-1] in "HSDC":
        return card_str[:-1], card_str[-1]
    return card_str, "?"


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
