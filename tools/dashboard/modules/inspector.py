import streamlit as st
import subprocess
import os

def run_linter_command(command, cwd=None):
    """Execution helper that returns stdout/stderr."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            cwd=cwd
        )
        return result
    except Exception as e:
        return f"Error: {e}"

def render_inspector_tab():
    st.header("🕵️ Code Inspector (Syntax & Integrity)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🐍 Python Backend")
        if st.button("Run Flake8 Analysis", key="btn_flake8"):
            with st.spinner("Analyzing Python Codebase..."):
                # We focus on logical errors (F) and syntax (E9) primarily to be fast and high-impact
                # Exclude .venv or standard excludes
                cmd = "flake8 server game_engine ai_worker tools --count --select=E9,F63,F7,F82 --show-source --statistics"
                res = run_linter_command(cmd)
                
                if res.returncode == 0:
                    st.success("✅ No Critical Syntax Errors Found!")
                else:
                    st.error("🚨 Issues Found")
                
                st.text("Output:")
                st.code(res.stdout + res.stderr, language="text")

        st.markdown("---")
        if st.button("Run Professional Audit (Pylint)", key="btn_pylint"):
            with st.spinner("Running Pylint (Google Style)..."):
                # Run pylint on critical paths only to save time
                # Using default rcfile for now, but enabling critical reports
                cmd = "pylint server game_engine --errors-only"
                res = run_linter_command(cmd)
                
                st.text("Pylint Output:")
                st.code(res.stdout + res.stderr, language="text")
                if res.returncode == 0:
                     st.success("✅ Clean Professional Audit!")

    with col2:
        st.subheader("⚛️ React Frontend")
        if st.button("Run Prettier Check", key="btn_prettier"):
            with st.spinner("Checking Frontend Indentation/Formatting..."):
                # Check .ts and .tsx files
                cmd = "npx prettier \"src/**/*.{ts,tsx}\" --check"
                res = run_linter_command(cmd, cwd="frontend")
                
                if res.returncode == 0:
                    st.success("✅ Formatting Looks Good!")
                else:
                    st.warning("⚠️ Formatting Issues Found (Prettier)")
                    
                st.text("Output:")
                st.code(res.stdout + res.stderr, language="text")
    
    st.markdown("---")
    st.subheader("📄 JSON Integrity Check")
    # Quick check for critical JSON files consistency if they exist
    json_files = ["config/game_rules.json", "config/ai_config.json"] # Example paths
    
    if st.button("Validate Config JSONs"):
        import json
        for fpath in json_files:
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r') as f:
                        json.load(f)
                    st.success(f"✅ {fpath} is Valid JSON")
                except json.JSONDecodeError as e:
                    st.error(f"❌ {fpath} is INVALID: {e}")
            else:
                st.info(f"ℹ️ {fpath} not found (Optional)")
