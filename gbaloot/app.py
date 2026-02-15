"""
🎮 GBaloot — Baloot Game Data Analysis Tool

Standalone app for capturing, processing, organizing, reviewing,
and creating action items from Baloot game data.
"""
import streamlit as st
from pathlib import Path
import sys

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="GBaloot",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Ensure project root is importable ────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

# ── Custom Theme ─────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label { color: #c9d1d9 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        font-weight: 500;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #238636, #2ea043);
        border: none; color: white; font-weight: 600;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2ea043, #3fb950);
    }
    .stExpander { border: 1px solid #21262d; border-radius: 8px; }
    /* Metrics */
    [data-testid="stMetricValue"] { color: #58a6ff; font-weight: 700; }
    /* Code blocks */
    .stCodeBlock { border: 1px solid #30363d; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 12px 0 8px;">
        <h1 style="margin: 0; font-size: 2rem;">🎮 GBaloot</h1>
        <p style="margin: 4px 0 0; color: #8b949e; font-size: 0.85rem;">Game Data Analysis</p>
    </div>
    <hr style="border-color: #21262d; margin: 12px 0;">
    """, unsafe_allow_html=True)

    section = st.radio(
        "Section",
        ["📡 Capture", "⚙️ Process", "📁 Organize", "🔍 Review", "📊 Benchmark", "📈 Analytics", "✅ Do"],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color: #21262d; margin: 16px 0;'>", unsafe_allow_html=True)

    # Quick stats
    data_dir = ROOT / "data"
    captures_dir = data_dir / "captures"
    sessions_dir = data_dir / "sessions"
    tasks_dir = data_dir / "tasks"
    for d in [captures_dir, sessions_dir, tasks_dir]:
        d.mkdir(parents=True, exist_ok=True)

    n_captures = len(list(captures_dir.glob("*.json")))
    n_sessions = len(list(sessions_dir.glob("*_processed.json")))
    n_tasks = len(list(tasks_dir.glob("*.json")))

    # Load manifest for health breakdown
    health_line = ""
    try:
        from gbaloot.core.session_manifest import load_manifest
        manifest = load_manifest(sessions_dir)
        if manifest:
            health_line = (
                f"🟢 {manifest.good_count} "
                f"🟡 {manifest.partial_count} "
                f"🔴 {manifest.empty_count}"
            )
    except Exception:
        pass

    health_row = ""
    if health_line:
        health_row = f"""
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span>Health</span><span style="font-size: 0.8rem;">{health_line}</span>
        </div>"""

    st.markdown(f"""
    <div style="background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 12px; font-size: 0.85rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span>📡 Captures</span><span style="color: #58a6ff; font-weight: 600;">{n_captures}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span>📊 Sessions</span><span style="color: #f0883e; font-weight: 600;">{n_sessions}</span>
        </div>
        {health_row}
        <div style="display: flex; justify-content: space-between;">
            <span>✅ Tasks</span><span style="color: #7ee787; font-weight: 600;">{n_tasks}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top: 16px; text-align: center;">
        <p style="color: #484f58; font-size: 0.75rem; margin: 0;">GBaloot v1.0</p>
    </div>
    """, unsafe_allow_html=True)


# ── Main Area ────────────────────────────────────────────────────────
if section == "📡 Capture":
    from gbaloot.sections.capture import render
    render()
elif section == "⚙️ Process":
    from gbaloot.sections.process import render
    render()
elif section == "📁 Organize":
    from gbaloot.sections.organize import render
    render()
elif section == "🔍 Review":
    from gbaloot.sections.review import render
    render()
elif section == "📊 Benchmark":
    from gbaloot.sections.benchmark import render
    render()
elif section == "📈 Analytics":
    from gbaloot.sections.analytics import render
    render()
elif section == "✅ Do":
    from gbaloot.sections.do import render
    render()
