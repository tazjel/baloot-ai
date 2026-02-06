import streamlit as st
import subprocess
from .utils import run_command

def render_launcher_tab():
    st.header("Test Orchestration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Fast Verification")
        if st.button("RUN: Turbo Tests (/test-fast)", type="primary"):
            with st.status("Running Turbo Tests...", expanded=True) as status:
                st.write("Initializing...")
                cmd = "powershell -ExecutionPolicy Bypass -File ./scripts/test_turbo.ps1"
                result = run_command(cmd)
                
                if result:
                    st.code(result.stdout)
                    if result.returncode == 0:
                        status.update(label="Tests Passed! ✅", state="complete", expanded=False)
                        st.success("Verification Successful")
                    else:
                        status.update(label="Tests Failed! ❌", state="error", expanded=True)
                        st.error("Verification Failed")
                        st.code(result.stderr)
                else:
                    st.error("Execution failed.")

    with col2:
        st.subheader("Deep Verification")
        if st.button("RUN: Full Browser Test (Headed)", help="Runs /nw equivalent"):
            st.info("Launching headed test in separate window...")
            subprocess.Popen("pytest tests/browser/test_ui_qayd.py --headed --slowmo 1000", shell=True)
            st.success("Test launched in background.")
