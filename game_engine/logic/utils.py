from game_engine.models.constants import ORDER_PROJECTS, ORDER_SUN, ORDER_HOKUM

def sort_hand(hand, game_mode, trump_suit=None):
    """Sorts a hand of cards based on the game mode."""
    def sort_key(card):
        # Primary sort: Suit
        # Secondary sort: Rank strength
        
        # Determine Suit Order (Alternating Colors: Red, Black, Red, Black)
        # Hearts(R), Spades(B), Diamonds(R), Clubs(B)
        suit_order = {
            '♥': 0, '♠': 1, '♦': 2, '♣': 3
        }
        
        # Adjust suit order for Hokum: Trump first
        current_suit_order = suit_order[card.suit]
        if game_mode == 'HOKUM' and trump_suit and card.suit == trump_suit:
             current_suit_order = -1 # Trump always first
             
        # Determine Rank Strength
        # User feedback: "sequence are not good".
        # Current: A, K, Q, J... (Descending)
        # Proposed: 7, 8, 9, 10, J, Q, K, A (Ascending)
        # This often makes reading "runs" easier (e.g. 7-8-9 vs 9-8-7).
        
        # ORDER_PROJECTS = ['A', 'K', 'Q', 'J', '10', '9', '8', '7']
        # Top down.
        # We want Bottom Up.
        # Index of A is 0. Index of 7 is 7.
        # To get 7 first, we want smaller key for 7.
        # If we use reverse index: 7->0, A->7.
        # Or -index: A->0, 7->-7. (Descending output if sorting ascendingly? No).
        # Python sorts Low to High.
        # If we want 7 (Index 7) to be FIRST (Low), and A (Index 0) to be LAST (High).
        # We need Key(7) < Key(A).
        # CURRENT: Key(A)=0, Key(7)=7. Sort: 0..7 -> A..7. (Descending Rank).
        # NEW GOAL: 7..A.
        # We need Key(7) < Key(A).
        # Let's use negative index? Key(A)=0, Key(7)=-7. Sort: -7..0 -> 7..A.
        # Wait, -7 < 0. So 7 comes first.
        # So using NEGATIVE index of ORDER_PROJECTS gives us 7->A.
        
        strength = -ORDER_PROJECTS.index(card.rank)
        
        return (current_suit_order, strength) # Group by suit, then 7 -> A sequence
        
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

def scan_hand_for_projects(hand, game_mode):
    """
    Scans a hand to find ALL valid projects.
    Hierarchy:
    - 400 (4 Aces in Sun) - Distinct from sequences usually.
    - 100 (4 of a Kind: K, Q, J, 10).
    - Sequences (100, 50, Sira).
    
    Returns a list of dicts: [{'type': 'SIRA', 'rank': 'A', 'score': 4}, ...]
    """
    projects = []
    
    # Sort hand by rank index (A..7) for 4-kind check and Suit/Rank for sequences
    # Helper to get rank index
    ranks = [c.rank for c in hand]
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    
    # 1. Check 4-of-a-Kind (400, 100)
    # These usually DO NOT consume cards for sequences? (Standard: They are independent)
    # i.e. You can have 4 Aces (400) AND A-K-Q (Sira).
    
    # 1. Check 4-of-a-Kind (400, 100)
    for r, count in rank_counts.items():
        if count == 4:
            if r == 'A' and game_mode == 'SUN':
                # 400 Project -> 200 Abnat (Raw) -> 40 Game Points (Sun)
                projects.append({'type': 'FOUR_HUNDRED', 'rank': 'A', 'score': 200, 'cards': [c for c in hand if c.rank == 'A']})
            elif r in ['K', 'Q', 'J', '10', 'A']:
                # 100 Project -> 100 Abnat (Raw)
                t = 'HUNDRED'
                projects.append({'type': t, 'rank': r, 'score': 100, 'kind': '4KIND', 'cards': [c for c in hand if c.rank == r]})

    # 2. Check Sequences
    # Group by Suit
    suits = ['♠', '♥', '♦', '♣']
    for s in suits:
        suit_cards = sorted([c for c in hand if c.suit == s], key=lambda x: ORDER_PROJECTS.index(x.rank)) # Sort A, K, Q...
        # Check for consecutive sequences
        if not suit_cards: continue
        
        # Iterate to find longest sequences
        current_seq = [suit_cards[0]]
        
        for i in range(1, len(suit_cards)):
            prev = suit_cards[i-1]
            curr = suit_cards[i]
            idx_prev = ORDER_PROJECTS.index(prev.rank)
            idx_curr = ORDER_PROJECTS.index(curr.rank)
            
            if idx_curr == idx_prev + 1:
                current_seq.append(curr)
            else:
                # End of a sequence
                if len(current_seq) >= 3:
                     add_sequence_project(projects, current_seq, game_mode)
                current_seq = [curr]
        
        # Check last seq
        if len(current_seq) >= 3:
            add_sequence_project(projects, current_seq, game_mode)
            
    return projects

