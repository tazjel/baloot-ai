import streamlit as st
import pandas as pd
import re
import os
import json
from datetime import datetime

# Regex to parse the standard log format:
# 2026-02-04 23:11:09,983 - GameServer - INFO - [EVENT] {...}
LOG_PATTERN = re.compile(
    r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (?P<logger>\S+) - (?P<level>\S+) - (?P<message>.*)'
)

def parse_log_file(filepath):
    data = []
    if not os.path.exists(filepath):
        return pd.DataFrame()

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        # Read lines in reverse or just all lines? Reverse is better for "Latest"
        # optimizing: read last 2000 lines
        lines = f.readlines()[-3000:] 
        
    for line in lines:
        match = LOG_PATTERN.match(line)
        if match:
            entry = match.groupdict()
            msg = entry['message']
            
            # Extract [EVENT] JSON if present
            event_data = {}
            is_event = False
            if "[EVENT]" in msg:
                try:
                    json_part = msg.split("[EVENT]", 1)[1].strip()
                    event_data = json.loads(json_part)
                    is_event = True
                    # Override timestamp with event timestamp if improved accuracy needed
                except:
                    pass
            
            # Enrich entry
            entry['is_event'] = is_event
            entry['event_type'] = event_data.get('event', '') if is_event else ''
            entry['game_id'] = event_data.get('game_id', '') if is_event else ''
            
            # Tag Errors specifically
            if entry['level'] in ['ERROR', 'CRITICAL']:
                entry['is_error'] = True
            else:
                entry['is_error'] = False
                
            data.append(entry)
            
    return pd.DataFrame(data)

def render_trace_tab():
    st.header("⏳ Timeline Trace (The Truth Machine)")
    
    log_path = "logs/server_stdout.log" # Default target
    if not os.path.exists(log_path):
        st.warning(f"Log file not found at {log_path}. Trying server_manual.log...")
        log_path = "logs/server_manual.log"
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

    df = parse_log_file(log_path)
    
    if df.empty:
        st.info("No logs found or empty file.")
        return

    # --- Filters ---
    st.sidebar.markdown("### Trace Filters")
    
    # 1. Game ID Filter
    game_ids = df[df['game_id'] != '']['game_id'].unique().tolist()
    if game_ids:
        selected_game = st.sidebar.selectbox("Filter by Game ID", ["All"] + game_ids)
        if selected_game != "All":
            df = df[df['game_id'] == selected_game]
            
    # 2. Event Only Toggle
    show_only_events = st.sidebar.checkbox("Show [EVENT]s Only", value=True)
    if show_only_events:
        df = df[ (df['is_event'] == True) | (df['is_error'] == True) ]

    # --- Visualization ---
    
    # Timeline View
    st.subheader("Event Sequence")
    
    # Display as a clean dataframe tailored for timeline
    display_cols = ['timestamp', 'level', 'event_type', 'message']
    
    def highlight_row(row):
        if row.get('is_error'):
            return ['background-color: #ffcccc'] * len(row)
        if 'TRICK_WIN' in str(row.get('event_type')):
             return ['background-color: #e6ffcc'] * len(row)
        if 'PHASE_CHANGE' in str(row.get('event_type')):
             return ['background-color: #e6f7ff'] * len(row)
        return [''] * len(row)

    st.dataframe(
        df[display_cols],
        width='stretch',
        height=600
    )
    
    st.subheader("Raw Last 50 Lines")
    st.text_area("Tail", value="\n".join(df.tail(50)['message'].tolist()), height=200)

    # --- Agent Report Generation ---
    st.markdown("---")
    st.subheader("🤖 Agent Handoff")
    st.info("Found a bug? Generate a report to paste directly to Antigravity.")
    
    if st.button("📋 Generate Report for Agent"):
        report = generate_agent_report(df)
        st.code(report, language="markdown")

def generate_agent_report(df):
    """Generates a markdown report from the current filtered dataframe."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get relevant context
    game_ids = df[df['game_id'] != '']['game_id'].unique().tolist()
    primary_game = game_ids[0] if game_ids else "Unknown"
    
    # Get errors
    errors = df[df['is_error'] == True]
    error_count = len(errors)
    last_error = errors.iloc[-1]['message'] if not errors.empty else "No explicit errors found in filter."
    
    # Get last few events for context
    events = df[df['is_event'] == True].tail(10)
    event_log = []
    for _, row in events.iterrows():
        event_log.append(f"- `{row['timestamp']}` **{row['event_type']}**: {row['message']}")
        
    event_str = "\n".join(event_log)
    
    report = f"""
# 🐛 Bug Report from Dashboard
**Time**: {timestamp} | **GameID**: `{primary_game}` | **Errors Found**: {error_count}

## 🚨 Critical Error Context
> {last_error}

## ⏳ Recent Event Trace
{event_str}

## 📝 User Note
(Describe what you saw on screen versus what happened here...)
"""
    return report
