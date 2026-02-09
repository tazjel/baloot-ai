
import json
import torch
import glob
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from ai_worker.learning.mind_utils import MindVocab

def parse_card_str(card_obj):
    # Input: {'suit': '♥', 'rank': 'A', ...}
    # Output: 'HA'
    suit_map = {'♥': 'H', '♦': 'D', '♠': 'S', '♣': 'C'}
    s = suit_map.get(card_obj['suit'])
    r = card_obj['rank']
    if not s: return None
    return f"{s}{r}"

def process_match(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sequences = [] # List of (X, Y) tuples
    # X: Tensor [SeqLen]
    # Y: Tensor [4, 32] (Hands of all 4 players, 1=Held, 0=Not Held) - We will mask 'Self' later at training time
    
    mh = data.get('match_history', [])
    for round_data in mh:
        tricks = round_data.get('tricks', [])
        if not tricks: continue
        
        # 1. Reconstruct Hands (Ground Truth)
        # player_hands[player_idx] = set(card_indices)
        player_hands = {0: set(), 1: set(), 2: set(), 3: set()}
        
        # We map string "Bottom", "Right", "Top", "Left" to 0, 1, 2, 3
        p_map = {"Bottom": 0, "Right": 1, "Top": 2, "Left": 3}
        
        # First pass: Collect all ownership
        all_plays = [] # (player_idx, card_token) ordered by time
        
        for trick in tricks:
            played_by_names = trick.get('playedBy', [])
            cards = trick.get('cards', [])
            
            for i, p_name in enumerate(played_by_names):
                if i >= len(cards): break
                pid = p_map.get(p_name)
                c_obj = cards[i]
                c_str = parse_card_str(c_obj)
                if pid is not None and c_str:
                    c_idx = MindVocab.card_to_index(c_str) # 0-31
                    c_token = MindVocab.get_card_token(c_str)
                    
                    if c_idx >= 0:
                        player_hands[pid].add(c_idx)
                        all_plays.append((pid, c_token))

        # 2. Build Temporal Sequences
        # At each step T, the input is History[0...T-1].
        # The Target is the contents of hands at time T.
        # Note: As cards are played, they leave the hand.
        
        history_tokens = [MindVocab.START]
        
        # Add Bidding info (simplified for now - just Bid type)
        bid = round_data.get('bid', {})
        if bid:
            b_token = MindVocab.get_bid_token(bid.get('type', 'PASS'))
            if b_token: history_tokens.append(b_token)

        # Iterate through plays matrix
        current_hands = {k: v.copy() for k,v in player_hands.items()}
        
        for pid, c_token in all_plays:
            # Snapshot State BEFORE this card is played
            # Input: history_tokens
            # Target: current_hands
            
            # Construct Target Tensor
            # Shape [4, 32]
            target = torch.zeros((4, 32))
            for p in range(4):
                for c in current_hands[p]:
                    target[p, c] = 1.0
            
            sequences.append((
                torch.tensor(history_tokens, dtype=torch.long), 
                target.clone()
            ))
            
            # Update State
            # 1. Add this play to history
            history_tokens.append(c_token)
            # 2. Remove card from hand (it's revealed, no longer hidden/held)
            # Actually, standard Mind Reader predicts REMAINING hands.
            c_idx = c_token - MindVocab.PLAY_OFFSET
            if c_idx in current_hands[pid]:
                current_hands[pid].remove(c_idx)
                
    return sequences

def main():
    print("Generating MindReader Dataset...")
    files = glob.glob("matches/*.json")
    print(f"Found {len(files)} replay files.")
    
    all_data = []
    total_samples = 0
    
    for f in files:
        try:
            seqs = process_match(f)
            all_data.extend(seqs)
            total_samples += len(seqs)
            print(f"Processed {f}: +{len(seqs)} samples")
        except Exception as e:
            print(f"Skipping {f}: {e}")
            
    print(f"Total Samples: {total_samples}")
    
    if total_samples > 0:
        torch.save(all_data, "ai_worker/data/mind_data.pt")
        print("Saved to ai_worker/data/mind_data.pt")
    else:
        print("No samples generated. Play more games.")

if __name__ == "__main__":
    main()
