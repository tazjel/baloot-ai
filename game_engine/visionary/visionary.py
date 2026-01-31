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
    COMPETITOR_WEB = "COMPETITOR_WEB"
    COMPETITOR_ARCHIVE = "COMPETITOR_ARCHIVE"

class VisionaryProcessor:
    def __init__(self, profile_name: str = Profile.COMPETITOR_WEB):
        self.profile_name = profile_name
        self.rois = self._load_rois(profile_name)

    def _load_rois(self, profile_name: str) -> Dict[str, ROI]:
        """
        Defines Regions of Interest for supported layouts.
        Coordinates are based on a normalized 1920x1080 reference canvas.
        """
        if profile_name == Profile.COMPETITOR_WEB:
            rois = {
                # Center Table (The "Floor")
                "floor": ROI(800, 400, 320, 240, "floor"),
                
                # Scores
                "score_us": ROI(100, 100, 200, 50, "score_us"),
                "score_them": ROI(1620, 100, 200, 50, "score_them"),
                
                # Bid Info
                "bid_info": ROI(800, 300, 320, 80, "bid_info")
            }

            # Parametrically define 8 hand cards
            # Base position for card 1 (approximate, based on previous value 600)
            # Assuming cards are overlapping or spaced. 
            # If card 1 is at 600, let's assume a spacing of ~80-100px.
            start_x = 550
            y_pos = 900
            card_w = 100
            card_h = 150
            spacing = 110 # Tunable parameter

            for i in range(8):
                idx = i + 1
                rois[f"hand_card_{idx}"] = ROI(
                    x=start_x + (i * spacing),
                    y=y_pos,
                    w=card_w,
                    h=card_h,
                    name=f"hand_{idx}"
                )
            return rois
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

    def compute_dhash(self, image: np.ndarray, hash_size: int = 8) -> int:
        """
        Computes a 'difference hash' for the image.
        Robust against slight lighting changes and exact pixel noise.
        """
        # 1. Resize to (hash_size + 1, hash_size)
        resized = cv2.resize(image, (hash_size + 1, hash_size))
        # 2. Convert to grayscale
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        # 3. Compute differences between adjacent pixels
        diff = gray[:, 1:] > gray[:, :-1]
        # 4. Convert boolean array to int
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

    def are_images_similar(self, hash1: int, hash2: int, threshold: int = 5) -> bool:
        """Returns True if Hamming distance between hashes is <= threshold."""
        return bin(hash1 ^ hash2).count('1') <= threshold

    def extract_frames_from_video(self, video_path: str, interval_seconds: float = 0.5, min_change_threshold: int = 5) -> List[np.ndarray]:
        """
        Extracts frames from a video file, skipping duplicates using dHash.
        
        Args:
            video_path: Path to video.
            interval_seconds: Minimum time between frames (lower = more candidates).
            min_change_threshold: Hamming distance threshold. If diff <= this, frame is skipped.
        """
        if not os.path.exists(video_path):
            print(f"Error: Video file not found {video_path}")
            return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30

        frames = []
        frame_interval = int(fps * interval_seconds)
        
        count = 0
        last_hash = None
        duplicates_skipped = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Check interval first
            if count % frame_interval == 0:
                current_hash = self.compute_dhash(frame)
                
                is_duplicate = False
                if last_hash is not None:
                    if self.are_images_similar(last_hash, current_hash, min_change_threshold):
                        is_duplicate = True
                        duplicates_skipped += 1
                
                if not is_duplicate:
                    frames.append(frame)
                    last_hash = current_hash
            
            count += 1
            
        cap.release()
        print(f"Extracted {len(frames)} unique frames from {video_path} (Skipped {duplicates_skipped} duplicates)")
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
    def __init__(self, model_path: str = "models/yolo_v8n_baloot.pt"):
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            if os.path.exists(self.model_path):
                print(f"Loading CardRecognizer model from {self.model_path}")
                self.model = YOLO(self.model_path)
            else:
                print(f"Warning: Model not found at {self.model_path}")
        except ImportError:
            print("Error: ultralytics not installed. Card recognition disabled.")

    def predict(self, roi_image: np.ndarray, conf_threshold: float = 0.5) -> List[str]:
        """
        Returns a list of detected card codes (e.g. ['AS', 'KH', '7D'])
        """
        if self.model is None or roi_image is None:
            return []

        results = self.model.predict(roi_image, conf=conf_threshold, verbose=False)
        cards = []
        for result in results:
            for box in result.boxes:
                # Get class name
                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]
                cards.append(label)
        
        return list(set(cards)) # Return unique cards found

class DatasetGenerator:
    def __init__(self, output_dir: str = "dataset"):
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        self.labels_dir = os.path.join(output_dir, "labels")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.labels_dir, exist_ok=True)
        self.processor = VisionaryProcessor()

    def process_video_for_training(self, video_path: str, interval: float = 0.5):
        """
        Extracts frames from video, crops valid play areas (Hand 1-8, Floor),
        and saves them for labeling.
        """
        # Capture more frequently (0.5s) because deduplication will filter out the static ones
        frames = self.processor.extract_frames_from_video(video_path, interval)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        count = 0
        for i, frame in enumerate(frames):
            rois = self.processor.extract_rois(frame)
            
            for roi_name, roi_img in rois.items():
                # Capture 'floor' and ALL 'hand_card_X' rois
                if roi_name == "floor" or roi_name.startswith("hand_card_"):
                    filename = f"{video_name}_{i:04d}_{roi_name}.jpg"
                    path = os.path.join(self.images_dir, filename)
                    cv2.imwrite(path, roi_img)
                    count += 1
                    
        print(f"Smart Generator Created {count} training images in {self.images_dir}")

# Example Usage
if __name__ == "__main__":
    VP = VisionaryProcessor()
    # Test execution logic can go here
    print("Visionary Processor Initialized")

