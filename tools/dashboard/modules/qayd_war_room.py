import streamlit as st
import json
from .utils import get_redis_client

def render_qayd_war_room():
    st.header("🕵️ Qayd Forensic War Room")
    st.info("Specialized interface for investigating Qayd (Rule Violations) and Dispute states.")
    
    r = get_redis_client()
    if not r:
        st.error("Redis connection required for War Room.")
        return

    keys = r.keys("game:state:*")
    if not keys:
        st.warning("No active game sessions.")
        return
        
    # Assuming single session mainly for local dev
    selected_key = keys[0] # or selectbox if needed
    data_str = r.get(selected_key)
    
    try:
        data = json.loads(data_str)
    except:
        st.error("Invalid JSON state.")
        return

    phase = data.get("phase")
    qayd_state = data.get("qaydState")
    
    # War Room Status Board
    col1, col2, col3 = st.columns(3)
    col1.metric("Game Phase", phase)
    col2.metric("Qayd Active", str(qayd_state.get("active") if qayd_state else False))
    col3.metric("Qayd Status", qayd_state.get("status") if qayd_state else "None")
    
    st.divider()
    
    if not qayd_state:
        st.markdown("### 💤 No Active Investigation")
        st.caption("Trigger a Qayd in the game to see forensic details here.")
        return

    # Forensic Details
    st.subheader("🔍 Case File")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Accuser:** " + str(qayd_state.get("accuser", "N/A")))
        st.markdown("**Defendant:** " + str(qayd_state.get("defendant", "N/A")))
    with c2:
        st.markdown("**Step:** " + str(qayd_state.get("step", "N/A")))
        
    st.markdown("#### Evidence")
    
    # Crime Card
    crime_card = qayd_state.get("crimeCard")
    proof_card = qayd_state.get("proofCard")
    
    ec1, ec2 = st.columns(2)
    with ec1:
        st.caption("Crime Card (The Violation)")
        if crime_card:
            st.json(crime_card)
        else:
            st.write("Not Selected")
            
    with ec2:
        st.caption("Proof Card (The Evidence)")
        if proof_card:
            st.json(proof_card)
        else:
            st.write("Not Selected")

    # Verdict
    verdict = qayd_state.get("verdictData")
    if verdict:
        st.success("⚖️ Verdict Rendered")
        st.json(verdict)
    else:
        st.warning("⚖️ No Verdict Yet")

    st.divider()
    
    # Emergency Controls
    st.subheader("🚨 Emergency Overrides")
    st.caption("Force state transitions if the game is stuck.")
    
    if st.button("FORCE: Cancel Qayd (Reset)"):
        # We can't easily call backend methods directly from here without RPC, 
        # but we can maybe set a flag or just warn user to use game UI.
        # Ideally, we would publish to a Redis channel that the backend listens to.
        # For now, just a placeholder or aggressive Redis edit (risky).
        st.warning("Force Cancel not fully implemented via Dashboard yet. Use Game UI.")
        
    if st.toggle("Show Raw Qayd State"):
        st.json(qayd_state)
