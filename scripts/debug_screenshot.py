
import requests
import os

# Path to the uploaded image in artifacts
IMAGE_PATH = r"C:/Users/MiEXCITE/.gemini/antigravity/brain/04011f34-3e0c-4455-90b5-90c7d02b7541/uploaded_image_1768684057905.png"
URL = "http://127.0.0.1:3005/react-py4web/analyze_screenshot"

def test_upload():
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: Image not found at {IMAGE_PATH}")
        return

    print(f"Attempting to upload {IMAGE_PATH} to {URL}...")
    try:
        with open(IMAGE_PATH, 'rb') as f:
            files = {'screenshot': ('screenshot.png', f, 'image/png')}
            response = requests.post(URL, files=files, timeout=30)
            
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_upload()
