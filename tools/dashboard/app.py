import streamlit as st
import redis
import time
from modules.launcher import render_launcher_tab
from modules.reports import render_reports_tab
from modules.logs import render_logs_tab
from modules.brain import render_brain_tab
from modules.visual_lab import render_visual_lab_tab
from modules.ops import render_ops_tab
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

# --- Config ---
st.set_page_config(
    page_title="Baloot AI Command Center",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar ---
st.sidebar.title("🃏 Baloot Ops")
st.sidebar.markdown("---")
st.sidebar.header("Status")

r = get_redis_client()
if r:
    st.sidebar.success("Redis: Connected ✅")
    try:
        info = r.info()
        st.sidebar.caption(f"Uptime: {info['uptime_in_seconds']}s")
        st.sidebar.caption(f"Memory: {info['used_memory_human']}")
    except:
        st.sidebar.warning("Redis: Connection unstable")
else:
    st.sidebar.error("Redis: Disconnected ❌")

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
    "🛠️ Ops"
]

tabs = st.tabs(tab_names)

# --- Render Modules ---

with tabs[0]:
    render_launcher_tab()

with tabs[1]:
    render_qayd_war_room()

with tabs[2]:
    render_brain_view()

with tabs[3]:
    render_inspector_tab()

with tabs[4]:
    render_trace_tab()

with tabs[5]:
    render_timeline_tab()

with tabs[6]:
    render_watchdog_module()

with tabs[7]:
    render_sherlock_view()

with tabs[8]:
    render_test_manager_tab()

with tabs[9]:
    render_reports_tab()

with tabs[10]:
    render_logs_tab()

with tabs[11]:
    render_visual_lab_tab()

with tabs[12]:
    render_ops_tab()
