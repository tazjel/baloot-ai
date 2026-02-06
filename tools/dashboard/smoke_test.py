import sys
import os

# Add project root to path
sys.path.insert(0, r"c:\Users\MiEXCITE\Projects\baloot-ai")

# Mock streamlit 
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()
sys.modules['streamlit.set_page_config'] = MagicMock()
# Mock submodules
sys.modules["modules"] = MagicMock()

try:
    # We just want to check if the file parses and local imports work
    # But streamlit apps are scripts, so importing them executes them. 
    # This might be tricky.
    # Instead, let's just syntax check.
    with open(r"c:\Users\MiEXCITE\Projects\baloot-ai\tools\dashboard\app.py", "r", encoding="utf-8") as f:
        compile(f.read(), "app.py", "exec")
    print("Syntax Valid")
except Exception as e:
    print(f"Syntax Error: {e}")
