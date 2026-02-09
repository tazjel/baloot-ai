
import os
import glob
import random
import google.generativeai as genai
from dotenv import load_dotenv

# Load API Key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=API_KEY)

def verify_dataset(sample_size=5):
    print(f"Starting Smart Verification with Gemini Flash (Sample: {sample_size})...")
    
    # Get all images
    images = glob.glob("dataset/images/train/*.jpg")
    if not images:
        print("No images found in dataset/images/train")
        return

    # Sample random images
    sample = random.sample(images, min(len(images), sample_size))
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    passed = 0
    total = 0
    
    for img_path in sample:
        filename = os.path.basename(img_path)
        print(f"\nAnalyzing {filename}...")
        
        try:
            # Load bytes
            with open(img_path, "rb") as f:
                img_data = f.read()
                
            prompt = """
            Look at this image. It is a crop from a Baloot card game.
            1. Is there a clearly visible playing card? (Yes/No)
            2. If yes, what is the rank and suit? (e.g., '7 of Spades', 'King of Hearts', 'Ace of Diamonds').
            3. Is it a 'back of card'? (Yes/No)
            
            Output strictly in this format:
            Visible: [Yes/No]
            Card: [Card Name / Back / None]
            """
            
            response = model.generate_content([
                {'mime_type': 'image/jpeg', 'data': img_data},
                prompt
            ])
            
            print(f"Gemini: {response.text.strip()}")
            passed += 1 # Just counting successful API calls for now, logic to parse 'Passed' can be added.
            total += 1
            
            import time
            print("Sleeping for 10s to respect rate limits...")
            time.sleep(10)
            
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            
    print(f"\nVerification Complete. Checked {total} images.")

if __name__ == "__main__":
    verify_dataset()
