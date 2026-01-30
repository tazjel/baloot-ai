
# Train Theory of Mind

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import sys
from pathlib import Path

# Add path
sys.path.append(str(Path(__file__).parent.parent))
from ai_worker.learning.mind_reader import MindReaderNet

class MindDataset(Dataset):
    def __init__(self, path):
        self.data = torch.load(path)
        
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        # x: [Seq], y: [4, 32]
        x, y = self.data[idx]
        return x, y

def collate_fn(batch):
    # Pad sequences to max length in batch
    xs, ys = zip(*batch)
    max_len = max([len(x) for x in xs])
    
    padded_xs = []
    masks = []
    
    for x in xs:
        # 0 is padding token
        pad_len = max_len - len(x)
        padded = torch.cat([x, torch.zeros(pad_len, dtype=torch.long)])
        padded_xs.append(padded)
        
        # Mask: True for Padding position? PyTorch Transformer src_key_padding_mask
        # shape (N, S), True where padding
        mask = torch.zeros(max_len, dtype=torch.bool)
        if pad_len > 0:
            mask[-pad_len:] = True
        masks.append(mask)
        
    return torch.stack(padded_xs), torch.stack(masks), torch.stack(ys)

def train():
    print("Initializing Training...")
    dataset = MindDataset("ai_worker/data/mind_data.pt")
    loader = DataLoader(dataset, batch_size=16, shuffle=True, collate_fn=collate_fn)
    
    model = MindReaderNet()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCEWithLogitsLoss()
    
    epochs = 20
    model.train()
    
    for epoch in range(epochs):
        total_loss = 0
        correct_cards = 0
        total_predictions = 0
        
        for x, mask, y in loader:
            optimizer.zero_grad()
            
            # Forward
            # Viewpoint Assumption: Model is always 'Bottom' (Player 0) viewpoint in this basic setup
            # But the dataset contains perspectives for everyone. 
            # In input sequence, we need to know WHO the generic "Left/Right" refers to.
            # Limitation: The simplified generator didn't rotate the perspective.
            # Assuming we are predicting absolute hands for P1(Right), P2(Top), P3(Left) from P0 frame.
            
            pred_l, pred_p, pred_r = model(x, mask)
            
            # Y shape: [Batch, 4, 32] (0=Self, 1=Right, 2=Partner, 3=Left)
            # Targets
            target_r = y[:, 1, :]
            target_p = y[:, 2, :]
            target_l = y[:, 3, :]
            
            loss_r = criterion(pred_r, target_r)
            loss_p = criterion(pred_p, target_p)
            loss_l = criterion(pred_l, target_l)
            
            loss = loss_r + loss_p + loss_l
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
            # Accuracy metric (Threshold 0.5)
            with torch.no_grad():
                preds = torch.cat([pred_r, pred_p, pred_l])
                targs = torch.cat([target_r, target_p, target_l])
                
                guess = (torch.sigmoid(preds) > 0.5).float()
                correct_cards += (guess == targs).sum().item()
                total_predictions += targs.numel()
                
        avg_loss = total_loss / len(loader)
        acc = (correct_cards / total_predictions) * 100
        print(f"Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.4f} | Card Acc: {acc:.2f}%")
        
    # Save
    torch.save(model.state_dict(), "ai_worker/models/mind_reader_v1.pth")
    print("Model saved to ai_worker/models/mind_reader_v1.pth")

if __name__ == "__main__":
    train()
