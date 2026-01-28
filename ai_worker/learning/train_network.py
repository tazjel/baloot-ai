
import sys
import os
import csv
import ast
import random
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# Add parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_worker.learning.feature_extractor import FeatureExtractor
from ai_worker.learning.model import StrategyNet

# Determine Device
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Training on: {DEVICE}")

class BalootDataset(Dataset):
    def __init__(self, csv_file):
        self.samples = []
        self.extractor = FeatureExtractor()
        
        print(f"Loading dataset from {csv_file}...")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None) # Skip header
                for row in reader:
                    if not row: continue
                    # row: [ts, game_id, vector_str, mcts_move_idx, target_str, win_rate]
                    if len(row) < 5: continue
                    
                    vector_str = row[2]
                    target_str = row[4] # "7S" (RankSuit)
                    
                    # Parse Input Vector
                    # vector_str is comma separated floats "0.00,1.00,..."
                    vector = [float(x) for x in vector_str.split(',')]
                    
                    # Parse Target (Card Label)
                    label_idx = self._parse_target_to_idx(target_str)
                    
                    if label_idx != -1 and len(vector) == 138:
                        self.samples.append({
                            'vector': torch.tensor(vector, dtype=torch.float32),
                            'label': torch.tensor(label_idx, dtype=torch.long)
                        })
                        
            print(f"Loaded {len(self.samples)} valid samples.")
            
        except Exception as e:
            print(f"Error loading dataset: {e}")

    def _parse_target_to_idx(self, target_str):
        # Format "7S", "10H", "AD" -> Rank + Suit
        if not target_str or target_str == 'None': return -1
        
        # Extract Suit (Last char)
        suit_char = target_str[-1]
        
        # Extract Rank (Rest)
        rank_str = target_str[:-1]
        
        # Normalize Suit
        norm_suit = self.extractor.suit_map.get(suit_char)
        if not norm_suit: return -1
        
        # Construct Key for FeatureExtractor map (SuitRank e.g. "♠7")
        key = f"{norm_suit}{rank_str}"
        
        return self.extractor.card_to_idx.get(key, -1)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]

def train():
    # Paths
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "ai_worker", "data", "training", "dataset.csv")
    models_dir = os.path.join(project_root, "ai_worker", "models")
    os.makedirs(models_dir, exist_ok=True)
    
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        return

    # Hyperparameters
    BATCH_SIZE = 64
    EPOCHS = 20 # Start small
    LR = 0.001
    
    # Data
    full_dataset = BalootDataset(dataset_path)
    if len(full_dataset) == 0:
        print("Dataset empty. Run generate_neural_data.py first.")
        return
        
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(full_dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # Model
    model = StrategyNet().to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=LR)
    criterion = nn.CrossEntropyLoss()
    
    print(f"Starting Training: {EPOCHS} Epochs")
    
    best_acc = 0.0
    
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch in train_loader:
            x = batch['vector'].to(DEVICE)
            y = batch['label'].to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(x)
            loss = criterion(outputs, y)
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
            _, predicted = torch.max(outputs.data, 1)
            total += y.size(0)
            correct += (predicted == y).sum().item()
            
        avg_loss = total_loss / len(train_loader)
        train_acc = 100 * correct / total
        
        # Validation
        val_acc = evaluate(model, val_loader)
        
        print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {avg_loss:.4f} | Train Acc: {train_acc:.2f}% | Val Acc: {val_acc:.2f}%")
        
        if val_acc > best_acc:
            best_acc = val_acc
            save_path = os.path.join(models_dir, "strategy_net_best.pth")
            model.save(save_path)
            # print(f"Saved Best Model: {save_path}")

    print(f"Training Complete. Best Validation Accuracy: {best_acc:.2f}%")
    
    # Save Final
    final_path = os.path.join(models_dir, "strategy_net_final.pth")
    model.save(final_path)

def evaluate(model, loader):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for batch in loader:
            x = batch['vector'].to(DEVICE)
            y = batch['label'].to(DEVICE)
            outputs = model(x)
            _, predicted = torch.max(outputs.data, 1)
            total += y.size(0)
            correct += (predicted == y).sum().item()
    return 100 * correct / total

if __name__ == "__main__":
    train()
