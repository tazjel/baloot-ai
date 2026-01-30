
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.visionary.visionary import VisionaryProcessor, Profile
import cv2

def test_roi_calibration():
    # 1. Define Paths
    # We will look for an artifact image in the project root or use a placeholder
    artifact_path = "C:/Users/MiEXCITE/.gemini/antigravity/brain/f3623068-56ea-430b-ae0d-82cba6a7c96d/uploaded_media_0_1769783663643.png"
    
    output_path = "roi_calibration_result.png"

    # 2. Initialize Processor
    print("Initializing Visionary Processor...")
    processor = VisionaryProcessor(profile_name=Profile.EXTERNAL_APP_WEB)

    # 3. Load Image
    print(f"Loading image from {artifact_path}...")
    image = processor.load_image(artifact_path)

    if image is None:
        print("Failed to load image. Please verify the path.")
        # Create a dummy image for testing logic
        print("Creating dummy black image for test...")
        image = cv2.imread("uploaded_media_0.png") # Try local relative
        if image is None:
             import numpy as np
             image = np.zeros((1080, 1920, 3), dtype=np.uint8)

    # 4. Extract and Draw
    print("Extracting ROIs and creating debug visual...")
    processor.debug_show_rois(image, save_path=output_path)
    
    print("Test Complete.")

if __name__ == "__main__":
    test_roi_calibration()
