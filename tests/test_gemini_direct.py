import os
import sys
from ai_worker.llm_client import GeminiClient

# Manually load env if needed (but start_dev should have set it, assume this script runs in same env)
# If running via `python`, need to ensure env vars are set or load .env

def test_gemini_direct():
    api_key = os.environ.get("GEMINI_API_KEY")
    print(f"API Key Present: {bool(api_key)}")
    if not api_key:
        # Try loading from .env or .env.local
        for env_file in ['.env', '.env.local']:
            if os.path.exists(env_file):
                try:
                     with open(env_file) as f:
                         for line in f:
                             if line.startswith("GEMINI_API_KEY="):
                                 os.environ["GEMINI_API_KEY"] = line.strip().split("=")[1]
                                 print(f"Loaded API Key from {env_file}")
                                 api_key = os.environ["GEMINI_API_KEY"]
                                 break
                except:
                     pass
            if api_key: break

    client = GeminiClient()
    
    img_path = os.path.join(os.getcwd(), "uploads", "dataset", "img_1316ba734ed74dcca50c3ca943bd988e.jpg")
    print(f"Analyzing {img_path}...")
    
    with open(img_path, "rb") as f:
        data = f.read()
        result = client.analyze_image(data)
        
    print("Result:", result)

if __name__ == "__main__":
    test_gemini_direct()
