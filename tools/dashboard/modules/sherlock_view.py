import streamlit as st
import pandas as pd
from modules.utils import get_redis_client

def render_sherlock_view(room_id=None):
    st.markdown("### 🕵️‍♂️ Sherlock Live Feed")
    
    r = get_redis_client()
    if not r:
        st.error("Redis disconnected.")
        return

    if not room_id:
        keys = r.keys("game:*:state")
        room_ids = [k.split(":")[1] for k in (keys if keys else [])]
        if room_ids:
            room_id = st.selectbox("Select Room", room_ids, key="sherlock_room_select")
            
    if not room_id:
        st.info("Select a room.")
        return

    r = get_redis_client()
    state_key = f"game:{room_id}:state"
    state = r.json().get(state_key)
    
    if not state:
        st.warning("No state")
        return

    # 1. Active Investigation Monitor
    qayd = state.get('qaydState', {})
    if qayd.get('active'):
        st.markdown(f"""
        <div style="background-color: #2b2102; border: 1px solid #ffd700; padding: 10px; border-radius: 5px;">
            <h4>🔍 Investigation ACTIVE</h4>
            <p><b>Reporter:</b> {qayd.get('reporter')}</p>
            <p><b>Crime ID:</b> {qayd.get('crimeId')}</p>
            <p><b>Status:</b> {qayd.get('status')}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("Middleware Status: *Monitoring...*")

    st.markdown("#### Detected Crimes (Memory)")
    # This requires us to peek into the Agent's internal memory?
    # Or we can scan the logs for [SHERLOCK] tags?
    # Scanning logs is expensive.
    # Alternatives: 
    # 1. Agents publish to a Redis list "game:{id}:crimes"
    # 2. We use the "Timeline" to see if any QAYD_TRIGGER actions happened.
    
    # For V4, let's scan the recent logs efficiently.
    # (Assuming logs are available via modules/logs)
    
    # Placeholder for Log Scan
    st.info("Log scanning coming in V4.1. For now, check the Console Logs.")
