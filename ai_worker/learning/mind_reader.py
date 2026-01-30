import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class MindReaderNet(nn.Module):
    """
    Transformer-based 'Theory of Mind' engine.
    Reads a sequence of game events and infers the hidden hands of opponents.
    """
    def __init__(self, vocab_size=128, embed_dim=64, num_heads=4, num_layers=2, num_cards=32):
        super(MindReaderNet, self).__init__()
        
        # 1. Embedding Layer
        # Represent game state as sequence of tokens (Card Played, Bid Made, etc.)
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.pos_encoder = PositionalEncoding(embed_dim)
        
        # 2. Transformer Encoder (The "Brain")
        encoder_layer = nn.TransformerEncoderLayer(d_model=embed_dim, nhead=num_heads, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # 3. Prediction Heads (3 Opponents * 32 Cards)
        # We predict the probability of EACH card being in EACH player's hand.
        # Output shape: [Batch, 3, 32]
        self.head_left = nn.Linear(embed_dim, num_cards)
        self.head_partner = nn.Linear(embed_dim, num_cards)
        self.head_right = nn.Linear(embed_dim, num_cards)
        
    def forward(self, x, mask=None):
        # x: [Batch, SeqLen] (Indices)
        
        # Embed
        x = self.embedding(x) * math.sqrt(64) # Scaling
        x = self.pos_encoder(x)
        
        # Transform
        # Output: [Batch, SeqLen, Embed]
        # We only care about the context at the LAST token (current state)
        feature_seq = self.transformer(x, src_key_padding_mask=mask)
        
        # Pooling: Take the last valid token's embedding as the summary vector
        # Ideally we use the last index, for simplicity here use max-pool or last
        summary_vec = feature_seq[:, -1, :] 
        
        # Predict
        out_left = self.head_left(summary_vec)
        out_partner = self.head_partner(summary_vec)
        out_right = self.head_right(summary_vec)
        
        return out_left, out_partner, out_right

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=500):
        super().__init__()
        import math
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x):
        # x: [Batch, Seq, Dim]
        return x + self.pe[:x.size(1), :]

if __name__ == "__main__":
    # Smoke Test
    import math
    model = MindReaderNet()
    dummy_input = torch.randint(0, 100, (1, 50)) # Batch 1, Seq 50
    l, p, r = model(dummy_input)
    print("Model Output Shapes:", l.shape, p.shape, r.shape)
    print("MindReaderNet initialized successfully.")
