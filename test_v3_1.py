import sys
import os

# Emulate Streamlit adding current dir to path
current_dir = os.path.join(os.getcwd(), 'tools', 'dashboard')
sys.path.append(current_dir)

try:
    from modules.inspector import render_inspector_tab
    print("✅ modules.inspector imported")
except ImportError as e:
    print(f"❌ Error importing modules.inspector: {e}")

try:
    from modules.trace import render_trace_tab
    print("✅ modules.trace imported")
except ImportError as e:
    print(f"❌ Error importing modules.trace: {e}")

try:
    import pandas
    print("✅ pandas imported")
except ImportError as e:
    print(f"❌ Error importing pandas: {e}")
