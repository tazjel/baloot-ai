"""
Game Capture Tab — Record and analyze Baloot gameplay.

Provides session management, screenshot capture, action logging,
and a viewer for past captures.
"""

import streamlit as st
from pathlib import Path
from . import capture_engine
import json


def render_capture_tab():
    st.header("🎬 Game Capture")
    st.caption("Record Baloot gameplay to train our AI — screenshots, video, and action logs")

    # ── Session Status ───────────────────────────────────────────
    info = capture_engine.get_session_info()

    if info["active"]:
        st.success(f"🔴 **Recording**: {info['name']} — "
                   f"{info['screenshot_count']} shots, {info['action_count']} actions")
        _render_active_controls()
    else:
        st.info("No active session. Start one to begin capturing gameplay.")
        _render_start_controls()

    # ── Capture Library ──────────────────────────────────────────
    st.markdown("---")
    _render_library()


def _render_start_controls():
    """Controls for starting a new capture session."""
    st.subheader("🚀 Start New Session")

    col1, col2 = st.columns([3, 1])
    with col1:
        session_name = st.text_input(
            "Session name",
            placeholder="e.g. hokum_aggressive_strategy",
            key="cap_session_name",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        start_clicked = st.button("▶️ Launch", type="primary",
                                   use_container_width=True, key="cap_start")

    url = st.text_input(
        "Game URL",
        value=capture_engine.GAME_URL or "",
        key="cap_url",
        help="Override the default game URL if needed"
    )

    # ── Login Credentials ────────────────────────────────────────
    with st.expander("🔐 Auto-Login Credentials", expanded=True):
        col_email, col_pass = st.columns(2)
        with col_email:
            email = st.text_input("Email", value="***REDACTED_EMAIL***",
                                  key="cap_email")
        with col_pass:
            password = st.text_input("Password", value="***REDACTED_PASSWORD***",
                                     type="password", key="cap_password")
        st.caption("Credentials are sent to the game server for auto-login. "
                   "Leave blank to login manually.")

    if start_clicked:
        name = session_name.strip() or None
        with st.spinner("Launching browser & logging in..."):
            result = capture_engine.start_session(
                name=name,
                url=url.strip() or None,
                email=email.strip() or None,
                password=password.strip() or None,
            )

        if result.get("success"):
            st.success(f"✅ {result['message']}")
            st.balloons()
            st.rerun()
        else:
            st.error(f"❌ {result.get('error', 'Unknown error')}")


def _render_active_controls():
    """Controls for an active recording session."""

    # ── Screenshot ───────────────────────────────────────────────
    st.subheader("📸 Capture")

    col_ann, col_snap = st.columns([4, 1])
    with col_ann:
        annotation = st.text_input(
            "Annotation",
            placeholder="e.g. Opponent led with trump Ace, I played 7",
            key="cap_annotation",
        )
    with col_snap:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📸 Screenshot", type="primary",
                      use_container_width=True, key="cap_screenshot"):
            result = capture_engine.take_screenshot(annotation.strip())
            if result.get("success"):
                st.success(f"✅ Saved: `{result['meta']['file']}`")
                # Show the screenshot
                try:
                    st.image(result["path"], caption=annotation or "Game capture",
                             use_container_width=True)
                except Exception:
                    pass
            else:
                st.error(result.get("error", "Screenshot failed"))

    # ── Action Logger ────────────────────────────────────────────
    st.subheader("📝 Log Game Action")

    col_type, col_detail = st.columns([1, 3])
    with col_type:
        action_type = st.selectbox(
            "Action Type",
            ["observation", "bid", "play_card", "trump_call", "strategy",
             "opponent_move", "trick_win", "round_end", "mistake", "insight"],
            key="cap_action_type",
        )
    with col_detail:
        action_detail = st.text_input(
            "Details",
            placeholder="Describe what happened...",
            key="cap_action_detail",
        )

    if st.button("📝 Log Action", key="cap_log_action"):
        if action_detail.strip():
            capture_engine.log_action(action_type, action_detail.strip())
            st.success(f"✅ Logged: [{action_type}] {action_detail}")
        else:
            st.warning("Enter details first.")

    # ── Quick Actions Row ────────────────────────────────────────
    st.markdown("---")
    st.subheader("🎯 Quick Capture")
    st.caption("One-click capture common game moments:")

    qc1, qc2, qc3, qc4, qc5 = st.columns(5)
    quick_actions = [
        (qc1, "🃏 My Hand", "hand_dealt", "Current hand dealt"),
        (qc2, "🏆 Trick Win", "trick_win", "Won this trick"),
        (qc3, "💡 Strategy", "strategy", "Strategic observation"),
        (qc4, "❌ Mistake", "mistake", "Made or observed a mistake"),
        (qc5, "🎯 Key Play", "play_card", "Important card play"),
    ]

    for col, label, atype, default_note in quick_actions:
        with col:
            if st.button(label, key=f"qc_{atype}", use_container_width=True):
                # Take screenshot + log
                ss = capture_engine.take_screenshot(f"[{atype}] {default_note}")
                capture_engine.log_action(atype, default_note)
                if ss.get("success"):
                    st.success(f"📸+📝 Captured!")
                else:
                    st.warning("Screenshot failed but action logged")

    # ── SignalR Live Feed ────────────────────────────────────────
    st.markdown("---")
    _render_signalr_feed()

    # ── Stop Session ─────────────────────────────────────────────
    st.markdown("---")
    col_stop, col_spacer = st.columns([1, 3])
    with col_stop:
        if st.button("⏹️ Stop Session", type="secondary",
                      use_container_width=True, key="cap_stop"):
            with st.spinner("Stopping... saving video..."):
                result = capture_engine.stop_session()
            if result.get("success"):
                st.success(f"✅ Session saved! "
                          f"{result['screenshots']} screenshots, "
                          f"{result['actions']} actions, "
                          f"{result.get('signalr_messages', 0)} SignalR messages")
                st.rerun()
            else:
                st.error(result.get("error", "Failed to stop"))


