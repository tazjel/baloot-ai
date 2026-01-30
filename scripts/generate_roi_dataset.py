import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shutil
import glob
from game_engine.visionary.visionary import DatasetGenerator

def reset_dataset():
    # Clear existing data
    dirs = [
        "dataset/images/train",
        "dataset/images/val",
        "dataset/labels/train",
        "dataset/labels/val"
    ]
    for d in dirs:
        if os.path.exists(d):
            print(f"Clearing {d}...")
            files = glob.glob(os.path.join(d, "*"))
            for f in files:
                os.remove(f)
        os.makedirs(d, exist_ok=True)

def generate_rois():
    # Initialize Generator
    # We hack the output_dir to be 'dataset' so it uses 'dataset/images'
    # But we want 'dataset/images/train'. 
    # The DatasetGenerator hardcodes 'images' and 'labels' subdirs.
    # So we will let it generate to 'dataset_temp' and move them.
    
    temp_dir = "dataset_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    print("Initializing DatasetGenerator...")
    generator = DatasetGenerator(output_dir=temp_dir)
    
    video_path = "dataset/Project.mp4"
    if not os.path.exists(video_path):
        print(f"Error: Video not found at {video_path}")
        return

    print(f"Processing {video_path}...")
    # interval=0.5 to get more frames since we are splitting them
    generator.process_video_for_training(video_path, interval=1.0) 
    
    # Move to train dir
    src_images = os.path.join(temp_dir, "images")
    dst_images = "dataset/images/train"
    
    count = 0
    if os.path.exists(src_images):
        for f in os.listdir(src_images):
            shutil.move(os.path.join(src_images, f), os.path.join(dst_images, f))
            count += 1
            
    print(f"Moved {count} ROI images to {dst_images}")
    
    # Clean up
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    reset_dataset()
    generate_rois()
