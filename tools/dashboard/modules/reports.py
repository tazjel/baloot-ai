import streamlit as st
import os
import streamlit.components.v1 as components

def render_reports_tab():
    st.header("Test Reports")
    report_path = "diagnostics/report.html"
    
    col_r1, col_r2 = st.columns([1, 4])
    with col_r1:
        if st.button("🔄 Refresh Report"):
            st.rerun()
            
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Determine height based on content approx or fixed
        components.html(html_content, height=800, scrolling=True)
    else:
        st.info("No report found. Run tests to generate one.")
