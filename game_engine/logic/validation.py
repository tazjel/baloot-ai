from typing import List, Dict, Tuple, Any
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM
from server.logging_utils import logger

def get_trick_winner_index(table_cards: List[Dict], game_mode: str, trump_suit: str = None) -> int:
    """
    Determines the index of the current winning card in the table_cards list.
    table_cards expected format: [{'card': CardObject, ...}, ...]
    """
    if not table_cards:
        return -1

    lead_card = table_cards[0]['card']
    lead_suit = _get_suit(lead_card)
    best_idx = 0
    current_best = -1
    
    for i, play in enumerate(table_cards):
        card = play['card']
        card_suit = _get_suit(card)
        card_rank = _get_rank(card)
        strength = -1
        
        if game_mode == "SUN":
            if card_suit == lead_suit:
                try:
                    strength = ORDER_SUN.index(card_rank)
                except ValueError:
                    strength = -1 
        else:
            # HOKUM
            if card_suit == trump_suit:
                try:
                    strength = 100 + ORDER_HOKUM.index(card_rank)
                except ValueError:
                    strength = -1
            elif card_suit == lead_suit:
                try:
                    strength = ORDER_SUN.index(card_rank)
                except ValueError:
                    strength = -1
        
        if strength > current_best:
            current_best = strength
            best_idx = i
            
    return best_idx

def can_beat_trump_card(winning_card: Card, hand: List[Card], trump_suit: str) -> Tuple[bool, List[Card]]:
    """ Returns True if hand contains a trump higher than winning_card. """
    try:
        winning_strength = 100 + ORDER_HOKUM.index(_get_rank(winning_card))
    except ValueError:
        return False, []

    beating_cards = []
    for c in hand:
        if _get_suit(c) == trump_suit:
             try:
                 s = 100 + ORDER_HOKUM.index(_get_rank(c))
                 if s > winning_strength:
                      beating_cards.append(c)
             except ValueError:
                 pass
    return (len(beating_cards) > 0), beating_cards

def _get_suit(card) -> str:
    if hasattr(card, 'suit'): return card.suit
    if isinstance(card, dict): return card.get('suit')
    return None

def _get_rank(card) -> str:
    if hasattr(card, 'rank'): return card.rank
    if isinstance(card, dict): return card.get('rank')
    return None
    
