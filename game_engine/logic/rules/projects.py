from typing import List, Dict, Any, Optional
from game_engine.models.constants import ORDER_PROJECTS, POINT_VALUES_HOKUM, POINT_VALUES_SUN, ORDER_SUN, ORDER_HOKUM

def sort_hand(hand, game_mode, trump_suit=None):
    """Sorts a hand of cards based on the game mode."""
    def sort_key(card):
        # Primary sort: Suit (Hearts(R), Spades(B), Diamonds(R), Clubs(B))
        suit_order = {'♥': 0, '♠': 1, '♦': 2, '♣': 3}
        current_suit_order = suit_order[card.suit]
        if game_mode == 'HOKUM' and trump_suit and card.suit == trump_suit:
             current_suit_order = -1 # Trump always first
             
        # Secondary sort: Rank strength
        # Using negative index of ORDER_PROJECTS ensures 7 -> A ordering
        strength = -ORDER_PROJECTS.index(card.rank)
        return (current_suit_order, strength)
        
    return sorted(hand, key=sort_key)

def add_sequence_project(projects_list, cards, game_mode):
    length = len(cards)
    high_rank = cards[0].rank # First is highest because sorted by ORDER_PROJECTS (A..7)
    
    if length >= 5: # 100 -> 100 Abnat
        projects_list.append({'type': 'HUNDRED', 'rank': high_rank, 'score': 100, 'kind': 'SEQ', 'cards': cards})
    elif length == 4: # 50 -> 50 Abnat
        projects_list.append({'type': 'FIFTY', 'rank': high_rank, 'score': 50, 'kind': 'SEQ', 'cards': cards})
    elif length == 3: # Sira -> 20 Abnat
        projects_list.append({'type': 'SIRA', 'rank': high_rank, 'score': 20, 'kind': 'SEQ', 'cards': cards})

def check_project_eligibility(hand: List[Any], game_mode: str) -> List[Dict[str, Any]]:
    """
    Scans a hand to find ALL valid projects.
    Pure function replacement for scan_hand_for_projects.
    """
    projects = []
    
    # Sort hand by rank index (A..7) for 4-kind check and Suit/Rank for sequences
    ranks = [c.rank for c in hand]
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    
    # 1. Check 4-of-a-Kind (400, 100)
    for r, count in rank_counts.items():
        if count == 4:
            if r == 'A' and game_mode == 'SUN':
                # 400 Project -> 200 Abnat (Raw) -> 40 Game Points (Sun)
                projects.append({'type': 'FOUR_HUNDRED', 'rank': 'A', 'score': 200, 'cards': [c for c in hand if c.rank == 'A']})
            elif r in ['K', 'Q', 'J', '10', 'A']: # 100 Project
                t = 'HUNDRED'
                projects.append({'type': t, 'rank': r, 'score': 100, 'kind': '4KIND', 'cards': [c for c in hand if c.rank == r]})

    # 2. Check Sequences
    suits = ['♠', '♥', '♦', '♣']
    for s in suits:
        # Sort A, K, Q...
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

def get_project_rank_order(rank_char):
    """Helper to get rank order for comparison (A > K > Q...). Lower index is better."""
    return ORDER_PROJECTS.index(rank_char)

def compare_projects(p1, p2, game_mode, dealer_index, p1_index, p2_index):
    """
    Compare two projects to decide which is stronger.
    Returns: 1 if p1 > p2, -1 if p2 > p1, 0 if strict tie logic fails (should not happen with position check).
    """
    def get_tier(p):
        t = p['type']
        if t == 'FOUR_HUNDRED': return 4
        if t == 'HUNDRED': return 3
        if t == 'FIFTY': return 2
        if t == 'SIRA': return 1
        return 0

    tier1 = get_tier(p1)
    tier2 = get_tier(p2)
    
    if tier1 > tier2: return 1
    if tier2 > tier1: return -1
    
    # Same Tier. Compare Rank.
    r1 = get_project_rank_order(p1['rank']) # Lower is better (0=Ace)
    r2 = get_project_rank_order(p2['rank'])
    
    if r1 < r2: return 1 # p1 has better rank (lower index)
    if r2 < r1: return -1
    
    # Strict Tie in Value and Rank -> Position wins.
    # Dist = (PlayerIndex - (DealerIndex + 1)) % 4. Lower is better/closer.
    d1 = (p1_index - (dealer_index + 1)) % 4
    d2 = (p2_index - (dealer_index + 1)) % 4
    
    if d1 < d2: return 1
    else: return -1

def is_kawesh_hand(hand):
    """
    Checks if a hand qualifies for 'Kawesh' (No court cards: A, K, Q, J, 10).
    Hand must be devoid of these ranks.
    """
    if not hand:
        return False
    court_ranks = {'A', 'K', 'Q', 'J', '10'}
    for card in hand:
        rank = getattr(card, 'rank', None)
        if rank is None and isinstance(card, dict):
            rank = card.get('rank')
        if rank in court_ranks:
            return False
    return True
