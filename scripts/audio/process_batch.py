import sys
import json
import base64
import os
import subprocess

def process_batch(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # Handle Playwright output wrapper
    if '### Result' in content:
        # Split into lines and find the JSON line
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('"') or line.startswith('{'):
                content = line
                break
    
    # Handle double-encoded JSON string (Playwright returns a stringified JSON)
    if content.startswith('"') and content.endswith('"'):
        try:
            content = json.loads(content) # Decode string to get inner JSON string
        except:
            pass # Maybe not a JSON string, try parsing as is

    # Parse the actual data (if it's still a string)
    if isinstance(content, str):
        data = json.loads(content)
    else:
        data = content
    
    output_dir = r'c:\Users\MiEXCITE\Projects\baloot-ai\mobile\assets\sounds'
    os.makedirs(output_dir, exist_ok=True)

    for name, b64_data in data.items():
        if not b64_data:
            print(f"Skipping {name} (no data)")
            continue
            
        wav_path = os.path.join(output_dir, f"{name}.wav")
        mp3_path = os.path.join(output_dir, f"{name}.mp3")
        
        print(f"Processing {name}...")
        try:
            with open(wav_path, 'wb') as audio_file:
                audio_file.write(base64.b64decode(b64_data))
            
            # Convert to MP3
            # Use -y to overwrite, -ab 320k for high quality
            result = subprocess.run(['ffmpeg', '-y', '-i', wav_path, '-ab', '320k', mp3_path], 
                                  check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Clean up WAV
            if os.path.exists(wav_path):
                os.remove(wav_path)
            print(f"  Done: {mp3_path}")
        except Exception as e:
            print(f"  Error processing {name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_batch.py <json_file>")
        sys.exit(1)
    process_batch(sys.argv[1])
