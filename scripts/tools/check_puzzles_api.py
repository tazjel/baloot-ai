
import requests
import json

def check_api():
    url = "http://127.0.0.1:3005/puzzles"
    try:
        print(f"Fetching {url}...")
        res = requests.get(url, timeout=5)
        print(f"Status Code: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            print("Response Data:")
            print(json.dumps(data, indent=2))
            
            puzzles = data.get("puzzles", [])
            print(f"Found {len(puzzles)} puzzles in response.")
        else:
            print("Error response:", res.text)
            
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    check_api()