def validate_project(hand, type_req, game_mode, trump_suit=None):
    # Refactored to use scan_hand
    # This function is now mostly a verificator for specific request?
    # Or legacy. If frontend asks "Declare SIRA", we check if ANY Sira exists.
    
    all_projects = scan_hand_for_projects(hand, game_mode)
    
    # Filter by requested type
    matches = [p for p in all_projects if p['type'] == type_req]
    
    if matches:
        # Return the best one? Or just the first valid one?
        # Typically we declare the BEST one.
        # But if user has two Siras, does he declare Sira once or twice?
        # Usually button just says "Sira". We register ALL Siras?
        # Return the 'best' match for scoring validation
        best = matches[0] # They are usually sorted or processing order
        return {'valid': True, 'score': best['score'], 'rank': best['rank'], 'type': best['type'], 'matches': matches}
    
    # Special Case: Baloot
    if type_req == 'BALOOT' and game_mode == 'HOKUM' and trump_suit:
        has_king = any(c.rank == 'K' and c.suit == trump_suit for c in hand)
        has_queen = any(c.rank == 'Q' and c.suit == trump_suit for c in hand)
        if has_king and has_queen:
             return {'valid': True, 'score': 20, 'rank': 'K', 'type': 'BALOOT'}
             
    return {'valid': False}

def get_project_rank_order(rank_char):
    """Helper to get rank order for comparison (A > K > Q...). Lower index is better."""
    return ORDER_PROJECTS.index(rank_char)

def compare_projects(p1, p2, game_mode, dealer_index, p1_index, p2_index):
    """
    Compare two projects to decide which is stronger.
    Returns:
       1 if p1 > p2
      -1 if p2 > p1
       0 if p1 == p2 (Strict tie in value/rank)
       
    Hierarchy:
    1. Score (Type Strength): 400 > 100 (Seq 5 or 4Kind) > 50 > Sira
       - Note: 4Kind 100 vs Seq 5 100? Usually 4Kind > Seq. Or score counts?
       - Standard Baloot: 400 > 100 > 50 > Sira.
       - If scores equal (e.g. both 100), check type?
       - Usually 4Kind beats Sequence of same score? Or just Rank?
       - Let's use Score First.
    
    2. Rank Strength: A > K > Q...
    
    3. Position (Distance from Dealer): Handled OUTSIDE or passed in indices?
       Passed indices to help break tie here or return 0 and handle outside.
       Let's handle purely Value/Rank here.
    """
    
    # Priority Scores dict
    # 400 > 100 > 50 > Sira (Sira=Score 4 or 2)
    # Map types to abstract strength levels if scores effectively same?
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
    
    # Strict Tie in Value and Rank.
    # Winner is one closer to Dealer (Who played first).
    # Turn Order: D+1, D+2, D+3, D.
    # Dist = (PlayerIndex - (DealerIndex + 1)) % 4. Lower is better.
    
    d1 = (p1_index - (dealer_index + 1)) % 4
    d2 = (p2_index - (dealer_index + 1)) % 4
    
    if d1 < d2: return 1
    else: return -1 # d2 < d1 or equal (impossible if indices distinct)

def is_kawesh_hand(hand):
    """
    Checks if a hand qualifies for 'Kawesh' (No court cards: A, K, Q, J, 10).
    Hand must be devoid of these ranks.
    """
    court_ranks = ['A', 'K', 'Q', 'J', '10']
    for card in hand:
         if card.rank in court_ranks:
              return False
    return True