def is_move_legal(
    card: Any, 
    hand: List[Any], 
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
    # DEBUG: Verbose Input Logging
    c_suit = _get_suit(card)
    # logger.info(f"VALIDATE: Card={card} (Suit={c_suit}) | Mode={game_mode} | Trump={trump_suit}")
    if table_cards:
         lead = table_cards[0]['card']
         l_suit = _get_suit(lead)
         # logger.info(f"VALIDATE: Table Lead={lead} (Suit={l_suit}) in Table len={len(table_cards)}")
    else:
         pass # logger.info("VALIDATE: Table Empty (Lead)")
         
    # 0. Check Closed Doubling Constraint (Magfool / Locked)
    if not table_cards and contract_variant == 'CLOSED' and game_mode == 'HOKUM':
        card_suit = _get_suit(card)
        if card_suit == trump_suit:
            has_non_trump = any(_get_suit(c) != trump_suit for c in hand)
            if has_non_trump:
                return False

    if not table_cards:
        return True
    
    lead_play = table_cards[0]
    lead_card = lead_play['card']
    lead_suit = _get_suit(lead_card)
    card_suit = _get_suit(card)
    
    # 1. Follow Suit (Mandatory in Sun & Hokum)
    try:
        has_suit = any(_get_suit(c) == lead_suit for c in hand)
        # DEBUG: Log Hand State for Revoke Check
        if table_cards:
             hand_suits = [_get_suit(c) for c in hand]
             # logger.info(f"VALIDATE CHECK: Lead={lead_suit} | Hand Suits={hand_suits} | HasSuit={has_suit}")
    except Exception as e:
        logger.error(f"CRITICAL ERROR in validation.py has_suit check: {e}")
        return True # Fail open to avoid crash
        
    if has_suit:
        if card_suit != lead_suit:
            # logger.info(f"VALIDATE RESULT: ILLEGAL (Revoke) - Played {card_suit} on {lead_suit}")
            return False
            
        # If following suit in Hokum and Lead is Trump, we are good (must follow).
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
    
    has_trump = any(_get_suit(c) == trump_suit for c in hand)
    
    # Case A: Void in Lead Suit
    if lead_suit == trump_suit and has_suit:
         # We are following trump. Must we beat the current winner (who is also trump)?
         can_beat, beating_cards = can_beat_trump_card(curr_winner_play['card'], hand, trump_suit)
         if can_beat:
              # Must play a beating card
              # Check safely
              # beating_cards logic relies on can_beat_trump_card which we might need to update too?
              # Let's inspect can_beat_trump_card next.
              
              if card not in beating_cards:
                   # Try manual check if object identity fails (dicts don't compare equal unless contents same)
                   pass
                   # Actually beating_cards returns list of objects from hand.
                   # If card is from hand, identity check works if usage is consistent.
                   
                   # But let's verify strength manually
                   played_rank = _get_rank(card)
                   winning_rank = _get_rank(curr_winner_play['card'])
                   
                   try:
                       played_strength = 100 + ORDER_HOKUM.index(played_rank)
                       winning_strength = 100 + ORDER_HOKUM.index(winning_rank)
                       if played_strength <= winning_strength:
                           return False 
                   except:
                       return True # Soft fail?
                       
              return True


    # Case B: Void in Lead Suit (Really void)
    if not has_suit:
        if has_trump:
            # Must play Trump
            if _get_suit(card) != trump_suit:
                return False
            
            # Must Over-Trump?
            if _get_suit(curr_winner_play['card']) == trump_suit:
                can_beat, beating_cards = can_beat_trump_card(curr_winner_play['card'], hand, trump_suit)
                if can_beat:
                     if card not in beating_cards: 
                          # Check strength manually just to be safe or rely on list check
                          played_rank = _get_rank(card)
                          winning_rank = _get_rank(curr_winner_play['card'])
                          
                          try:
                              played_strength = 100 + ORDER_HOKUM.index(played_rank)
                              winning_strength = 100 + ORDER_HOKUM.index(winning_rank)
                              if played_strength <= winning_strength:
                                   return False
                          except:
                               pass
            return True

    return True

def get_violation_details(
    card: Any, 
    hand: List[Any], 
    table_cards: List[Dict], 
    game_mode: str, 
    trump_suit: str, 
    my_team: str,
    players_team_map: Dict[str, str],
    contract_variant: str = None
) -> Dict[str, Any]:
    """
    Detailed validation that returns the reason and PROOF (if applicable).
    Used for Qayd/Forensic analysis.
    """
    # Default Result
    res = {'is_legal': True, 'violation_type': None, 'reason': None, 'proof_hint': None}

    c_suit = _get_suit(card)
    c_rank = _get_rank(card)

    # 0. Check Closed Doubling Constraint
    if not table_cards and contract_variant == 'CLOSED' and game_mode == 'HOKUM':
        if c_suit == trump_suit:
            non_trumps = [c for c in hand if _get_suit(c) != trump_suit]
            if non_trumps:
                 return {
                     'is_legal': False,
                     'violation_type': 'TRUMP_IN_DOUBLE',
                     'reason': 'Cannot lead Trump in Locked mode unless forced',
                     'proof_hint': non_trumps[0].to_dict() if hasattr(non_trumps[0], 'to_dict') else non_trumps[0]
                 }

    if not table_cards:
        return res
    
    lead_play = table_cards[0]
    lead_card = lead_play['card']
    lead_suit = _get_suit(lead_card)
    
    # 1. Follow Suit (Mandatory)
    cards_of_suit = [c for c in hand if _get_suit(c) == lead_suit]
    has_suit = len(cards_of_suit) > 0
    
    if has_suit:
        if c_suit != lead_suit:
            # Illegal unless following suit in Hokum (Trump) overrides
            if game_mode == 'HOKUM' and lead_suit == trump_suit:
                 pass 
            else:
                 return {
                     'is_legal': False, 
                     'violation_type': 'REVOKE', 
                     'reason': f"Must follow suit ({lead_suit})",
                     'proof_hint': cards_of_suit[0].to_dict() if hasattr(cards_of_suit[0], 'to_dict') else cards_of_suit[0]
                 }

    if game_mode == 'SUN':
        return res
    
    # --- HOKUM STRICT RULES ---
    
    # Determine Current Winner
    winner_idx = get_trick_winner_index(table_cards, game_mode, trump_suit)
    curr_winner_play = table_cards[winner_idx]
    curr_winner_pos = curr_winner_play['playedBy']
    
    # Is partner winning?
    winner_team = players_team_map.get(curr_winner_pos)
    is_partner_winning = (winner_team == my_team)
    
    if is_partner_winning:
        return res # Partner winning = freedom (mostly)

    # Enemy Winning
    trumps_in_hand = [c for c in hand if _get_suit(c) == trump_suit]
    has_trump = len(trumps_in_hand) > 0
    
    # Case A: Void in Lead Suit (Already checked suit follow above)
    # If lead was trump, we handled it.
    
    # Case B: Void in Lead Suit -> Must Trump
    if not has_suit:
        if has_trump:
            if c_suit != trump_suit:
                return {
                    'is_legal': False,
                    'violation_type': 'NO_TRUMP',
                    'reason': "Must trump when void in lead suit",
                    'proof_hint': trumps_in_hand[0].to_dict() if hasattr(trumps_in_hand[0], 'to_dict') else trumps_in_hand[0]
                }
            
            # Must Over-Trump?
            winning_card = curr_winner_play['card']
            if _get_suit(winning_card) == trump_suit:
                 can_beat, beating_cards = can_beat_trump_card(winning_card, hand, trump_suit)
                 if can_beat:
                      # Did we play a beating card?
                      # beating_cards contains valid options.
                      # We need to check if 'card' is one of them.
                      # Ideally check identity or value.
                      
                      played_strength = 100 + ORDER_HOKUM.index(c_rank)
                      winning_strength = 100 + ORDER_HOKUM.index(_get_rank(winning_card))
                      
                      if played_strength <= winning_strength:
                           return {
                               'is_legal': False,
                               'violation_type': 'NO_OVERTRUMP',
                               'reason': "Must over-trump current winner",
                               'proof_hint': beating_cards[0].to_dict() if hasattr(beating_cards[0], 'to_dict') else beating_cards[0]
                           }

    return res
