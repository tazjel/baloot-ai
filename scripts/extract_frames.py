import sys
import os
import cv2

def extract_frames_stream(video_path, output_dir, interval=1.0):
    if not os.path.exists(video_path):
        print(f"Video not found: {video_path}")
        return

    print(f"Extracting frames from {video_path} every {interval}s to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error opening video stream or file")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 30
    
    frame_interval = int(fps * interval)
    print(f"FPS: {fps}, Interval frames: {frame_interval}")
    
    count = 0
    saved_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if count % frame_interval == 0:
            fname = f"frame_{saved_count:04d}.jpg"
            path = os.path.join(output_dir, fname)
            cv2.imwrite(path, frame)
            saved_count += 1
            if saved_count % 10 == 0:
                print(f"Saved {saved_count} frames...")
        
        count += 1
        
    cap.release()
    print(f"Done! Saved {saved_count} frames to {output_dir}")

if __name__ == "__main__":
    video = "dataset/Project.mp4"
    out = "dataset/images/train" 
    extract_frames_stream(video, out, interval=2.0)
