
import sys
import os

# Mock classes
class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
    def __repr__(self):
        return f"{self.rank}{self.suit}"

# Constants from game_logic.py
ORDER_PROJECTS = ['A', 'K', 'Q', 'J', '10', '9', '8', '7']

def scan_hand_for_projects(hand, game_mode):
    projects = []
    ranks = [c.rank for c in hand]
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    
    # 1. 4 of a kind
    for r, count in rank_counts.items():
        if count == 4:
            if r == 'A' and game_mode == 'SUN':
                projects.append({'type': 'FOUR_HUNDRED', 'rank': 'A', 'score': 40})
            elif r in ['K', 'Q', 'J', '10', 'A']:
                score = 20 if game_mode == 'SUN' else 10
                t = 'HUNDRED'
                if r == 'A' and game_mode != 'SUN': t = 'HUNDRED'
                projects.append({'type': t, 'rank': r, 'score': score})

    # 2. Sequences
    suits = ['♠', '♥', '♦', '♣']
    for s in suits:
        suit_cards = sorted([c for c in hand if c.suit == s], key=lambda x: ORDER_PROJECTS.index(x.rank))
        if not suit_cards: continue
        
        current_seq = [suit_cards[0]]
        for i in range(1, len(suit_cards)):
            prev = suit_cards[i-1]
            curr = suit_cards[i]
            idx_prev = ORDER_PROJECTS.index(prev.rank)
            idx_curr = ORDER_PROJECTS.index(curr.rank)
            
            if idx_curr == idx_prev + 1:
                current_seq.append(curr)
            else:
                if len(current_seq) >= 3:
                    add_sequence_project(projects, current_seq, game_mode)
                current_seq = [curr]
        
        if len(current_seq) >= 3:
            add_sequence_project(projects, current_seq, game_mode)
            
    return projects

def add_sequence_project(projects_list, cards, game_mode):
    length = len(cards)
    high_rank = cards[0].rank
    if length >= 5:
        score = 20 if game_mode == 'SUN' else 10
        projects_list.append({'type': 'HUNDRED', 'rank': high_rank, 'score': score})
    elif length == 4:
        score = 10 if game_mode == 'SUN' else 5
        projects_list.append({'type': 'FIFTY', 'rank': high_rank, 'score': score})
    elif length == 3:
        score = 4 if game_mode == 'SUN' else 2
        projects_list.append({'type': 'SIRA', 'rank': high_rank, 'score': score})

# Test Case
hand = [
    Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), # Sira Spades
    Card('♥', '10'), Card('♥', '9'), Card('♥', '8'), # Sira Hearts
    Card('♦', '7'), Card('♦', '8') 
]

print("Test Hand:", hand)
projs = scan_hand_for_projects(hand, "SUN")
print("Projects Found:", projs)
