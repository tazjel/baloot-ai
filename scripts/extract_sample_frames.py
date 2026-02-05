import cv2
import os
import sys

def extract_samples(video_path, output_dir="debug_samples", num_samples=5):
    if not os.path.exists(video_path):
        print(f"❌ Error: Video not found at {video_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error: Could not open video.")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"🎥 Video loaded: {total_frames} frames found.")

    interval = total_frames // (num_samples + 1)
    
    print(f"📸 Extracting {num_samples} diagnostic frames...")

    for i in range(num_samples):
        frame_idx = interval * (i + 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if ret:
            # Save raw frame
            filename = f"sample_{i+1}.jpg"
            save_path = os.path.join(output_dir, filename)
            cv2.imwrite(save_path, frame)
            print(f"   ✅ Saved: {save_path}")
    
    cap.release()
    print(f"\n✨ Done! Drag these 5 images into Claude to help it 'see' the layout.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_sample_frames.py <video_path>")
        print("Example: python scripts/extract_sample_frames.py dataset/my_replay.mp4")
    else:
        extract_samples(sys.argv[1])
