"""
🔓 Protocol Decoder — Visual Binary Protocol Analysis Dashboard

Provides a comprehensive Streamlit UI for decoding and analyzing
captured game WebSocket binary traffic using the TLV decoder engine.

Features:
  - Capture file selector
  - Decode statistics and success rate
  - Action breakdown bar chart
  - Searchable/filterable event timeline
  - Detailed message viewer on row selection
"""
import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime

# Add tools/ to path so we can import game_decoder
TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from game_decoder import GameDecoder, decode_card

CAPTURES_DIR = TOOLS_DIR.parent / "captures"


# ── Helpers ──────────────────────────────────────────────────────

def _get_capture_files() -> list[Path]:
    """List available capture files sorted by modification time (newest first)."""
    if not CAPTURES_DIR.exists():
        return []
    files = sorted(
        CAPTURES_DIR.glob("game_capture_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files


def _format_timestamp(epoch_ms: float) -> str:
    """Format epoch milliseconds to human-readable time."""
    if epoch_ms <= 0:
        return "—"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000).strftime("%H:%M:%S.%f")[:-3]
    except Exception:
        return str(epoch_ms)


def _field_display(fields: dict, max_depth: int = 3) -> str:
    """Pretty-format decoded TLV fields for display."""
    try:
        return json.dumps(fields, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(fields)


# ── Action Colors ────────────────────────────────────────────────

ACTION_COLORS = {
    "a_card_played": "#58a6ff",
    "a_cards_eating": "#f0883e",
    "a_accept_next_move": "#8b949e",
    "a_bid": "#f778ba",
    "hokom": "#d29922",
    "sira": "#7ee787",
    "signalr": "#484f58",
    "ws_connect": "#3fb950",
    "unknown": "#30363d",
    "<decode_error>": "#f85149",
}


# ── Main Render ──────────────────────────────────────────────────

def render_protocol_decoder():
    """Render the Protocol Decoder dashboard tab."""

    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(88, 166, 255, 0.08) 0%, rgba(139, 148, 158, 0.05) 100%);
        border: 1px solid rgba(88, 166, 255, 0.2);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
    ">
        <h2 style="margin:0 0 4px 0; color: #58a6ff;">🔓 Protocol Decoder</h2>
        <p style="margin:0; color: #8b949e; font-size: 0.9rem;">
            Binary TLV protocol analysis for captured game WebSocket traffic
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── File Selector ────────────────────────────────────────────
    files = _get_capture_files()

    if not files:
        st.warning("No capture files found in `captures/` directory. Run a game capture first.")
        return

    col_select, col_info = st.columns([3, 1])

    with col_select:
        file_labels = [f.name for f in files]
        selected_idx = st.selectbox(
            "📁 Select Capture File",
            range(len(file_labels)),
            format_func=lambda i: file_labels[i],
            key="decoder_file_select",
        )

    selected_file = files[selected_idx]

    with col_info:
        size_kb = selected_file.stat().st_size / 1024
        st.metric("File Size", f"{size_kb:.1f} KB")

    # ── Decode Button ────────────────────────────────────────────
    if st.button("🔓 Decode Capture", type="primary", key="decode_btn", use_container_width=True):
        with st.spinner("Decoding binary protocol..."):
            _run_decode(selected_file)

    # ── Results ──────────────────────────────────────────────────
    if "decoder_result" in st.session_state:
        _render_results()


@st.cache_data(ttl=300)
def _cached_decode(file_path: str):
    """Decode a capture file with caching."""
    decoder = GameDecoder(file_path)
    decoder.load()
    decoder.decode_all()
    return {
        "stats": decoder.stats,
        "events": [
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
        "capture_meta": {
            "captured_at": decoder.capture.get("captured_at", "N/A"),
            "label": decoder.capture.get("label", "N/A"),
        },
        "timeline": decoder.get_game_timeline(),
    }


def _run_decode(file_path: Path):
    """Execute decode and store results in session state."""
    try:
        result = _cached_decode(str(file_path))
        st.session_state["decoder_result"] = result
        st.session_state["decoder_file"] = file_path.name
        st.rerun()
    except Exception as e:
        st.error(f"Decode failed: {e}")


def _render_results():
    """Render the decoded results UI."""
    result = st.session_state["decoder_result"]
    stats = result["stats"]
    meta = result["capture_meta"]

    # ── Header Stats ─────────────────────────────────────────────
    st.markdown(f"##### 📊 Decoded: `{st.session_state.get('decoder_file', '')}`")
    st.caption(f"Captured: {meta['captured_at']} · Label: {meta['label']}")

    c1, c2, c3, c4, c5 = st.columns(5)
    total = stats["total_messages"]
    decoded = stats["decoded_ok"]
    errors = stats["decode_errors"]
    rate = (decoded / stats["binary_messages"] * 100) if stats["binary_messages"] > 0 else 0

    c1.metric("Total Messages", total)
    c2.metric("Binary", stats["binary_messages"])
    c3.metric("JSON / SignalR", stats["json_messages"])
    c4.metric("Decoded OK", decoded, delta=f"{rate:.1f}%")
    c5.metric("Errors", errors, delta=f"-{errors}" if errors > 0 else "0", delta_color="inverse")

    st.markdown("---")

    # ── Action Breakdown ─────────────────────────────────────────
    actions = stats.get("actions_found", {})
    if actions:
        col_chart, col_table = st.columns([2, 1])

        with col_chart:
            st.markdown("##### 🎯 Action Breakdown")
            sorted_actions = sorted(actions.items(), key=lambda x: -x[1])

            # Use Streamlit's built-in bar chart
            import pandas as pd
            df = pd.DataFrame(sorted_actions, columns=["Action", "Count"])
            df = df.set_index("Action")
            st.bar_chart(df, color="#58a6ff")

        with col_table:
            st.markdown("##### 📋 Action Counts")
            for action, count in sorted_actions:
                pct = count / total * 100 if total > 0 else 0
                color = ACTION_COLORS.get(action, "#8b949e")
                st.markdown(
                    f'<div style="display:flex; justify-content:space-between; '
                    f'padding:4px 8px; margin:2px 0; border-radius:4px; '
                    f'background:rgba(22,27,34,0.6); border-left:3px solid {color};">'
                    f'<span style="color:#c9d1d9; font-size:0.85rem;">{action}</span>'
                    f'<span style="color:{color}; font-weight:600;">{count}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # ── Event Timeline ───────────────────────────────────────────
    st.markdown("##### ⏱️ Event Timeline")

    events = result["events"]

    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        direction_filter = st.selectbox(
            "Direction",
            ["All", "SEND", "RECV", "CONNECT"],
            key="decoder_dir_filter",
        )
    with fcol2:
        action_options = ["All"] + sorted(set(e["action"] for e in events))
        action_filter = st.selectbox(
            "Action Type",
            action_options,
            key="decoder_action_filter",
        )
    with fcol3:
        search_text = st.text_input("🔍 Search fields", key="decoder_search", placeholder="card, player, bid...")

    # Filter events
    filtered = events
    if direction_filter != "All":
        filtered = [e for e in filtered if e["direction"] == direction_filter]
    if action_filter != "All":
        filtered = [e for e in filtered if e["action"] == action_filter]
    if search_text:
        search_low = search_text.lower()
        filtered = [
            e for e in filtered
            if search_low in json.dumps(e["fields"], default=str).lower()
            or search_low in e["action"].lower()
        ]

    st.caption(f"Showing {len(filtered)} of {len(events)} events")

    # Display as scrollable table
    if filtered:
        # Paginate for performance
        page_size = 50
        total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            key="decoder_page",
        )
        start = (page - 1) * page_size
        page_events = filtered[start : start + page_size]

        for i, ev in enumerate(page_events):
            idx = start + i
            ts = _format_timestamp(ev["timestamp"])
            d = ev["direction"]
            a = ev["action"]
            size = ev["raw_size"]
            errs = ev.get("decode_errors", [])
            color = ACTION_COLORS.get(a, "#8b949e")
            dir_icon = "⬆️" if d == "SEND" else "⬇️" if d == "RECV" else "🔌"
            err_badge = f' <span style="color:#f85149;">⚠ {len(errs)}</span>' if errs else ""

            with st.expander(
                f"`{ts}` {dir_icon} **{a}** ({size}B){' ⚠️' if errs else ''}",
                expanded=False,
            ):
                # Show key fields inline
                fields = ev["fields"]
                if a == "a_card_played" and ("card" in fields or "c" in fields):
                    card = fields.get("card", fields.get("c", ""))
                    st.markdown(f"**Card:** `{decode_card(str(card))}`")
                elif a == "a_bid" and ("bid" in fields or "b" in fields):
                    bid = fields.get("bid", fields.get("b", ""))
                    st.markdown(f"**Bid:** `{bid}`")

                # Full fields
                st.code(_field_display(fields), language="json")

                if errs:
                    for err in errs:
                        st.warning(f"Decode note: {err}")
    else:
        st.info("No events match the current filters.")
