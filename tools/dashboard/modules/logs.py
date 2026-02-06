import streamlit as st
import time
from .utils import read_last_lines

def render_logs_tab():
    st.header("System Logs")
    
    log_files = {
        "Backend (Headless)": "logs/server_headless.out.log",
        "Frontend (Headless)": "logs/frontend_headless.out.log",
        "Backend (Error)": "logs/server_headless.err.log",
        "Turbo Test Log": "logs/last_test_execution.log"
    }
    
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_log = st.selectbox("Select Log File", list(log_files.keys()))
    with col2:
        auto_refresh = st.toggle("Auto-Refresh", value=False)
        
    path = log_files[selected_log]
    
    # Filter controls
    filter_text = st.text_input("Filter Logs (Regex or Text)", placeholder="e.g. error|exception|critical")
    
    if auto_refresh:
        time.sleep(2)
        st.rerun()

    lines = read_last_lines(path, n=200) # Increased to 200
    
    if filter_text:
        filtered_lines = [line for line in lines if filter_text.lower() in line.lower()]
        st.caption(f"Showing {len(filtered_lines)} matches out of {len(lines)} lines")
        log_text = "".join(filtered_lines)
    else:
        log_text = "".join(lines)
    
    # Simple color coding for errors if using markdown? 
    # For large logs, text_area is safer. 
    # But let's try to highlight if it's an error log.
    
    height = 600
    st.text_area("Log Output", log_text, height=height)
