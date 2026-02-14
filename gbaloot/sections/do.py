"""
✅ Do Section — Task board for things to do / verify / replicate.

Create tasks from reviewed sessions, manage backlog, mark done.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from ..core.models import TaskStore, GameTask

PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}

def render():
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(126,231,135,0.1) 0%, rgba(22,27,34,0.6) 100%);
        border: 1px solid rgba(126,231,135,0.25); border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;">
        <h2 style="margin:0 0 4px 0; color: #7ee787;">✅ Do</h2>
        <p style="margin:0; color: #8b949e; font-size: 0.9rem;">Create, track, and complete analysis tasks</p>
    </div>""", unsafe_allow_html=True)

    data_dir = Path(__file__).resolve().parents[1] / "data" / "tasks"
    data_dir.mkdir(parents=True, exist_ok=True)
    store = TaskStore(data_dir)

    tab_board, tab_new = st.tabs(["📋 Task Board", "➕ New Task"])

    with tab_board:
        _render_board(store)

    with tab_new:
        _render_create(store)


def _render_board(store: TaskStore):
    tasks = store.load_all()
    if not tasks:
        st.info("No tasks yet. Create one in the **New Task** tab.")
        return

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        status_f = st.selectbox("Status", ["All", "todo", "in_progress", "done"], key="do_status")
    with fc2:
        prio_f = st.selectbox("Priority", ["All", "high", "medium", "low"], key="do_prio")
    with fc3:
        search = st.text_input("🔍 Search", key="do_search")

    filtered = tasks
    if status_f != "All":
        filtered = [t for t in filtered if t.status == status_f]
    if prio_f != "All":
        filtered = [t for t in filtered if t.priority == prio_f]
    if search:
        sl = search.lower()
        filtered = [t for t in filtered if sl in t.title.lower() or sl in t.description.lower()]

    st.caption(f"Showing {len(filtered)} of {len(tasks)} tasks")

    for task in filtered:
        p_emoji = PRIORITY_EMOJI.get(task.priority, "⚪")
        status_color = {"todo": "#8b949e", "in_progress": "#d29922", "done": "#3fb950"}.get(task.status, "#8b949e")
        with st.expander(f"{p_emoji} **{task.title}** — `{task.status}`"):
            st.write(task.description)
            if task.source_session:
                st.caption(f"📎 Linked session: `{task.source_session}`")

            ac1, ac2, ac3, ac4 = st.columns(4)
            with ac1:
                if task.status != "in_progress" and st.button("▶️ Start", key=f"start_{task.id}"):
                    store.update(task.id, status="in_progress")
                    st.rerun()
            with ac2:
                if task.status != "done" and st.button("✅ Done", key=f"done_{task.id}"):
                    store.update(task.id, status="done")
                    st.rerun()
            with ac3:
                if task.status != "todo" and st.button("⏪ Reset", key=f"reset_{task.id}"):
                    store.update(task.id, status="todo")
                    st.rerun()
            with ac4:
                if st.button("🗑️ Delete", key=f"del_{task.id}"):
                    store.delete(task.id)
                    st.rerun()


def _render_create(store: TaskStore):
    with st.form("new_task_form"):
        title = st.text_input("Task Title", placeholder="e.g. Check bot bidding strategy")
        desc = st.text_area("Description", placeholder="What needs to be done?")
        c1, c2 = st.columns(2)
        with c1:
            priority = st.selectbox("Priority", ["medium", "high", "low"])
        with c2:
            session_ref = st.text_input("Link Session (optional)", placeholder="session filename")

        if st.form_submit_button("Create Task", type="primary"):
            if not title:
                st.error("Title is required")
            else:
                task = GameTask(
                    title=title,
                    description=desc,
                    priority=priority,
                    source_session=session_ref or "",
                )
                store.add(task)
                st.success(f"Created task: **{title}**")
                st.rerun()
