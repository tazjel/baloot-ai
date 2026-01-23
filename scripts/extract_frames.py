import cv2
import os
import glob

# Configuration
VIDEO_PATH = r".agent/knowledge/Full_round_kamelna_Recording 2026-01-07 043250.mp4"
OUTPUT_DIR = r".agent/knowledge/video_frames"
INTERVAL_SECONDS = 5  # Extract one frame every 5 seconds

def extract_frames():
    if not os.path.exists(VIDEO_PATH):
        print(f"Error: Video file not found at {VIDEO_PATH}")
        # Try finding it with glob in case of path issues
        files = glob.glob(".agent/knowledge/*.mp4")
        if files:
            print(f"Found similar files: {files}")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    print(f"Video Info: {fps} FPS, {total_frames} frames, {duration:.2f} seconds.")

    frame_interval = int(fps * INTERVAL_SECONDS)
    count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if count % frame_interval == 0:
            timestamp = count / fps
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            filename = f"kamelna_{minutes:02d}m{seconds:02d}s.jpg"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # Optional: Resize if too massive (e.g. > 1920 width)
            h, w = frame.shape[:2]
            if w > 1920:
                scale = 1920 / w
                frame = cv2.resize(frame, (1920, int(h * scale)))

            cv2.imwrite(filepath, frame)
            print(f"Saved {filename}")
            saved_count += 1

        count += 1

    cap.release()
    print(f"Done. Extracted {saved_count} frames to {OUTPUT_DIR}")

if __name__ == "__main__":
    extract_frames()
