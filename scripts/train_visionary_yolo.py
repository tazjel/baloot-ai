import os
import yaml
from ultralytics import YOLO
import argparse

def setup_dataset_structure(base_dir="dataset"):
    """
    Creates the necessary directory structure for YOLO training.
    dataset/
      images/
        train/
        val/
      labels/
        train/
        val/
      data.yaml
    """
    dirs = [
        "images/train", "images/val",
        "labels/train", "labels/val"
    ]
    
    for d in dirs:
        path = os.path.join(base_dir, d)
        os.makedirs(path, exist_ok=True)
        print(f"Verified directory: {path}")

def create_data_yaml(base_dir="dataset"):
    """
    Generates the data.yaml file defining the 53 classes for Baloot cards.
    """
    # 52 Cards + Back
    ranks = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2']
    suits = ['S', 'H', 'D', 'C'] # Spades, Hearts, Diamonds, Clubs
    
    classes = {}
    idx = 0
    
    # Generate standard deck
    for s in suits:
        for r in ranks:
            classes[idx] = f"{r}{s}"
            idx += 1
            
    # Add back of card
    classes[idx] = "CARD_BACK"
    
    data = {
        'path': os.path.abspath(base_dir),
        'train': 'images/train',
        'val': 'images/val',
        'names': classes
    }
    
    yaml_path = os.path.join(base_dir, "data.yaml")
    with open(yaml_path, 'w') as f:
        yaml.dump(data, f, sort_keys=False)
        
    print(f"Created data configuration: {yaml_path}")
    return yaml_path

def train_model(data_yaml, epochs=50, imgsz=640):
    print(f"Starting Training with {data_yaml}...")
    # Load a model
    model = YOLO("yolov8n.pt")  # load a pretrained model (nano version for speed)

    # Train the model
    results = model.train(
        data=data_yaml, 
        epochs=epochs, 
        imgsz=imgsz,
        plots=True,
        batch=16,
        name='baloot_clash'
    )
    print("Training Complete!")
    print(f"Best model saved at: {results.save_dir}/weights/best.pt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visionary Studio YOLO Trainer")
    parser.add_argument("--setup-only", action="store_true", help="Only create folder structure and yaml")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    
    args = parser.parse_args()
    
    setup_dataset_structure()
    yaml_path = os.path.join("dataset", "data.yaml")
    if not os.path.exists(yaml_path) or args.setup_only:
        yaml_path = create_data_yaml()
    else:
        print(f"Using existing config: {yaml_path}")
    
    if not args.setup_only:
        train_model(yaml_path, epochs=args.epochs)
