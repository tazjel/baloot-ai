import sys
import os

# Emulate Streamlit adding current dir to path
current_dir = os.path.join(os.getcwd(), 'tools', 'dashboard')
sys.path.append(current_dir)

print(f"Path: {sys.path}")

try:
    from modules.launcher import render_launcher_tab
    print("Success: modules.launcher imported")
except ImportError as e:
    print(f"Error importing modules.launcher: {e}")

try:
    from modules.utils import get_redis_client
    print("Success: modules.utils imported")
except ImportError as e:
    print(f"Error importing modules.utils: {e}")
