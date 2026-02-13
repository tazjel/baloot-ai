import streamlit as st
import os
import glob
from datetime import datetime

def render_visual_lab_tab():
    st.header("Visual Regression Gallery")
    SNAPSHOT_DIR = "tests/browser/snapshots"
    
    if os.path.exists(SNAPSHOT_DIR):
        snapshots = glob.glob(f"{SNAPSHOT_DIR}/**/*.png", recursive=True)
        if not snapshots:
            st.info("No snapshots found.")
        else:
            files_map = {os.path.basename(p): p for p in snapshots}
            selected_file = st.selectbox("Select Snapshot", list(files_map.keys()))
            if selected_file:
                path = files_map[selected_file]
                st.image(path, caption=path, width='stretch')
                file_stats = os.stat(path)
                st.caption(f"Modified: {datetime.fromtimestamp(file_stats.st_mtime)}")
    else:
        st.error(f"Snapshot directory not found: {SNAPSHOT_DIR}")
