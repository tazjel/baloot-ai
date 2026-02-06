import streamlit as st
import os
import glob
import subprocess
import streamlit.components.v1 as components
from datetime import datetime
from .utils import get_redis_client

def run_cmd_capture(cmd, cwd=None):
    try:
        # Use shell=True for standard shell commands
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10, cwd=cwd)
        return res.stdout.strip() if res.stdout else res.stderr.strip()
    except Exception as e:
        return f"Error: {e}"

def generate_deep_diagnostic_report():
    """Generates a comprehensive system state report for AI Agent debugging."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. System Health (Concise)
    # Docker: Only show relevant containers or count
    docker_raw = run_cmd_capture("docker ps --format '{{.Names}} ({{.Status}})'")
    docker_info = docker_raw if docker_raw else "No active containers"
    
    # Processes: filtered for key components
    tasklist = run_cmd_capture("tasklist /FI \"IMAGENAME eq python.exe\" /NH")
    python_count = tasklist.count("python.exe") if tasklist else 0
    
    # Ports (Essentials)
    ports_raw = run_cmd_capture("netstat -ano | findstr \"3005 5173 6379\"")
    ports_info = ports_raw if ports_raw else "Critical ports not listening"

    # Git: Check for dirty state
    git_status = run_cmd_capture("git status --short")
    git_info = git_status if git_status else "Clean"
    
    # 2. Redis State
    r = get_redis_client()
    redis_info = "Not Connected"
    if r:
        try:
            info = r.info()
            keys = r.keys("game:*")
            redis_info = f"✅ Connected. Keys: {len(keys)}. Mem: {info.get('used_memory_human', '?')}"
        except Exception as e:
            redis_info = f"❌ Error: {e}"

    # 3. Code Integrity (Inspector Integration)
    # Python Lint (Fast check)
    flake8_cmd = "flake8 server game_engine ai_worker --count --select=E9,F63,F7,F82 --show-source --statistics"
    flake8_out = run_cmd_capture(flake8_cmd)
    flake8_res = "✅ Pass" if not flake8_out or "0" in flake8_out.splitlines()[-1] else f"⚠️ Issues Found:\n{flake8_out}"

    # Frontend formatting check
    # prettier_cmd = "npx prettier \"src/**/*.{ts,tsx}\" --check"
    # prettier_out = run_cmd_capture(prettier_cmd, cwd="frontend")
    # prettier_res = "✅ Pass" if "Checking..." in prettier_out or not prettier_out else "⚠️ Issues"

    # 4. Smart Log Analysis
    # Instead of tailing blindly, we check for ERRORs first
    server_log_content = "No logs found"
    log_summary = "No logs analyzed"
    
    try:
        if os.path.exists("logs/server_stdout.log"):
            with open("logs/server_stdout.log", "r", encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                # Check for ERROR/CRITICAL in last 200 lines to be safe
                last_200 = lines[-200:]
                errors = [l for l in last_200 if "ERROR" in l or "CRITICAL" in l]
                if errors:
                     log_summary = f"🚨 {len(errors)} Errors in last 200 lines"
                     # Show last 5 errors + last 10 lines of context
                     server_log_content = "".join(errors[-5:]) + "\n... (context) ...\n" + "".join(lines[-10:])
                else:
                     log_summary = "✅ Clean (Last 200 lines)"
                     server_log_content = "".join(lines[-15:]) # Just show context
    except Exception as e:
        server_log_content = f"Error reading logs: {e}"

    report = f"""
# 🕵️ Deep Diagnostic Report
**Time**: {timestamp}

## 1. Vital Signs
| Component | Status | Details |
| :--- | :--- | :--- |
| **Redis** | {redis_info} | |
| **Docker** | Active | `{docker_info}` |
| **Processes** | Running | `{python_count} Python processes` |
| **Git** | Status | `{git_info}` |

## 2. Code Integrity
**Python (Flake8 Critical)**:
```
{flake8_res}
```

## 3. Log Analysis
**Status**: {log_summary}

**Recent Context (Optimized)**:
```
{server_log_content}
```

## 4. User Note
(Describe the bug here...)
"""
    return report

def render_reports_tab():
    st.header("📈 Test Reports")
    report_path = "diagnostics/report.html"
    
    col_r1, col_r2 = st.columns([1, 4])
    with col_r1:
        if st.button("🔄 Refresh Report"):
            st.rerun()
            
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        components.html(html_content, height=800, scrolling=True)
    else:
        st.info("No report found in diagnostics/report.html. Run /nw to generate one.")
