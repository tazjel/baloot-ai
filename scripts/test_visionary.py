
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.visionary.visionary import VisionaryProcessor, Profile
import cv2

def test_roi_calibration(image_path=None):
    # 1. Define Paths
    if image_path:
        artifact_path = image_path
    else:
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
    
    # 5. Test Recognition
    from game_engine.visionary.visionary import CardRecognizer
    print("Testing Card Recognition...")
    recognizer = CardRecognizer(model_path="models/yolo_v8n_baloot.pt")
    
    # Test on a specific ROI if available, or just the whole image for now to see what it finds
    # In reality, we should pass the 'floor' or 'hand' ROI.
    rois = processor.extract_rois(image)
    
    if "floor" in rois:
        print("Predicting on Floor ROI...")
        cards = recognizer.predict(rois["floor"])
        print(f"Floor Cards: {cards}")
        
    if "hand_card_1" in rois:
         print("Predicting on Hand ROI...")
         cards = recognizer.predict(rois["hand_card_1"])
         print(f"Hand Cards: {cards}")

    print("Test Complete.")

if __name__ == "__main__":
    # Use a real image from the dataset we just created
    import glob
    images = glob.glob("dataset/images/train/*.jpg")
    if images:
        test_img = images[0]
        print(f"Using test image: {test_img}")
        
        processor = VisionaryProcessor(profile_name=Profile.EXTERNAL_APP_WEB)
        img = processor.load_image(test_img)
        processor.debug_show_rois(img)
        
        # Run recognition test
        test_roi_calibration(test_img) 
    else:
        test_roi_calibration()
