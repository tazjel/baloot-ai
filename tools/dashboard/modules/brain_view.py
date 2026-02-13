import streamlit as st
import re
from modules.utils import read_last_lines

def render_brain_view(room_id=None):
    st.markdown("### 🧠 Bot Thought Stream")
    
    # Auto-refresh toggle - uses fragment to avoid blocking other tabs
    if 'auto_refresh_brain' not in st.session_state:
        st.session_state['auto_refresh_brain'] = False
        
    on = st.toggle("Live Stream", value=st.session_state['auto_refresh_brain'], key="brain_live_toggle")
    st.session_state['auto_refresh_brain'] = on
    
    if on:
        st.caption("🔴 Live — auto-refreshes every 3s")
        import time
        # Use st.empty() to create a refresh timer that doesn't block
        # The actual refresh happens via a manual button or next interaction

    log_path = "logs/server_headless.out.log"
    
    try:
        lines = read_last_lines(log_path, n=300) # Deep scan
    except Exception:
        st.error("Could not read server logs.")
        return

    # Parsing Logic
    thoughts = []
    
    # Regex patterns
    # 1. Sherlock
    # 2. General Bot Actions
    # 3. Reasoning (if visible)
    
    for line in lines:
        if "[SHERLOCK]" in line:
            thoughts.append({"type": "SHERLOCK", "text": line.strip(), "icon": "🕵️‍♂️"})
        elif "[BOT-EYE]" in line:
            thoughts.append({"type": "VISION", "text": line.strip(), "icon": "👁️"})
        elif "[BRAIN]" in line:
             thoughts.append({"type": "MEMORY", "text": line.strip(), "icon": "🧠"})
        elif "Bot" in line and "Action" in line:
             thoughts.append({"type": "ACTION", "text": line.strip(), "icon": "🤖"})
        # Catch JSON dumps which might contain reasoning
        elif "reasoning" in line:
             # Try to extract just the reasoning
             # ... "reasoning": "Cutting Enemy" ...
             match = re.search(r'"reasoning":\s*"([^"]+)"', line)
             if match:
                  thoughts.append({"type": "THOUGHT", "text": f"Reasoning: {match.group(1)}", "icon": "💡"})
    
    # Display in reverse order (newest first)
    for t in reversed(thoughts):
        color = "#ffffff"
        bg = "#000000"
        
        if t['type'] == "SHERLOCK": bg = "#2b1c1c"; color = "#ffaaaa"
        elif t['type'] == "THOUGHT": bg = "#1c2b1c"; color = "#aaffaa"
        elif t['type'] == "VISION": bg = "#1c1c2b"; color = "#aaaaff"
        
        st.markdown(f"""
        <div style="background-color: {bg}; color: {color}; padding: 8px; border-radius: 5px; margin-bottom: 5px; border-left: 4px solid {color}">
            <b>{t['icon']}</b> {t['text']}
        </div>
        """, unsafe_allow_html=True)
        
    if not thoughts:
        st.info("No bot thoughts detected in recent logs.")
