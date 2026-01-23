import requests
import os

# Path to the user's uploaded image (absolute path from metadata)
IMAGE_PATH = r"C:/Users/MiEXCITE/.gemini/antigravity/brain/4ddca2fa-5f9f-4928-8efb-e5f9e2e7ef89/uploaded_image_1768685881050.png"
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
