from ultralytics import YOLO
import os
import yaml
import glob
from tqdm import tqdm

def auto_label_dataset(images_dir, labels_dir, data_yaml_path):
    """
    Uses YOLO-World to zero-shot detect cards and save labels.
    """
    print("Loading YOLO-World model (yolov8l-worldv2)...")
    # Using 'l' (large) model for better accuracy during labeling
    model = YOLO('yolov8l-worldv2.pt') 

    # Load class names from yaml
    with open(data_yaml_path, 'r') as f:
        data_cfg = yaml.safe_load(f)
        class_names = data_cfg['names']

    # Define natural language prompts for YOLO-World
    # We map the class ID to a descriptive prompt
    prompts = []
    
    # Map '7S' to "playing card seven of spades", etc.
    suit_map = {'S': 'spades', 'H': 'hearts', 'D': 'diamonds', 'C': 'clubs'}
    rank_map = {
        '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten', 
        'J': 'jack', 'Q': 'queen', 'K': 'king', 'A': 'ace'
    }

    print("Setting custom vocabulary for Baloot cards...")
    custom_vocab = []
    
    # Iterate through classes in order of ID to ensure alignment
    sorted_ids = sorted(class_names.keys())
    
    for cls_id in sorted_ids:
        name = class_names[cls_id]
        if name == "CARD_BACK":
            prompt = "back of playing card"
        else:
            # Parse 7S, 10H, etc.
            rank = name[:-1]
            suit = name[-1]
            
            rank_text = rank_map.get(rank, rank)
            suit_text = suit_map.get(suit, suit)
            
            prompt = f"playing card {rank_text} of {suit_text}"
        
        custom_vocab.append(prompt)
        
    print(f"Vocabulary: {custom_vocab}")
    model.set_classes(custom_vocab)

    # Process Images
    image_files = glob.glob(os.path.join(images_dir, "*.jpg")) + \
                  glob.glob(os.path.join(images_dir, "*.png"))
    
    print(f"Labeling {len(image_files)} images...")
    os.makedirs(labels_dir, exist_ok=True)

    for img_path in tqdm(image_files):
        # Run inference with higher resolution and lower confidence
        results = model.predict(img_path, conf=0.05, iou=0.5, imgsz=1280, save=False, verbose=False)
        
        result = results[0]
        filename = os.path.basename(img_path)
        label_filename = os.path.splitext(filename)[0] + ".txt"
        label_path = os.path.join(labels_dir, label_filename)
        
        with open(label_path, 'w') as f:
            for box in result.boxes:
                # YOLO format: class x_center y_center width height
                # All normalized 0-1
                cls_id = int(box.cls[0])
                xywhn = box.xywhn[0].tolist()
                
                line = f"{cls_id} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}\n"
                f.write(line)

    print(f"Finished auto-labeling to {labels_dir}")

if __name__ == "__main__":
    auto_label_dataset(
        "dataset/images/train", 
        "dataset/labels/train", 
        "dataset/data.yaml"
    )
