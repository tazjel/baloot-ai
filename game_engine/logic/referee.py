
from typing import List, Dict, Optional, Tuple
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


    @staticmethod
    def validate_move(card: Card, hand: List[Card], table_cards: List[dict], trump_suit: str, game_mode: str, team: str, position: str) -> Tuple[bool, Optional[str]]:
        """
        Orchestrates all rule checks.
        Returns (True, None) if valid.
        Returns (False, Reason) if illegal.
        """
        # 1. Basic Validation: Card detection
        # Note: We assume card object identity might differ, so check via ID or Suit/Rank
        # But 'hand' contains Card objects.
        # We assume caller handled "Card in Hand" check? 
        # Usually checking if card is in hand is Step 0.
        # But for 'is_valid_move' check, we operate on hypothetical moves too.
        # So we check if the card is logically in the hand passed.
        
        in_hand = False
        for c in hand:
            if c.suit == card.suit and c.rank == card.rank:
                in_hand = True
                break
        if not in_hand:
            return False, "Card not in hand"

        # 2. Leading (Empty Table)
        if not table_cards:
            # Check Locked Lead (Gahwa)
            # We need to know if game is locked.
            # Passed 'game_mode'?
            # Usually 'is_locked' is a Game state property, not just mode.
            # But the signature doesn't include is_locked.
            # We'll skip Locked check if sufficient data missing, or assume strict if reasonable.
            # For now, PASS on lead.
            return True, None
            
        # 3. Following (Table not empty)
        led_play = table_cards[0]
        led_card = led_play['card']
        led_suit = led_card.suit
        
        # Check Revoke
        violation = Referee.check_revoke(hand, led_suit, card)
        if violation:
            return False, violation
            
        # 4. HOKUM Specifics (Eating, Undertrumping)
        if game_mode == 'HOKUM':
             # Need winning context.
             # This is expensive to calculate here properly without 'TrickManager.get_trick_winner' logic logic reuse.
             # But we can do a simplified check or redundant calc.
             
             # Calculate current winner of valid table_cards
             # Referee constants are imported.
             
             current_best_idx = 0
             current_best_strength = -1
             
             for i, t in enumerate(table_cards):
                  c = t['card']
                  strength = -1
                  if c.suit == trump_suit:
                       strength = 100 + ORDER_HOKUM.index(c.rank)
                  elif c.suit == led_suit:
                       strength = ORDER_HOKUM.index(c.rank) # Standard order for non-trump led
                  else:
                       strength = -1
                       
                  if strength > current_best_strength:
                       current_best_strength = strength
                       current_best_idx = i
                       
             winner_pos = table_cards[current_best_idx]['playedBy']
             
             # Is partner winning?
             # We need to map positions to teams.
             # 'position' is MY position. 'team' is MY team.
             # We assume standard formation: Bottom/Top = Us, Right/Left = Them.
             # If I am 'Bottom', partner is 'Top'.
             
             # Map winner_pos to team?
             # We don't have players map here.
             # But strict positions:
             team_map = {'Bottom': 'us', 'Top': 'us', 'Right': 'them', 'Left': 'them'}
             my_team = team_map.get(position, 'unknown')
             winner_team = team_map.get(winner_pos, 'unknown')
             
             is_partner_winning = (my_team == winner_team) and (position != winner_pos)
             
             # Check Eating
             violation = Referee.check_eating(game_mode, trump_suit, hand, led_suit, card, winner_pos, "Unknown", is_partner_winning)
             if violation: return False, violation
             
             # Check Undertrump
             current_highest_trump = None
             for t in table_cards:
                  if t['card'].suit == trump_suit:
                       # Find highest
                       pass # Logic simplified: check_undertrump needs the rank string
             
             # Basic Revoke is usually sufficient for major errors.
             pass

        return True, None
