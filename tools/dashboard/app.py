import streamlit as st
import redis
import time
import json
from pathlib import Path
from modules.home import render_home_tab
from modules.terminal import render_terminal_tab
from modules.launcher import render_launcher_tab
from modules.reports import render_reports_tab
from modules.logs import render_logs_tab
from modules.visual_lab import render_visual_lab_tab
from modules.ops import render_ops_tab
from modules.qayd_war_room import render_qayd_war_room
from modules.inspector import render_inspector_tab
from modules.trace import render_trace_tab
from modules.timeline import render_timeline_tab
from modules.watchdog import render_watchdog_module
from modules.sherlock_view import render_sherlock_view
from modules.brain_view import render_brain_view
from modules.test_manager import render_test_manager_tab
from modules.utils import get_redis_client
from modules import cmd_queue
from modules.playwright_capture import render_capture_tab
from modules.protocol_decoder import render_protocol_decoder

# --- Config ---
st.set_page_config(
    page_title="Baloot AI Command Center",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Dark Theme CSS ---
st.markdown("""
<style>
/* ── Global dark polish ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
}
[data-testid="stSidebar"] * {
    color: #c9d1d9 !important;
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #58a6ff !important;
}

/* Tab bar styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: rgba(13, 17, 23, 0.5);
    border-radius: 8px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 0.85rem;
}
.stTabs [aria-selected="true"] {
    background: rgba(88, 166, 255, 0.15) !important;
    border-bottom-color: #58a6ff !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(22, 27, 34, 0.6);
    border: 1px solid rgba(48, 54, 61, 0.6);
    border-radius: 8px;
    padding: 12px;
}

/* Expander styling */
.streamlit-expanderHeader {
    border-radius: 6px;
    font-weight: 500;
}

/* Button polish */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
    border: none;
    border-radius: 6px;
    transition: all 0.2s ease;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(46, 160, 67, 0.4);
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #484f58; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("🃏 Baloot AI")
st.sidebar.caption("Command Center v2.0")
st.sidebar.markdown("---")

# Service Status
st.sidebar.markdown("##### ⚡ Services")
r = get_redis_client()
if r:
    try:
        info = r.info()
        mem = info.get('used_memory_human', '?')
        st.sidebar.markdown(f"🟢 Redis — `{mem}`")
    except:
        st.sidebar.markdown("🟡 Redis — unstable")
else:
    st.sidebar.markdown("🔴 Redis — offline")

# Last Test Results
st.sidebar.markdown("---")
st.sidebar.markdown("##### 🧪 Last Test Run")
try:
    hist_path = Path(__file__).parent / "test_history.json"
    if hist_path.exists():
        history = json.loads(hist_path.read_text(encoding="utf-8"))
        if history:
            last = history[-1]
            p, f, e = last.get("passed", 0), last.get("failed", 0), last.get("errors", 0)
            dur = last.get("duration", "?")
            ts = last.get("timestamp", "")[:16]
            if f == 0 and e == 0:
                st.sidebar.markdown(f"✅ **{p} passed** in {dur}s")
            else:
                st.sidebar.markdown(f"❌ **{f} failed** / {p} passed")
            st.sidebar.caption(f"📅 {ts}")
        else:
            st.sidebar.caption("No test history yet")
    else:
        st.sidebar.caption("No test history yet")
except Exception:
    st.sidebar.caption("Could not load test history")

st.sidebar.markdown("---")

# Command Queue Status
if r:
    q_size = cmd_queue.get_queue_size(r)
    if q_size > 0:
        st.sidebar.markdown(f"##### 📬 Command Queue: **{q_size}** pending")
    else:
        st.sidebar.markdown("##### 📬 Queue: idle")
st.sidebar.markdown("---")

# --- Activity Indicator for Qayd ---
# Optional: Highlight War Room if Qayd is active
qayd_active = False
if r:
    keys = r.keys("game:state:*")
    if keys:
        try:
            data = json_data = r.get(keys[0])
            import json
            jd = json.loads(json_data)
            qayd_state = jd.get("qaydState")
            if qayd_state and (qayd_state.get("active") or jd.get("phase") == "CHALLENGE"):
                qayd_active = True
        except:
            pass

war_room_title = "🕵️ Qayd War Room"
if qayd_active:
    war_room_title = "🕵️ Qayd War Room 🔴 (ACTIVE)"


# --- Tabs ---
tab_names = [
    "🏠 Home",
    "⚡ Terminal",
    "🚀 Launcher", 
    war_room_title,
    "🧠 Brain",
    "🕵️ Inspector",
    "⏳ Trace",
    "⏪ Timeline",
    "🚨 Watchdog", 
    "🔍 Sherlock",
    "🧪 Test Manager",
    "📈 Reports",
    "📜 Logs",
    "📸 Visual Lab", 
    "🎬 Game Capture",
    "🔓 Protocol Decoder",
    "🛠️ Ops"
]

tabs = st.tabs(tab_names)

# --- Render Modules ---

with tabs[0]:
    render_home_tab()

with tabs[1]:
    render_terminal_tab()

with tabs[2]:
    render_launcher_tab()

with tabs[3]:
    render_qayd_war_room()

with tabs[4]:
    render_brain_view()

with tabs[5]:
    render_inspector_tab()

with tabs[6]:
    render_trace_tab()

with tabs[7]:
    render_timeline_tab()

with tabs[8]:
    render_watchdog_module()

with tabs[9]:
    render_sherlock_view()

with tabs[10]:
    render_test_manager_tab()

with tabs[11]:
    render_reports_tab()

with tabs[12]:
    render_logs_tab()

with tabs[13]:
    render_visual_lab_tab()

with tabs[14]:
    render_capture_tab()

with tabs[15]:
    render_protocol_decoder()

with tabs[16]:
    render_ops_tab()
