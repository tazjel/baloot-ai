import requests
import os

# Path to the test screenshot — set via env var or provide a local path
IMAGE_PATH = os.environ.get("TEST_SCREENSHOT_PATH", "test_screenshot.png")
URL = "http://127.0.0.1:3005/react-py4web/analyze_screenshot"

def test_analyze():
    print(f"Testing {URL} with {IMAGE_PATH}")
    if not os.path.exists(IMAGE_PATH):
        print("Image file not found!")
        return

    try:
        with open(IMAGE_PATH, 'rb') as f:
            files = {'screenshot': ('test.png', f, 'image/png')}
            response = requests.post(URL, files=files)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_analyze()
