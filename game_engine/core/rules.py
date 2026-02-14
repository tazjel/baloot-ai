from typing import List, Optional, Dict, Any
from game_engine.models.card import Card
from game_engine.models.constants import SUITS, RANKS, ORDER_SUN, ORDER_HOKUM, GamePhase

def is_valid_move(
    card: Card, 
    hand: List[Card], 
    table_cards: List[Dict[str, Any]], 
    game_mode: str, 
    trump_suit: Optional[str],
    current_player_position: str,
    strict_mode: bool = False
) -> bool:
    """
    Pure function to validate a move.
    
    Args:
        card: The card being played.
        hand: The player's current hand.
        table_cards: List of cards already played in the trick (ordered).
                     Expected format: [{'card': Card, 'playedBy': str}, ...]
        game_mode: 'SUN' or 'HOKUM'.
        trump_suit: The trump suit (if HOKUM).
        current_player_position: Position of the player.
        strict_mode: Enforce strict Baloot rules (Liar's Protocol).
        
    Returns:
        bool: True if valid, False otherwise.
    """
    
    # 1. First player can play anything
    if not table_cards:
        return True
        
    led_card_dict = table_cards[0]['card']
    # Handle dict vs object
    led_card = led_card_dict if hasattr(led_card_dict, 'suit') else Card(led_card_dict['suit'], led_card_dict['rank'])
    
    led_suit = led_card.suit
    
    # Check if player has the led suit
    has_led_suit = any(c.suit == led_suit for c in hand)
    
    # --- SUN MODE RULES ---
    if game_mode == 'SUN':
        # Must follow suit if possible
        if has_led_suit and card.suit != led_suit:
            return False
            
        # If void in led suit, can play anything
        return True

    # --- HOKUM MODE RULES (Trump) ---
    elif game_mode == 'HOKUM':
        assert trump_suit is not None
        
        # Scenario A: Leading Trump
        if led_suit == trump_suit:
            # Must follow suit (trump)
            if has_led_suit:
                if card.suit != trump_suit:
                    return False
                    
                # Must beat current highest trump if possible (Ekl)
                current_winner_card = _get_current_winner_card(table_cards, game_mode, trump_suit)
                if current_winner_card and current_winner_card.suit == trump_suit:
                     can_beat = _can_beat_trump(hand, current_winner_card)
                     if can_beat:
                          # If passing up is possible, did they?
                          if _compare_cards(card, current_winner_card, game_mode, trump_suit) <= 0:
                               return False # Failed to beat
                return True
            else:
                # Void in trump: Can play anything
                return True

        # Scenario B: Leading Non-Trump
        else:
            # Must follow suit if possible
            if has_led_suit:
                if card.suit != led_suit:
                     return False
                return True
            
            # Void in led suit -> Must Trump (Ekl/Dug)
            # UNLESS partner is winning
            current_winner_pos = _get_current_winner_pos(table_cards, game_mode, trump_suit)
            # Parse teams manually (Bottom/Top vs Right/Left)
            us_positions = ['Bottom', 'Top']
            them_positions = ['Right', 'Left']
            
            my_team = 'us' if current_player_position in us_positions else 'them'
            winner_team = 'us' if current_winner_pos in us_positions else 'them'
            
            partner_winning = (my_team == winner_team)
            
            has_trump = any(c.suit == trump_suit for c in hand)
            
            if has_trump:
                # If partner is winning, you don't HAVE to trump (unless strict rule variations?)
                # Standard Baloot: You usually save trump if partner winning on non-trump trick.
                if partner_winning:
                     # Can play anything (usually waste)
                     return True
                else:
                     # Must Trump if possible
                     if card.suit != trump_suit:
                          return False
                     
                     # Must Over-Trump if previous player trumped?
                     # (Complex logic omitted for brevity in Phase 1, but this is the slot for it)
                     return True
            else:
                # Void in Led Suit AND Void in Trump -> Play anything
                return True

    return True

def _get_current_winner_card(table_cards, game_mode, trump_suit) -> Optional[Card]:
    """Find the currently winning card on the table.

    Evaluates all played cards considering suit-following and trump rules.
    Returns the Card object that is currently winning the trick.
    """
    if not table_cards:
        return None

    order = ORDER_HOKUM if game_mode == 'HOKUM' else ORDER_SUN
    led_card_dict = table_cards[0]['card']
    led_card = led_card_dict if hasattr(led_card_dict, 'suit') else Card(led_card_dict['suit'], led_card_dict['rank'])
    led_suit = led_card.suit

    best_card = led_card
    for tc in table_cards[1:]:
        cd = tc['card']
        c = cd if hasattr(cd, 'suit') else Card(cd['suit'], cd['rank'])

        c_is_trump = (trump_suit and c.suit == trump_suit)
        best_is_trump = (trump_suit and best_card.suit == trump_suit)

        if c_is_trump and not best_is_trump:
            best_card = c
        elif c_is_trump and best_is_trump:
            if order.index(c.rank) > order.index(best_card.rank):
                best_card = c
        elif not c_is_trump and not best_is_trump and c.suit == best_card.suit:
            if order.index(c.rank) > order.index(best_card.rank):
                best_card = c

    return best_card


def _get_current_winner_pos(table_cards, game_mode, trump_suit) -> str:
    """Find the position of the player currently winning the trick."""
    if not table_cards:
        return "Bottom"

    order = ORDER_HOKUM if game_mode == 'HOKUM' else ORDER_SUN
    led_card_dict = table_cards[0]['card']
    led_card = led_card_dict if hasattr(led_card_dict, 'suit') else Card(led_card_dict['suit'], led_card_dict['rank'])

    best_idx = 0
    best_card = led_card
    for i, tc in enumerate(table_cards[1:], start=1):
        cd = tc['card']
        c = cd if hasattr(cd, 'suit') else Card(cd['suit'], cd['rank'])

        c_is_trump = (trump_suit and c.suit == trump_suit)
        best_is_trump = (trump_suit and best_card.suit == trump_suit)

        if c_is_trump and not best_is_trump:
            best_card = c
            best_idx = i
        elif c_is_trump and best_is_trump:
            if order.index(c.rank) > order.index(best_card.rank):
                best_card = c
                best_idx = i
        elif not c_is_trump and not best_is_trump and c.suit == best_card.suit:
            if order.index(c.rank) > order.index(best_card.rank):
                best_card = c
                best_idx = i

    return table_cards[best_idx].get('playedBy', 'Bottom')


def _can_beat_trump(hand: List[Card], target_card: Card) -> bool:
    """Check if the hand contains a trump card that beats the target trump card."""
    trump_cards = [c for c in hand if c.suit == target_card.suit]
    if not trump_cards:
        return False
    for c in trump_cards:
        if ORDER_HOKUM.index(c.rank) > ORDER_HOKUM.index(target_card.rank):
            return True
    return False


def _compare_cards(c1: Card, c2: Card, mode: str, trump: str) -> int:
    """Compare two cards in the same suit.

    Returns:
        > 0 if c1 beats c2
        < 0 if c2 beats c1
        0 if equal (shouldn't happen with unique cards)
    """
    order = ORDER_HOKUM if mode == 'HOKUM' else ORDER_SUN
    # If different suits, trump always wins
    if c1.suit != c2.suit:
        if trump and c1.suit == trump:
            return 1
        if trump and c2.suit == trump:
            return -1
        return 0  # Off-suit vs off-suit — led suit matters (handled by caller)
    # Same suit — compare by rank order
    return order.index(c1.rank) - order.index(c2.rank)
