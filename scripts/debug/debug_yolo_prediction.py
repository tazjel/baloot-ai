import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ultralytics import YOLO
import cv2
import glob
from game_engine.visionary.visionary import VisionaryProcessor

def debug_prediction(model_path, image_path):
    print(f"Loading Model: {model_path}")
    model = YOLO(model_path)
    
    print(f"Loading Image: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        print("Failed to load image")
        return

    # 1. Predict on FULL image (1280px)
    print("Predicting on FULL image...")
    results_full = model.predict(img, conf=0.10, imgsz=1280)
    
    # Save visualized full image
    res_plotted = results_full[0].plot()
    cv2.imwrite("debug_prediction_full.jpg", res_plotted)
    print("Saved debug_prediction_full.jpg")
    
    # 2. Predict on ROIs
    vp = VisionaryProcessor()
    # ROIs rely on 1920x1080 normalization
    rois = vp.extract_rois(img)
    
    for name, roi in rois.items():
        if name in ["floor", "hand_card_1"]:
            print(f"Predicting on ROI: {name}")
            results_roi = model.predict(roi, conf=0.10, imgsz=640)
            roi_plotted = results_roi[0].plot()
            cv2.imwrite(f"debug_prediction_{name}.jpg", roi_plotted)
            print(f"Saved debug_prediction_{name}.jpg")

def draw_yolo_labels(img, label_path, class_names):
    if not os.path.exists(label_path):
        return img
    
    with open(label_path, 'r') as f:
        lines = f.readlines()
        
    h, w, _ = img.shape
    for line in lines:
        parts = line.strip().split()
        cls_id = int(parts[0])
        x_center = float(parts[1]) * w
        y_center = float(parts[2]) * h
        width = float(parts[3]) * w
        height = float(parts[4]) * h
        
        x1 = int(x_center - width/2)
        y1 = int(y_center - height/2)
        x2 = int(x_center + width/2)
        y2 = int(y_center + height/2)
        
        # Draw GT in Green
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
        cv2.putText(img, f"GT: {label}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return img

if __name__ == "__main__":
    # Load class names
    import yaml
    with open("dataset/data.yaml", 'r') as f:
        data = yaml.safe_load(f)
        names = data['names']

    # Find a test image
    images = glob.glob("dataset/images/train/*.jpg")
    import random
    random.shuffle(images)
    
    for i, img_path in enumerate(images[:5]): # Test on 5 random images
        print(f"--- Debugging Image {i+1}: {img_path} ---")
        debug_prediction("models/yolo_v8n_baloot.pt", img_path)
        
        # Visualize GT
        img = cv2.imread(img_path)
        label_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
        img_gt = draw_yolo_labels(img, label_path, names)
        cv2.imwrite(f"debug_gt_{i}.jpg", img_gt)
        print(f"Saved debug_gt_{i}.jpg")
