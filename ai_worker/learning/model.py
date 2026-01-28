
import torch
import torch.nn as nn
import torch.nn.functional as F

class StrategyNet(nn.Module):
    """
    Feed-Forward Neural Network to predict optimal card to play.
    Input: 138 Features (Hand, Table, Context)
    Output: 32 Logits (One per Card in Deck)
    """
    def __init__(self, input_size=138, num_classes=32):
        super(StrategyNet, self).__init__()
        
        self.fc1 = nn.Linear(input_size, 256)
        self.bn1 = nn.BatchNorm1d(256)
        
        self.fc2 = nn.Linear(256, 128)
        self.bn2 = nn.BatchNorm1d(128)
        
        self.fc3 = nn.Linear(128, 64)
        self.bn3 = nn.BatchNorm1d(64)
        
        self.head_policy = nn.Linear(64, num_classes)
        
        self.dropout = nn.Dropout(0.3)
        
    def forward(self, x):
        # Layer 1
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        # Layer 2
        x = self.fc2(x)
        x = self.bn2(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        # Layer 3
        x = self.fc3(x)
        x = self.bn3(x)
        x = F.relu(x)
        
        # Output Head
        logits = self.head_policy(x)
        return logits

    def save(self, path):
        torch.save(self.state_dict(), path)
        
    def load(self, path):
        self.load_state_dict(torch.load(path))
        self.eval()
