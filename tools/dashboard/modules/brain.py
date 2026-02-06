import streamlit as st
import json
from .utils import get_redis_client

def render_brain_tab():
    st.header("Live Game State (Redis)")
    
    r = get_redis_client()
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
                    
                    # Top Level Metrics
                    st.subheader("📊 Vital Signs")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Phase", data.get("phase", "N/A"))
                    m2.metric("Turn", data.get("current_turn", "N/A"))
                    scores = data.get("scores", {})
                    m3.metric("Team US", scores.get("us", 0))
                    m4.metric("Team THEM", scores.get("them", 0))

                    # Deep Dive
                    st.divider()
                    st.subheader("🧠 Deep State Inspection")
                    
                    tab_json, tab_players, tab_tricks = st.tabs(["Raw JSON", "Players", "Tricks"])
                    
                    with tab_json:
                        st.json(data, expanded=False)
                        
                    with tab_players:
                        players = data.get("players", [])
                        for p in players:
                            st.text(f"Player {p.get('position')}: {p.get('hand_count', 0)} cards")
                            # Can expand to show hand if needed/available? Usually masked.
                            
                    with tab_tricks:
                        tricks = data.get("round_history", [])
                        st.write(f"Tricks played: {len(tricks)}")
                        if tricks:
                            st.json(tricks, expanded=False)

                except json.JSONDecodeError:
                    st.error("Failed to decode Game State JSON.")
                    st.code(data_str)
    else:
        st.error("Redis connection required.")
