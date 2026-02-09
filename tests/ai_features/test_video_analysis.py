import requests
import os
import time

# Configuration
API_URL = "http://127.0.0.1:3005/react-py4web/analyze_screenshot"
# Use the known video file
VIDEO_PATH = os.path.join(os.getcwd(), "kamelnna_desktop.mp4")

def test_analyze_video():
    if not os.path.exists(VIDEO_PATH):
        print(f"Video not found at {VIDEO_PATH}")
        return

    print(f"Testing Video Analysis with {VIDEO_PATH}...")
    print("This may take 10-20 seconds for upload and processing...")
    
    try:
        start_time = time.time()
        with open(VIDEO_PATH, 'rb') as f:
            files = {'screenshot': ('game_video.mp4', f, 'video/mp4')}
            response = requests.post(API_URL, files=files)
            
        print(f"Response Time: {time.time() - start_time:.2f}s")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                print("SUCCESS: AI returned analysis data.")
                print("Game State Summary:")
                print(str(data['data'])[:500])
            else:
                print("FAILURE: No 'data' field in response.")
        else:
            print("Error Response:", response.text)

    except Exception as e:
        print(f"Test Execution Failed: {e}")

if __name__ == "__main__":
    test_analyze_video()
