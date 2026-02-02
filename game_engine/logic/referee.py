
from typing import List, Dict, Optional
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_HOKUM, ORDER_SUN

class Referee:
    """
    Strict Rule Enforcement for Baloot.
    Violation of these rules results in IMMEDIATE LOSS (Qayd).
    """
    
    @staticmethod
    def check_revoke(hand: List[Card], led_suit: str, played_card: Card) -> Optional[str]:
        """
        Rule: Must follow suit if possessed.
        """
        if played_card.suit == led_suit:
            return None
            
        has_suit = any(c.suit == led_suit for c in hand)
        if has_suit:
            return "QATA: Player holds Led Suit but played otherwise."
        return None

    @staticmethod
    def check_eating(game_mode: str, trump_suit: str, hand: List[Card], led_suit: str, played_card: Card, 
                    current_winner_pos: str, partner_pos: str, is_partner_winning: bool) -> Optional[str]:
        """
        Rule (Hokum): If void in led suit, MUST play trump if opponent is winning.
        "Eating" (Akl) is mandatory.
        """
        if game_mode != 'HOKUM':
            return None
            
        if played_card.suit == led_suit:
            return None # Following suit is handled by Revoke check
            
        # Player is void in led suit (assumed checked effectively by check_revoke passing or being called after)
        # But we should double check emptiness here? 
        # Actually logic: if played_card.suit != led_suit AND has_suit(led) -> Revoke.
        # So if we are here and not revoked, we assume void in led_suit (or we re-check).
        
        has_led_suit = any(c.suit == led_suit for c in hand)
        if has_led_suit:
             return None # Revoke check handles this priority.
             
        if is_partner_winning:
             return None # No need to eat if partner is winning (unless specific strict variants? standard is no)
             
        if played_card.suit == trump_suit:
             return None # Already eating (or overtrumping checked elsewhere)
             
        has_trump = any(c.suit == trump_suit for c in hand)
        if has_trump:
             return "MANDATORY_EATING: Void in Led Suit and Opponent winning -> Must Play Trump."
             
        return None

    @staticmethod
    def check_undertrump(game_mode: str, trump_suit: str, hand: List[Card], played_card: Card, 
                        current_highest_trump_rank: Optional[str], current_highest_is_partner: bool) -> Optional[str]:
        """
        Rule (Hokum): If playing a trump, must Overtrump the current highest trump if possible.
        (Undertrumping is forbidden unless you only have lower trumps).
        """
        if game_mode != 'HOKUM':
            return None
        if played_card.suit != trump_suit:
            return None
        if not current_highest_trump_rank:
            return None # I am the first trump or no trumps played yet
            
        # Get strength
        my_strength = ORDER_HOKUM.index(played_card.rank)
        highest_strength = ORDER_HOKUM.index(current_highest_trump_rank)
        
        if my_strength > highest_strength:
             # Beating! Good.
             return None
             
        # I am playing a weaker trump than current highest.
        # "Undertrumping".
        
        can_beat = False
        for c in hand:
             if c.suit == trump_suit:
                  s = ORDER_HOKUM.index(c.rank)
                  if s > highest_strength: # Stronger
                       can_beat = True
                       break
        
        if can_beat:
             return f"UNDERTRUMP: You have a trump that can beat the current high trump ({current_highest_trump_rank})."
             
        return None

    @staticmethod
    def check_locked_lead(is_locked: bool, trump_suit: str, hand: List[Card], played_card: Card) -> Optional[str]:
        """
        Rule: In Locked Game (Gahwa/Doubled), cannot lead Trump unless forced (only trumps in hand).
        """
        if not is_locked:
            return None
            
        if played_card.suit != trump_suit:
            return None
            
        # Leading Trump. Check if forced.
        has_non_trump = any(c.suit != trump_suit for c in hand)
        
        if has_non_trump:
             return "LOCKED_LEAD: Cannot lead Trump in Locked game while holding other suits."
             
        return None



    @staticmethod
    def estimate_kaboot(offending_team_has_tricks: bool, 
                       remaining_cards_by_player: Dict[str, List[Card]], 
                       players_team_map: Dict[str, str],
                       offender_team: str,
                       game_mode: str, trump_suit: str) -> bool:
        """
        Estimates if Kaboot (Slam) was likely.
        Returns True if Offending Team has NO chance of winning a trick (No Boss Cards).
        """
        if offending_team_has_tricks:
             return False # Already lost Kaboot
             
        # Gather all remaining cards
        all_remaining = []
        for h in remaining_cards_by_player.values():
             all_remaining.extend(h)
             
        if not all_remaining: return True
        
        suits = ['♠', '♥', '♦', '♣']
        
        for suit in suits:
             suit_cards = [c for c in all_remaining if c.suit == suit]
             if not suit_cards: continue
             
             is_trump = (game_mode == 'HOKUM' and suit == trump_suit)
             # Fix Order logic
             current_order = ORDER_HOKUM if is_trump else ORDER_SUN
             
             # Find Boss
             boss_card = max(suit_cards, key=lambda c: current_order.index(c.rank))
             
             # Who holds it?
             for pos, hand in remaining_cards_by_player.items():
                  if any(c.suit == boss_card.suit and c.rank == boss_card.rank for c in hand):
                       team = players_team_map.get(pos)
                       if team == offender_team:
                            return False # Offender has a Boss Card -> Can likely win a trick.
                            
        # If we reached here, Offender has NO Boss Cards in ANY suit.
        # Implies Non-Offender holds all Aces/Kings/Bosses.
        return True

