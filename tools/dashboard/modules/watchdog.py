import time
import streamlit as st
from modules.utils import get_redis_client

def render_watchdog_module(room_id=None):
    st.markdown("### 🚨 Anomaly Watchdog")
    
    r = get_redis_client()
    if not r:
        st.error("Redis connection failed.")
        return

    if not room_id:
        # Auto-select or prompt
        keys = r.keys("game:*:state")
        room_ids = [k.split(":")[1] for k in (keys if keys else [])]
        
        if not room_ids:
             st.info("No active rooms found.")
             return
             
        room_id = st.selectbox("Select Room to Monitor", room_ids, key="watchdog_room_select")
    
    if not room_id:
        return

    # 1. Fetch Key State
    state_key = f"game:{room_id}:state"
    # Handle decode explicitly if needed, but r.json() usually handles it
    state = r.json().get(state_key)
    
    if not state:
        st.warning(f"Room {room_id} not found or empty.")
        return

    anomalies = []
    
    # Check 1: Stall Detection (Last Update)
    last_update_ts = float(state.get('last_update', 0) or 0)
    now = time.time()
    ago = now - last_update_ts
    
    if ago > 45:
        anomalies.append({
            "Level": "CRITICAL",
            "Type": "STALL",
            "Message": f"Game state hasn't changed for {ago:.1f}s.",
            "Recommendation": "Check Heartbeat. If dead, Restart Server."
        })
    elif ago > 15:
        anomalies.append({
            "Level": "WARNING",
            "Type": "LAG",
            "Message": f"Game state is slow ({ago:.1f}s since update).",
            "Recommendation": "Monitor latency."
        })

    # Check 2: Phase Liveness
    phase = state.get('phase')
    turn_player = state.get('currentTurn')
    
    if phase == 'BIDDING' and ago > 30:
        anomalies.append({
            "Level": "CRITICAL",
            "Type": "LOCK",
            "Message": f"Stuck in BIDDING for {ago:.1f}s. Waiting for {turn_player}.",
            "Recommendation": "Check if Bot is disconnected or stuck in thought loop."
        })
        
    if phase == 'PLAYING' and ago > 30:
         anomalies.append({
            "Level": "WARNING",
            "Type": "SLOW_PLAY",
            "Message": f"Player {turn_player} taking long ({ago:.1f}s).",
            "Recommendation": "Timer should force auto-play soon."
        })

    # Check 3: Qayd Freeze
    qayd = state.get('qaydState', {})
    if qayd.get('active'):
        # If Qayd matches active but phase is not CHALLENGE (weird state)
        if phase != 'CHALLENGE' and phase != 'FINISHED':
             anomalies.append({
                "Level": "CRITICAL",
                "Type": "STATE_DESYNC",
                "Message": "Qayd is Active but Phase is not CHALLENGE.",
                "Recommendation": "Force Re-sync or Key Delete."
             })
        
        # If Qayd active for too long
        # We don't have start timestamp in QaydState yet, but can infer from staleness?
        pass

    # Render
    if not anomalies:
        st.success("✅ No Anomalies Detected. Guard Dog is sleeping.")
    else:
        st.error(f"⚠️ {len(anomalies)} Anomalies Detected!")
        for a in anomalies:
            icon = "🛑" if a['Level'] == "CRITICAL" else "⚠️"
            st.markdown(f"""
            <div style="padding: 10px; border: 1px solid #ff4b4b; border-radius: 5px; margin-bottom: 5px;">
                <b>{icon} {a['Type']}</b>: {a['Message']}<br>
                <i>Fix: {a['Recommendation']}</i>
            </div>
            """, unsafe_allow_html=True)
            
    return anomalies
