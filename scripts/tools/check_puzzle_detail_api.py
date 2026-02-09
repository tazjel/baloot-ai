
import requests
import json

def check_puzzle_detail():
    # Try to fetch puzzle_3 (one of the seeded ones)
    url = "http://127.0.0.1:3005/puzzles/puzzle_3"
    try:
        print(f"Fetching {url}...")
        res = requests.get(url, timeout=5)
        print(f"Status Code: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            print("Response Data:")
            print(json.dumps(data, indent=2))
        else:
            print("Error response:", res.text)
            
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    check_puzzle_detail()
