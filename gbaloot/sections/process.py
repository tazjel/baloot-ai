"""
⚙️ Process Section — Decode raw captures into structured events.

Select a capture file, run the SFS2X decoder, view stats, and save results.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime

from ..core.decoder import GameDecoder, decode_card
from ..core.models import ProcessedSession


def render():
    """Render the Process section."""

    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(210, 153, 34, 0.1) 0%, rgba(22, 27, 34, 0.6) 100%);
        border: 1px solid rgba(210, 153, 34, 0.25);
        border-radius: 12px;
        padding: 20px 24px; margin-bottom: 20px;
    ">
        <h2 style="margin:0 0 4px 0; color: #d29922;">⚙️ Process</h2>
        <p style="margin:0; color: #8b949e; font-size: 0.9rem;">
            Decode raw capture files into structured game events using the SFS2X protocol decoder
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── File Selector ────────────────────────────────────────────
    capture_files = _get_capture_files()

    if not capture_files:
        st.warning("No capture files found. Go to **Capture** to record a game first.")
        return

    col_select, col_info = st.columns([3, 1])

    with col_select:
        file_labels = [f.name for f in capture_files]
        selected_idx = st.selectbox(
            "📁 Select Capture File",
            range(len(file_labels)),
            format_func=lambda i: file_labels[i],
            key="proc_file_select",
        )

    selected_file = capture_files[selected_idx]

    with col_info:
        size_kb = selected_file.stat().st_size / 1024
        st.metric("File Size", f"{size_kb:.1f} KB")

    # ── Decode Controls ──────────────────────────────────────────
    col_decode, col_batch = st.columns(2)

    with col_decode:
        if st.button("🔓 Decode", type="primary", use_container_width=True, key="proc_decode"):
            with st.spinner("Decoding SFS2X binary protocol..."):
                _run_decode(selected_file)

    with col_batch:
        if st.button("⚡ Batch Decode All", use_container_width=True, key="proc_batch"):
            with st.spinner("Processing all captures..."):
                _batch_decode(capture_files)

    # ── Results ──────────────────────────────────────────────────
    if "proc_result" in st.session_state:
        _render_results()


def _get_capture_files() -> list[Path]:
    """Find capture files in both gbaloot/data and project captures/."""
    sources = [
        Path(__file__).resolve().parents[1] / "data" / "captures",
        Path(__file__).resolve().parents[2] / "captures",
    ]
    files = []
    for d in sources:
        if d.exists():
            files.extend(d.glob("game_capture_*.json"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _run_decode(file_path: Path):
    """Decode a single capture file and store in session state."""
    try:
        decoder = GameDecoder(str(file_path))
        decoder.load()
        decoder.decode_all()

        result = {
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
            "file_name": file_path.name,
            "file_path": str(file_path),
        }
        st.session_state["proc_result"] = result
        st.rerun()
    except Exception as e:
        st.error(f"Decode failed: {e}")


def _batch_decode(capture_files: list[Path]):
    """Decode all unprocessed capture files."""
    sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    for f in capture_files:
        out_file = sessions_dir / f"{f.stem}_processed.json"
        if out_file.exists():
            continue
        try:
            decoder = GameDecoder(str(f))
            decoder.load()
            decoder.decode_all()

            session = ProcessedSession(
                capture_path=str(f),
                captured_at=decoder.capture.get("captured_at", ""),
                label=decoder.capture.get("label", ""),
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
            session.save(sessions_dir)
            processed += 1
        except Exception as e:
            st.warning(f"Failed to decode {f.name}: {e}")

    skipped = len(capture_files) - processed
    st.success(f"Batch complete: {processed} new, {skipped} already processed")

    # Rebuild manifest after batch processing
    try:
        from gbaloot.core.session_manifest import build_manifest, save_manifest
        manifest = build_manifest(sessions_dir)
        save_manifest(manifest, sessions_dir)
        st.caption(
            f"Manifest updated: 🟢 {manifest.good_count} good, "
            f"🟡 {manifest.partial_count} partial, "
            f"🔴 {manifest.empty_count} empty"
        )
    except Exception:
        pass


def _render_results():
    """Render decode results."""
    result = st.session_state["proc_result"]
    stats = result["stats"]
    meta = result["capture_meta"]

    st.markdown(f"##### 📊 Decoded: `{result.get('file_name', '')}`")
    st.caption(f"Captured: {meta['captured_at']} · Label: {meta['label']}")

    # Stats row
    c1, c2, c3, c4, c5 = st.columns(5)
    total = stats["total_messages"]
    decoded = stats["decoded_ok"]
    errors = stats["decode_errors"]
    rate = (decoded / stats["binary_messages"] * 100) if stats["binary_messages"] > 0 else 0

    c1.metric("Total", total)
    c2.metric("Binary", stats["binary_messages"])
    c3.metric("JSON", stats["json_messages"])
    c4.metric("Decoded", decoded, delta=f"{rate:.1f}%")
    c5.metric("Errors", errors, delta=f"-{errors}" if errors > 0 else "0", delta_color="inverse")

    # Action breakdown
    actions = stats.get("actions_found", {})
    if actions:
        st.markdown("---")
        st.markdown("##### 🎯 Action Breakdown")
        sorted_actions = sorted(actions.items(), key=lambda x: -x[1])

        import pandas as pd
        df = pd.DataFrame(sorted_actions, columns=["Action", "Count"]).set_index("Action")
        st.bar_chart(df, color="#d29922")

    # Save button
    st.markdown("---")
    if st.button("💾 Save Processed Session", use_container_width=True, key="proc_save"):
        sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"
        session = ProcessedSession(
            capture_path=result.get("file_path", ""),
            captured_at=meta.get("captured_at", ""),
            label=meta.get("label", ""),
            stats=stats,
            events=result["events"],
            timeline=result["timeline"],
        )
        out = session.save(sessions_dir)
        st.success(f"Saved to `{out.name}`")

    # Event timeline preview
    st.markdown("---")
    st.markdown("##### ⏱️ Event Timeline (preview)")
    events = result["events"][:30]
    for ev in events:
        ts = _fmt_time(ev["timestamp"])
        d = ev["direction"]
        a = ev["action"]
        icon = "⬆️" if d == "SEND" else "⬇️" if d == "RECV" else "🔌"
        err = " ⚠️" if ev.get("decode_errors") else ""
        st.caption(f"`{ts}` {icon} **{a}** ({ev['raw_size']}B){err}")


def _fmt_time(epoch_ms: float) -> str:
    if epoch_ms <= 0:
        return "—"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000).strftime("%H:%M:%S.%f")[:-3]
    except Exception:
        return str(epoch_ms)
