import requests
import os

# Configuration
API_URL = "http://127.0.0.1:3005/react-py4web/analyze_screenshot"
# Use the existing image found in the dataset
IMAGE_PATH = os.path.join(os.getcwd(), "uploads", "dataset", "img_1316ba734ed74dcca50c3ca943bd988e.jpg")

def test_analyze_screenshot():
    target_path = IMAGE_PATH
    
    if not os.path.exists(target_path):
        print(f"Image not found at {target_path}")
        # Try to find any jpg in the folder
        dataset_dir = os.path.dirname(target_path)
        if os.path.exists(dataset_dir):
            files = [f for f in os.listdir(dataset_dir) if f.endswith('.jpg')]
            if files:
                target_path = os.path.join(dataset_dir, files[0])
                print(f"Found alternative image: {target_path}")
            else:
                print("No images found in dataset folder.")
                return
        else:
             print(f"Dataset dir {dataset_dir} does not exist.")
             return

    print(f"Testing Screenshot Analysis with {target_path}...")
    
    try:
        with open(target_path, 'rb') as f:
            files = {'screenshot': f}
            response = requests.post(API_URL, files=files)
            
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Response Data:", data)
            if 'data' in data:
                print("SUCCESS: AI returned analysis data.")
                print("Players Detected:", len(data['data'].get('players', [])))
            else:
                print("FAILURE: No 'data' field in response.")
        else:
            print("Error Response:", response.text)

    except Exception as e:
        print(f"Test Execution Failed: {e}")

if __name__ == "__main__":
    test_analyze_screenshot()
