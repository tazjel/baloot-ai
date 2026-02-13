import streamlit as st
import pandas as pd
import json
import datetime
from game_engine.core.recorder import TimelineRecorder
from modules.utils import get_redis_client

def render_timeline_tab():
    st.header("⏳ Time Travel Inspector")
    
    r = get_redis_client()
    if not r:
        st.error("Redis disconnected")
        return

    # 1. Select Room
    # Scan for ANY game-related keys to find room IDs
    # Optimized: Scan `game:*:timeline` keys specifically
    timeline_keys = r.keys("game:*:timeline")
    room_ids = []
    for k in timeline_keys:
        # k is str if decode_responses=True
        k_str = k if isinstance(k, str) else k.decode()
        # Parse room_id
        parts = k_str.split(":")
        if len(parts) >= 2:
            room_ids.append(parts[1])
            
    if not room_ids:
        st.info("No recorded timelines found.")
        return

    selected_room = st.selectbox("Select Game Room", room_ids)
    
    if st.button("Refresh History"):
        st.rerun()

    # 2. Fetch History
    recorder = TimelineRecorder(r)
    # Fetch last 100 events
    history = recorder.get_history(selected_room, count=100)
    
    if not history:
        st.warning("Timeline exists but is empty.")
        return

    # 3. Display Dataframe
    # Prepare data for table
    table_data = []
    for entry in history:
        dt = datetime.datetime.fromtimestamp(entry['timestamp'])
        table_data.append({
            "Time": dt.strftime("%H:%M:%S"),
            "Event": entry['event'],
            "Details": entry['details'],
            "ID": entry['id'],
            "state_data": entry['state'] # Hidden from table, used for selection
        })
        
    df = pd.DataFrame(table_data)
    
    # Grid layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Event Log")
        # Use simple table or dataframe with selection if possible? 
        # Streamlit generic dataframe doesn't support row selection well without plugins.
        # We will use a selectbox for the "Focus Tick"
        
        # Create a label for the selectbox
        options = [f"{r['Time']} - {r['Event']} ({r['Details']})" for r in table_data]
        selected_idx_label = st.selectbox("Select Tick to Inspect", options, index=0)
        
        # Find the index
        idx = options.index(selected_idx_label)
        selected_entry = table_data[idx]
        
        st.dataframe(df[["Time", "Event", "Details"]], width='stretch')

    with col2:
        st.subheader("Game State Snapshot")
        state = selected_entry['state_data']
        
        # Expandable sections for readability
        with st.expander("Scores & Phase", expanded=True):
            st.json({
                "phase": state.get("phase"),
                "scores": state.get("matchScores"),
                "turn": state.get("currentTurnIndex"),
                "dealer": state.get("dealerIndex")
            })
            
        with st.expander("Table Cards"):
            st.json(state.get("tableCards"))
            
        with st.expander("Players (Hands)"):
            st.json(state.get("players"))
            
        with st.expander("Full JSON"):
            st.json(state)
            
