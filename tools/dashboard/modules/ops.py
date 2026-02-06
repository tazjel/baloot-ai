import streamlit as st
import time
from .utils import get_redis_client, run_command

def render_ops_tab():
    st.header("Operations Control")
    st.write("⚠️ **Danger Zone**")
    
    col_o1, col_o2 = st.columns(2)
    
    with col_o1:
        if st.button("🧹 Flush Redis DB", type="secondary"):
            r = get_redis_client()
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
