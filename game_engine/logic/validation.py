from typing import List, Dict, Tuple, Any
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM

def get_trick_winner_index(table_cards: List[Dict], game_mode: str, trump_suit: str = None) -> int:
    """
    Determines the index of the current winning card in the table_cards list.
    table_cards expected format: [{'card': CardObject, ...}, ...]
    """
    if not table_cards:
        return -1

    lead_card = table_cards[0]['card']
    best_idx = 0
    current_best = -1
    
    for i, play in enumerate(table_cards):
        card = play['card']
        strength = -1
        
        if game_mode == "SUN":
            if card.suit == lead_card.suit:
                try:
                    strength = ORDER_SUN.index(card.rank)
                except ValueError:
                    strength = -1 
        else:
            # HOKUM
            if card.suit == trump_suit:
                try:
                    strength = 100 + ORDER_HOKUM.index(card.rank)
                except ValueError:
                     strength = -1
            elif card.suit == lead_card.suit:
                try:
                    strength = ORDER_SUN.index(card.rank)
                except ValueError:
                    strength = -1
        
        if strength > current_best:
            current_best = strength
            best_idx = i
            
    return best_idx

def can_beat_trump_card(winning_card: Card, hand: List[Card], trump_suit: str) -> Tuple[bool, List[Card]]:
    """ Returns True if hand contains a trump higher than winning_card. """
    try:
        winning_strength = 100 + ORDER_HOKUM.index(winning_card.rank)
    except ValueError:
        return False, []

    beating_cards = []
    for c in hand:
        if c.suit == trump_suit:
             try:
                 s = 100 + ORDER_HOKUM.index(c.rank)
                 if s > winning_strength:
                      beating_cards.append(c)
             except ValueError:
                 pass
    return (len(beating_cards) > 0), beating_cards

def is_move_legal(
    card: Card, 
    hand: List[Card], 
    table_cards: List[Dict], 
    game_mode: str, 
    trump_suit: str, 
    my_team: str,
    players_team_map: Dict[str, str],
    contract_variant: str = None
) -> bool:
    """
    Pure validation logic for Baloot.
    players_team_map: Dict mapping 'position' -> 'team' ('us', 'them')
    """
    
    # 0. Check Closed Doubling Constraint (Magfool / Locked)
    if not table_cards and contract_variant == 'CLOSED' and game_mode == 'HOKUM':
        # Cannot lead Trump if I have other suits
        if card.suit == trump_suit:
            has_non_trump = any(c.suit != trump_suit for c in hand)
            if has_non_trump:
                return False

    if not table_cards:
        return True
    
    lead_play = table_cards[0]
    lead_card = lead_play['card']
    lead_suit = lead_card.suit
    
    # 1. Follow Suit (Mandatory in Sun & Hokum)
    has_suit = any(c.suit == lead_suit for c in hand)
    if has_suit:
        if card.suit != lead_suit:
            return False
            
        # If following suit in Hokum and Lead is Trump, we are good (must follow).
        # But if we can't follow suit... see below.
        if game_mode == 'HOKUM' and lead_suit == trump_suit:
             pass 
        else:
             return True

    if game_mode == 'SUN':
        return True # If can't follow suit (or followed correctly above), play anything.
    
    # --- HOKUM STRICT RULES ---
    
    # Determine Current Winner of the Trick
    winner_idx = get_trick_winner_index(table_cards, game_mode, trump_suit)
    curr_winner_play = table_cards[winner_idx]
    curr_winner_pos = curr_winner_play['playedBy']
    
    # Is partner winning?
    winner_team = players_team_map.get(curr_winner_pos)
    is_partner_winning = (winner_team == my_team)
    
    # 2. Partner Winning? -> Play Anything (unless forced to follow suit, handled above)
    if is_partner_winning:
        return True

    # 3. Enemy Winning
    # Must Trump if possible OR Must Over-Trump
    
    has_trump = any(c.suit == trump_suit for c in hand)
    
    # Case A: Void in Lead Suit (has_suit is False, because if True we handled it or fell through)
    # Wait, if has_suit is True, we returned True (line 80) OR fell through (line 78).
    # If we fell through (Hokum Trump Lead), we are following suit.
    # If Lead is Trump, we must over-trump if possible!
    
    if lead_suit == trump_suit and has_suit:
         # We are following trump. Must we beat the current winner (who is also trump)?
         can_beat, beating_cards = can_beat_trump_card(curr_winner_play['card'], hand, trump_suit)
         if can_beat:
              # Must play a beating card
              if card not in beating_cards:
                   # Tried to play a small trump when I have a bigger one?
                   # Rule: "If you can over-trump, you MUST."
                   # But wait, logic line 130 in TrickManager says:
                   # if played_strength <= winning_strength: return False
                   # effectively enforcing playing a higher card.
                   # Let's verify my can_beat logic returns ONLY beating cards.
                   
                   # But wait, what if I play a beating card?
                   # card IS in beating_cards -> Returns True (allowed).
                   
                   # What if I play a losing card?
                   # card NOT in beating_cards -> Returns False?
                   pass

              # Checking strictly:
              played_strength = 100 + ORDER_HOKUM.index(card.rank)
              winning_strength = 100 + ORDER_HOKUM.index(curr_winner_play['card'].rank)
              
              if played_strength <= winning_strength:
                   return False # Under-trumping when I could over-trump
         return True


    # Case B: Void in Lead Suit (Really void)
    if not has_suit:
        if has_trump:
            # Must play Trump
            if card.suit != trump_suit:
                return False
            
            # Must Over-Trump?
            if curr_winner_play['card'].suit == trump_suit:
                can_beat, beating_cards = can_beat_trump_card(curr_winner_play['card'], hand, trump_suit)
                if can_beat:
                     if card not in beating_cards: 
                          # Check strength manually just to be safe or rely on list check
                          played_strength = 100 + ORDER_HOKUM.index(card.rank)
                          winning_strength = 100 + ORDER_HOKUM.index(curr_winner_play['card'].rank)
                          if played_strength <= winning_strength:
                               return False
            return True

    return True
