"""
📁 Organize Section — Tag, group, and annotate processed sessions.
"""
import streamlit as st
import json
from pathlib import Path
from ..core.models import ProcessedSession


def render():
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(126,231,135,0.1) 0%, rgba(22,27,34,0.6) 100%);
        border: 1px solid rgba(126,231,135,0.25); border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;">
        <h2 style="margin:0 0 4px 0; color: #7ee787;">📁 Organize</h2>
        <p style="margin:0; color: #8b949e; font-size: 0.9rem;">Tag, group, and annotate your processed game sessions</p>
    </div>""", unsafe_allow_html=True)

    sessions_dir = Path(__file__).resolve().parents[1] / "data" / "sessions"
    sessions = _load_sessions(sessions_dir)

    if not sessions:
        st.info("No processed sessions found. Run **Process** on your captures first.")
        return

    fcol1, fcol2 = st.columns(2)
    with fcol1:
        search = st.text_input("🔍 Search", placeholder="label, tag, notes...", key="org_search")
    with fcol2:
        all_groups = sorted(set(s.group for s in sessions if s.group))
        group_filter = st.selectbox("Group", ["All"] + all_groups, key="org_group")

    filtered = sessions
    if search:
        sl = search.lower()
        filtered = [s for s in filtered if sl in s.label.lower() or sl in s.notes.lower()
                     or any(sl in t.lower() for t in s.tags)]
    if group_filter != "All":
        filtered = [s for s in filtered if s.group == group_filter]

    st.caption(f"Showing {len(filtered)} of {len(sessions)} sessions")

    for i, session in enumerate(filtered):
        _render_card(session, i, sessions_dir)


def _load_sessions(d: Path) -> list[ProcessedSession]:
    if not d.exists():
        return []
    sessions = []
    for f in sorted(d.glob("*_processed.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            sessions.append(ProcessedSession.load(f))
        except Exception:
            pass
    return sessions


def _render_card(session: ProcessedSession, idx: int, sessions_dir: Path):
    stats = session.stats or {}
    decoded = stats.get("decoded_ok", 0)
    total = stats.get("total_messages", 0)
    label = session.label or Path(session.capture_path).stem

    with st.expander(f"📄 **{label}** — {decoded}/{total} decoded", expanded=False):
        st.caption(f"📅 {session.captured_at}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Decoded", decoded)
        col2.metric("Binary", stats.get("binary_messages", 0))
        col3.metric("JSON", stats.get("json_messages", 0))

        actions = stats.get("actions_found", {})
        if actions:
            top = sorted(actions.items(), key=lambda x: -x[1])[:5]
            st.caption("Top actions: " + ", ".join(f"{a} ({c})" for a, c in top))

        st.markdown("---")
        new_tags = st.text_input("Tags (comma-separated)", value=", ".join(session.tags), key=f"org_tags_{idx}")
        new_group = st.text_input("Group", value=session.group, key=f"org_grp_{idx}")
        new_notes = st.text_area("Notes", value=session.notes, key=f"org_notes_{idx}", height=80)

        if st.button("💾 Save", key=f"org_save_{idx}"):
            session.tags = [t.strip() for t in new_tags.split(",") if t.strip()]
            session.group = new_group.strip()
            session.notes = new_notes.strip()
            out = sessions_dir / f"{Path(session.capture_path).stem}_processed.json"
            with open(out, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False, default=str)
            st.success("Saved!")
