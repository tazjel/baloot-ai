
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# from server.settings import GEMINI_API_KEY
from ai_worker.llm_client import GeminiClient

print(f"API Key Present in Env: {bool(os.environ.get('GEMINI_API_KEY'))}")

try:
    client = GeminiClient()
    print("✅ GeminiClient instantiated successfully.")
except Exception as e:
    print(f"❌ GeminiClient failed: {e}")