def _render_signalr_feed():
    """Live SignalR message feed during active session."""
    st.subheader("📡 SignalR Live Feed")
    st.caption("Real-time game messages intercepted from the game server")

    # Connection status
    status = capture_engine.get_signalr_status()
    hub_url = status.get("hub_url", "—")
    connected = status.get("connected", False)
    methods = status.get("methods_registered", [])
    ws_url = status.get("ws_url", "—")

    col_status, col_hub = st.columns([1, 3])
    with col_status:
        if connected:
            st.markdown("🟢 **Connected**")
        else:
            st.markdown("🟡 **Waiting for connection...**")
            st.caption("Log in and join a game")
    with col_hub:
        if hub_url and hub_url != "—":
            st.code(hub_url, language=None)

    if methods:
        with st.expander(f"📋 Registered Methods ({len(methods)})", expanded=False):
            st.write(", ".join(f"`{m}`" for m in methods))

    # Refresh button + message display
    col_refresh, col_spacer = st.columns([1, 3])
    with col_refresh:
        refresh = st.button("🔄 Refresh Messages", type="primary",
                            use_container_width=True, key="cap_signalr_refresh")

    if refresh:
        with st.spinner("Collecting messages..."):
            result = capture_engine.capture_messages()

        if result.get("success"):
            count = result.get("messages_collected", 0)
            saved = result.get("messages_saved", 0)
            st.success(f"✅ Collected **{count}** messages (saved {saved})")

            messages = result.get("messages", [])
            if messages:
                with st.expander(f"📨 Last {len(messages)} Messages", expanded=True):
                    for msg in reversed(messages):
                        ts = msg.get("ts", "")[-12:]  # HH:MM:SS.sss
                        direction = msg.get("dir", "?")
                        method = msg.get("method", "?")
                        args = msg.get("args", [])

                        icon = "⬇️" if direction == "recv" else "⬆️" if direction == "send" else "ℹ️"
                        args_preview = json.dumps(args, ensure_ascii=False)[:120]

                        st.markdown(
                            f"{icon} `{ts}` **{method}** — {args_preview}"
                        )
            else:
                st.info("No messages yet. Play a game to see data flow!")
        else:
            st.error(result.get("error", "Failed to collect messages"))


def _render_library():
    """Browse past capture sessions and screenshots."""
    st.subheader("📚 Capture Library")

    sessions = capture_engine.list_sessions()

    if not sessions:
        st.caption("No saved sessions yet. Start your first capture!")
        return

    st.markdown(f"**{len(sessions)} sessions** captured")

    for session in sessions[:10]:  # Show last 10
        sid = session.get("session_id", "?")
        name = session.get("name", sid)
        started = session.get("started_at", "")[:16]
        ended = session.get("ended_at", "")[:16]
        shots = session.get("screenshot_count", 0)
        actions = session.get("action_count", 0)
        signalr = session.get("signalr_message_count", 0)

        label_parts = [f"{shots} shots", f"{actions} actions"]
        if signalr:
            label_parts.append(f"{signalr} msgs")
        label = ", ".join(label_parts)

        with st.expander(f"🎬 **{name}** — {label} ({started})"):
            st.caption(f"📅 {started} → {ended}")

            # Videos
            videos = capture_engine.get_session_videos(sid)
            if videos:
                st.markdown("**🎥 Videos:**")
                for v in videos:
                    st.markdown(f"- `{Path(v).name}`")
                    try:
                        st.video(v)
                    except Exception:
                        st.caption(f"Cannot preview: {v}")

            # Screenshots
            shots_list = capture_engine.list_screenshots(sid)
            if shots_list:
                st.markdown(f"**📸 Screenshots ({len(shots_list)}):**")
                # Show in grid
                cols = st.columns(min(3, len(shots_list)))
                for i, shot in enumerate(shots_list[:9]):  # Max 9 preview
                    with cols[i % 3]:
                        img_path = shot.get("_image_path", "")
                        ann = shot.get("annotation", "")
                        if Path(img_path).exists():
                            st.image(img_path, caption=ann or f"Shot {shot.get('index', i+1)}",
                                     use_container_width=True)

            # Action log
            action_log = capture_engine.get_session_log(sid)
            if action_log:
                st.markdown(f"**📝 Action Log ({len(action_log)} entries):**")
                for entry in action_log:
                    ts = entry.get("timestamp", "")[:19]
                    action = entry.get("action", "?")
                    details = entry.get("details", "")
                    if action in ("session_start", "session_end"):
                        continue
                    st.markdown(f"- `{ts}` **[{action}]** {details}")
