import cv2
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import os

@dataclass
class ROI:
    x: int
    y: int
    w: int
    h: int
    name: str

class Profile:
    EXTERNAL_APP_WEB = "EXTERNAL_APP_WEB"
    EXTERNAL_APP_ARCHIVE = "EXTERNAL_APP_ARCHIVE"

class VisionaryProcessor:
    def __init__(self, profile_name: str = Profile.EXTERNAL_APP_WEB):
        self.profile_name = profile_name
        self.rois = self._load_rois(profile_name)

    def _load_rois(self, profile_name: str) -> Dict[str, ROI]:
        """
        Defines Regions of Interest for supported layouts.
        Coordinates are based on a normalized 1920x1080 reference canvas.
        """
        if profile_name == Profile.EXTERNAL_APP_WEB:
            return {
                # POV Hand (Bottom Center) - Approximate
                "hand_card_1": ROI(600, 900, 100, 150, "hand_1"),
                # ... other cards would be calculated relative to this or explicitly defined
                
                # Center Table (The "Floor")
                "floor": ROI(800, 400, 320, 240, "floor"),
                
                # Scores (Top Corners usually, or Side in Desktop)
                "score_us": ROI(100, 100, 200, 50, "score_us"),
                "score_them": ROI(1620, 100, 200, 50, "score_them"),
                
                # Bid Info (Center or Sidebar)
                "bid_info": ROI(800, 300, 320, 80, "bid_info")
            }
        return {}

    def load_image(self, path: str) -> Optional[np.ndarray]:
        if not os.path.exists(path):
            print(f"Error: File not found {path}")
            return None
        return cv2.imread(path)

    def extract_rois(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Extracts sub-images for each defined ROI.
        Resizes input image to reference 1920x1080 before extraction to match ROI coords.
        """
        # Resize to reference resolution for consistent ROI extraction
        target_h, target_w = 1080, 1920
        resized = cv2.resize(image, (target_w, target_h))
        
        extracted = {}
        for name, roi in self.rois.items():
            # Basic bounds check
            y2 = min(roi.y + roi.h, target_h)
            x2 = min(roi.x + roi.w, target_w)
            
            crop = resized[roi.y:y2, roi.x:x2]
            extracted[name] = crop
            
        return extracted

    def extract_frames_from_video(self, video_path: str, interval_seconds: float = 1.0) -> List[np.ndarray]:
        """
        Extracts frames from a video file at a specified interval.
        """
        if not os.path.exists(video_path):
            print(f"Error: Video file not found {video_path}")
            return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30 # Fallback

        frames = []
        frame_interval = int(fps * interval_seconds)
        
        count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if count % frame_interval == 0:
                frames.append(frame)
            
            count += 1
            
        cap.release()
        print(f"Extracted {len(frames)} frames from {video_path}")
        return frames

    def debug_show_rois(self, image: np.ndarray, save_path: str = "debug_rois.png"):
        """Draws rectangles around ROIs for visual validation"""
        if image is None:
            print("Error: No image provided for debug")
            return

        target_h, target_w = 1080, 1920
        # Check aspect ratio to decide if we crop or pad, but for now strict resize
        debug_img = cv2.resize(image, (target_w, target_h))
        
        for name, roi in self.rois.items():
            # Draw Outer Box
            cv2.rectangle(debug_img, (roi.x, roi.y), (roi.x + roi.w, roi.y + roi.h), (0, 255, 0), 2)
            
            # Draw semi-transparent fill
            overlay = debug_img.copy()
            cv2.rectangle(overlay, (roi.x, roi.y), (roi.x + roi.w, roi.y + roi.h), (0, 255, 0), -1)
            alpha = 0.2
            debug_img = cv2.addWeighted(overlay, alpha, debug_img, 1 - alpha, 0)
            
            # Label
            label = f"{name} ({roi.w}x{roi.h})"
            cv2.putText(debug_img, label, (roi.x, roi.y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
        cv2.imwrite(save_path, debug_img)
        print(f"Saved ROI debug image to {save_path}")

class CardRecognizer:
    def __init__(self):
        # Placeholder for YOLO model or Template Matcher
        self.model = None

    def predict(self, roi_image: np.ndarray) -> List[str]:
        """
        Returns a list of detected card codes (e.g. ['AS', 'KH', '7D'])
        """
        # TODO: Implement actual recognition
        return []

class DatasetGenerator:
    def __init__(self, output_dir: str = "dataset"):
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        self.labels_dir = os.path.join(output_dir, "labels")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.labels_dir, exist_ok=True)
        self.processor = VisionaryProcessor()

    def process_video_for_training(self, video_path: str, interval: float = 2.0):
        """
        Extracts frames from video, crops valid play areas (Hand, Floor),
        and saves them for labeling.
        """
        frames = self.processor.extract_frames_from_video(video_path, interval)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        count = 0
        for i, frame in enumerate(frames):
            rois = self.processor.extract_rois(frame)
            
            # We are primarily interested in the 'floor' and 'hand' for object detection training
            # 'score' is usually OCR, but we can save it too.
            
            for roi_name, roi_img in rois.items():
                if roi_name in ["floor", "hand_1"]: # Focus on these for YOLO
                    filename = f"{video_name}_{i:04d}_{roi_name}.jpg"
                    path = os.path.join(self.images_dir, filename)
                    cv2.imwrite(path, roi_img)
                    count += 1
                    
        print(f"Generated {count} training images in {self.images_dir}")

# Example Usage
if __name__ == "__main__":
    VP = VisionaryProcessor()
    # Test execution logic can go here
    print("Visionary Processor Initialized")

