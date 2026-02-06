import streamlit as st
import streamlit.components.v1 as components
import redis
import json
import subprocess
import os
import glob
import pandas as pd
from datetime import datetime
import time

# --- Config ---
st.set_page_config(
    page_title="Baloot AI Command Center",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Helpers ---
def get_redis_client():
    try:
        # Add timeout to prevent UI freeze
        r = redis.Redis(
            host='127.0.0.1',  # Force IPv4
            port=6379, 
            db=0, 
            decode_responses=True, 
            socket_timeout=5.0  # Increased to 5s for Windows Docker latency
        )
        r.ping()
        return r
    except (redis.ConnectionError, redis.TimeoutError, Exception):
        return None

def run_command(command, cwd=None):
    """Run a shell command and return result."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            cwd=cwd
        )
        return result
    except Exception as e:
        return None

def read_last_lines(filepath, n=50):
    if not os.path.exists(filepath):
        return [f"File not found: {filepath}"]
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-n:]
    except Exception as e:
        return [f"Error reading file: {e}"]

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

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🚀 Launcher", 
    "📈 Reports",
    "📜 Logs",
    "🧠 Brain", 
    "📸 Visual Lab", 
    "🛠️ Ops"
])

# --- Tab 1: Launcher ---
with tab1:
    st.header("Test Orchestration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Fast Verification")
        if st.button("RUN: Turbo Tests (/test-fast)", type="primary"):
            with st.status("Running Turbo Tests...", expanded=True) as status:
                st.write("Initializing...")
                cmd = "powershell -ExecutionPolicy Bypass -File ./scripts/test_turbo.ps1"
                result = run_command(cmd)
                
                if result:
                    st.code(result.stdout)
                    if result.returncode == 0:
                        status.update(label="Tests Passed! ✅", state="complete", expanded=False)
                        st.success("Verification Successful")
                    else:
                        status.update(label="Tests Failed! ❌", state="error", expanded=True)
                        st.error("Verification Failed")
                        st.code(result.stderr)
                else:
                    st.error("Execution failed.")

    with col2:
        st.subheader("Deep Verification")
        if st.button("RUN: Full Browser Test (Headed)", help="Runs /nw equivalent"):
            st.info("Launching headed test in separate window...")
            subprocess.Popen("pytest tests/browser/test_ui_qayd.py --headed --slowmo 1000", shell=True)
            st.success("Test launched in background.")

# --- Tab 2: Reports ---
with tab2:
    st.header("Test Reports")
    report_path = "diagnostics/report.html"
    
    col_r1, col_r2 = st.columns([1, 4])
    with col_r1:
        if st.button("🔄 Refresh Report"):
            st.rerun()
            
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Determine height based on content approx or fixed
        components.html(html_content, height=800, scrolling=True)
    else:
        st.info("No report found. Run tests to generate one.")

# --- Tab 3: Logs ---
with tab3:
    st.header("System Logs")
    
    log_files = {
        "Backend (Headless)": "logs/server_headless.out.log",
        "Frontend (Headless)": "logs/frontend_headless.out.log",
        "Backend (Error)": "logs/server_headless.err.log",
        "Turbo Test Log": "logs/last_test_execution.log" # Placeholder if we redirect there
    }
    
    selected_log = st.selectbox("Select Log File", list(log_files.keys()))
    path = log_files[selected_log]
    
    if st.toggle("Auto-Refresh", value=False):
        time.sleep(2)
        st.rerun()

    lines = read_last_lines(path, n=100)
    log_text = "".join(lines)
    
    st.text_area("Log Output", log_text, height=400)


# --- Tab 4: Brain ---
with tab4:
    st.header("Live Game State (Redis)")
    
    if r:
        keys = r.keys("game:state:*")
        
        if not keys:
            st.warning("No active game sessions found in Redis.")
        else:
            selected_key = st.selectbox("Select Game Session", keys)
            
            if st.button("Refresh State"):
                st.rerun()

            if selected_key:
                data_str = r.get(selected_key)
                try:
                    data = json.loads(data_str)
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Phase", data.get("phase", "N/A"))
                    m2.metric("Turn", data.get("current_turn", "N/A"))
                    scores = data.get("scores", {})
                    m3.metric("Team US", scores.get("us", 0))
                    m4.metric("Team THEM", scores.get("them", 0))

                    st.markdown("### 🔍 JSON Inspector")
                    st.json(data)
                except json.JSONDecodeError:
                    st.error("Failed to decode Game State JSON.")
                    st.code(data_str)
    else:
        st.error("Redis connection required.")

# --- Tab 5: Visual Lab ---
with tab5:
    st.header("Visual Regression Gallery")
    SNAPSHOT_DIR = "tests/browser/snapshots"
    if os.path.exists(SNAPSHOT_DIR):
        snapshots = glob.glob(f"{SNAPSHOT_DIR}/**/*.png", recursive=True)
        if not snapshots:
            st.info("No snapshots found.")
        else:
            files_map = {os.path.basename(p): p for p in snapshots}
            selected_file = st.selectbox("Select Snapshot", list(files_map.keys()))
            if selected_file:
                path = files_map[selected_file]
                st.image(path, caption=path, use_container_width=True)
                file_stats = os.stat(path)
                st.caption(f"Modified: {datetime.fromtimestamp(file_stats.st_mtime)}")
    else:
        st.error(f"Snapshot directory not found: {SNAPSHOT_DIR}")

# --- Tab 6: Ops ---
with tab6:
    st.header("Operations Control")
    
    st.write("⚠️ **Danger Zone**")
    
    col_o1, col_o2 = st.columns(2)
    
    with col_o1:
        if st.button("🧹 Flush Redis DB", type="secondary"):
            if r:
                r.flushall()
                st.success("Redis DB Flushed.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Redis not connected.")
                
    with col_o2:
        if st.button("💀 Kill Python Processes", type="secondary"):
            # Windows only
            run_command("taskkill /F /IM python.exe")
            st.warning("Killed python processes. You may need to restart the dashboard.")

