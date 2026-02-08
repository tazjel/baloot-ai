from typing import List, Set, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from game_engine.models.card import Card

def check_sawa_eligibility(hand: List['Card'], 
                         played_cards: Set[str], 
                         trump_suit: Optional[str], 
                         game_mode: str,
                         phase: str) -> bool:
    """
    Determines if a player holds a 'Sawa' (Grand Slam) hand.
    Sawa means the player GUARANTEES winning ALL remaining tricks.

    Logic:
    1. Player must have the lead (controlled by caller, this func just checks cards).
    2. For every suit in hand, player must hold the highest remaining cards unbroken.
    
    Args:
        hand: Player's current hand.
        played_cards: Set of card keys (e.g. 'A♠') already played.
        trump_suit: Current trump suit (if Hokum).
        game_mode: 'SUN' or 'HOKUM'.
        phase: Game phase (must be PLAYING).
        
    Returns:
        True if the hand is a guaranteed Sawa.
    """
    if not hand:
        return False
        
    # Standard Rank Orders
    ORDER_SUN = ['A', '10', 'K', 'Q', 'J', '9', '8', '7']
    ORDER_HOKUM = ['J', '9', 'A', '10', 'K', 'Q', '8', '7']
    
    # 1. Group hand by suit
    hand_by_suit = {'S': [], 'H': [], 'D': [], 'C': []}
    for card in hand:
        # Normalize suit keys just in case
        s = card.suit
        if s == '♠': s = 'S'
        elif s == '♥': s = 'H'
        elif s == '♦': s = 'D'
        elif s == '♣': s = 'C'
        
        if s in hand_by_suit:
            hand_by_suit[s].append(card)

    # 2. Check each suit in hand
    for suit_code, cards in hand_by_suit.items():
        if not cards: continue
        
        # Determine strict order for this suit
        is_trump = (game_mode == 'HOKUM' and trump_suit and _match_suit(suit_code, trump_suit))
        rank_order = ORDER_HOKUM if is_trump else ORDER_SUN
        
        # Sort our cards high-to-low
        cards_sorted = sorted(cards, key=lambda c: rank_order.index(c.rank))
        
        # 3. Verify 'Mastery' (Unbroken sequence from top)
        # The highest card we hold MUST be the highest remaining in the game.
        # And the next highest we hold must be the next highest remaining, etc.
        
        # Generate list of ALL cards higher than our lowest card
        # Actually, simpler: iterate through the rank order from the top.
        # For every rank R:
        #   If R is in played_cards -> ignore (burned).
        #   If R is in our hand -> good, continue to next our card.
        #   If R is NOT in hand and NOT played -> We assume opponent has it -> NOT SAWA.
        
        # Map suit code back to symbol for played_cards lookup
        suit_sym = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}[suit_code]
        
        # Optimization: We only need to check until we cover all cards we hold in this suit
        cards_to_match = len(cards)
        matched_count = 0
        
        for rank in rank_order:
            card_key = f"{rank}{suit_sym}"
            
            if card_key in played_cards:
                continue # Card is dead
                
            # Card is alive. Do we have it?
            has_it = any(c.rank == rank for c in cards)
            
            if has_it:
                matched_count += 1
                if matched_count == cards_to_match:
                    # We have accounted for all our cards in this suit, 
                    # and they are the top N remaining cards. Pass!
                    break
            else:
                # We don't have it, and it's not played.
                # So an opponent has a card higher than one of ours (or interlaced).
                # BUT wait! If we have [A, K] and opponent has Q, we are good.
                # The condition is: We must hold a continuous sequence of the TOP remaining cards.
                # If we encounter a live card that we DON'T hold, all our SUBSEQUENT cards lose master status.
                # Does this invalidate Sawa?
                # Yes, because if we lose control of the suit, we can't guarantee winning ALL tricks.
                # (Unless we have trumps to cut back in? Sawa usually implies winning *current* trick too).
                # Standard Definition: You must be able to play your cards top-down without being beaten.
                return False

    # 4. TRUMP CONTROL (Hokum Specific)
    # If we are in Hokum, and we have non-trump suits...
    # We must ensure opponents satisfy one of these:
    # A) Opponents have NO trumps left.
    # B) We are only playing trumps right now.
    # C) Our non-trump masters won't be cut. (Hard to prove without counting cards perfectly).
    
    # Strict Sawa Rule:
    # If I have a master Ace of Hearts, but an opponent has a Trump... do I have Sawa?
    # If it's my turn, and I have the Master Trump, I can draw their trumps first.
    # So logic:
    #   If I strictly hold the top N trumps remaining, I can flush them.
    #   THEN I can run my side suits.
    #   So the logic above (checking each suit for mastery) is actually sufficient IF:
    #   - We treat Trumps as just another suit we must master.
    #   - AND we verify we can execute the sequence.
    #   
    #   Edge Case: I have A♥ (Master) but no Trumps. Opponent has 2 Trumps.
    #   If I play A♥, they cut. Not Sawa.
    #   
    #   So: If there are outstanding Trumps in opponent hands, 
    #   WE MUST HOLD MASTERS OF TRUMP to be able to flush them.
    #   
    #   Refined Logic for Hokum:
    #   1. Count outstanding trumps held by opponents.
    #      (Count all trumps in deck - trumps played - trumps in my hand)
    #   2. If Opponents have trumps:
    #      We MUST have enough high trumps to pull them all.
    #      (This is covered by the specific suit check loop above? 
    #       If we have master trumps, we valid. If we don't, the loop returns False).
    #      
    #      BUT: What if we have A♥ (Master) and NO Trumps?
    #      The loop above says A♥ is master of Hearts -> Pass.
    #      But opponent has 7♦ (Trump). We play A♥ -> They Cut.
    #      
    #      Fix: If game_mode == HOKUM:
    #           Check if any trumps are outstanding (not played, not in our hand).
    #           If yes -> We MUST hold the Master Trump to initiate control.
    #           Actually, if we don't have ANY trumps, and they do, we can never force them out.
    #           We lose Sawa immediately.
    
    if game_mode == 'HOKUM' and trump_suit:
        # Check outstanding trumps
        trump_sym = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}[_get_suit_code(trump_suit)]
        all_trumps = [f"{r}{trump_sym}" for r in ORDER_HOKUM]
        
        outstanding_trumps = False
        for tc in all_trumps:
            if tc in played_cards: continue
            # Check if in our hand
             # Optimization: reuse the hand structure
            suit_code = _get_suit_code(trump_suit)
            if any(c.rank == tc[:-1] for c in hand_by_suit.get(suit_code, [])):
                continue
            
            outstanding_trumps = True
            break
            
        if outstanding_trumps:
            # We must be able to pull them.
            # Only possible if we have trumps ourselves?
            # Yes. If we have no trumps, we can't extract theirs. Valid Sawa denied.
            my_trumps = hand_by_suit.get(_get_suit_code(trump_suit), [])
            if not my_trumps:
                return False
                
    return True

def _get_suit_code(suit_sym):
    if suit_sym in ['♠', 'S']: return 'S'
    if suit_sym in ['♥', 'H']: return 'H'
    if suit_sym in ['♦', 'D']: return 'D'
    if suit_sym in ['♣', 'C']: return 'C'
    return suit_sym

def _match_suit(code, sym):
    return _get_suit_code(sym) == code
