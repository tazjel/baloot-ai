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

    st.markdown("---")
    st.subheader("Process Health (Heartbeat)")
    
    r = get_redis_client()
    if r:
        from server.process_manager import Reaper
        
        # Manually implement simple scan here to avoid import issues if path not set
        keys = r.keys("heartbeat:*:*")
        if not keys:
            st.warning("No active heartbeats found.")
        else:
            data = []
            for k in keys:
                decoded = k if isinstance(k, str) else k.decode()
                # Format: heartbeat:service_name:pid
                parts = decoded.split(":")
                service = parts[1] if len(parts) > 1 else "unknown"
                pid = parts[2] if len(parts) > 2 else "?"
                
                hb_data = r.hgetall(k)
                
                def get_val(d, key):
                     if key in d: return d[key]
                     if key.encode() in d: return d[key.encode()]
                     return None
                
                last_seen_raw = get_val(hb_data, 'last_seen') or 0
                last_seen = float(last_seen_raw)
                
                status_raw = get_val(hb_data, 'status') or 'unknown'
                status = status_raw if isinstance(status_raw, str) else status_raw.decode()
                
                # Check latency
                ago = time.time() - last_seen
                status_icon = "🟢" if ago < 10 else "🔴"
                
                data.append({
                    "Service": service,
                    "PID": pid,
                    "Status": f"{status_icon} {status}",
                    "Last Seen": f"{ago:.1f}s ago"
                })
            
            st.table(data)
