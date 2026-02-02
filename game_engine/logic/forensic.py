from typing import List, Dict, Optional, Tuple
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_HOKUM, ORDER_SUN
from game_engine.logic.referee import Referee

class ForensicReferee:
    """
    Handles POST-GAME or PAUSED-GAME forensic analysis.
    Delegates to Referee to ensure same logic is applied as live game.
    """

    @staticmethod
    def validate_accusation(game_snapshot: Dict, 
                            crime_card: Dict, 
                            proof_card: Dict, 
                            violation_type: str) -> Dict:
        """
        Validates if the 'proof_card' proves that 'crime_card' was illegal.
        """
        
        # 1. Locate the Trick and Context of the Crime
        trick_index = -1
        crime_trick = None
        
        for idx, trick in enumerate(game_snapshot['roundHistory']):
            for card_play in trick['cards']:
                if card_play['card']['suit'] == crime_card['suit'] and \
                   card_play['card']['rank'] == crime_card['rank'] and \
                   card_play['playedBy'] == crime_card['playedBy']:
                       trick_index = idx
                       crime_trick = trick
                       break
            if crime_trick: break
            
        if not crime_trick:
            return {'success': False, 'error': "Crime card not found in history."}

        # 2. Reconstruct State AT THAT MOMENT
        cards_before = []
        for cp in crime_trick['cards']:
            if cp['card']['suit'] == crime_card['suit'] and cp['card']['rank'] == crime_card['rank']: 
                 break 
            cards_before.append(cp)
            
        led_suit = cards_before[0]['card']['suit'] if cards_before else None
        
        game_mode = game_snapshot['gameMode']
        trump_suit = game_snapshot['trumpSuit']
        
        # Convert dicts to Objects for Referee
        crime_card_obj = Card(crime_card['suit'], crime_card['rank'])
        proof_card_obj = Card(proof_card['suit'], proof_card['rank'])
        
        # Virtual Hand: The suspect held the proof card.
        # Referee checks if "hand" had options.
        virtual_hand = [proof_card_obj]
        
        if led_suit and crime_card_obj.suit != led_suit and proof_card_obj.suit == led_suit:
             # If violation is REVOKE, we need to ensure they actually revoked.
             # The check below handles logic, but we must verify card ownership order.
             # Check if proof was played BEFORE crime?
             proof_played_idx = ForensicReferee._find_card_played_index(game_snapshot['roundHistory'], proof_card)
             crime_played_idx = trick_index # Simplified, assuming trick_index is monotonicish or we need absolute order
             
             # Actually we need absolute index of play.
             # If proof played *before*, it wasn't in hand.
             if proof_played_idx != -1 and proof_played_idx < ForensicReferee._find_card_played_index(game_snapshot['roundHistory'], crime_card):
                  return {'success': True, 'is_guilty': False, 'reason': "Proof card was played BEFORE the crime."}

        error_reason = None
        penalty = 0

        # --- DELEGATE TO REFEREE ---
        if violation_type == 'REVOKE':
            if led_suit:
                 error_reason = Referee.check_revoke(virtual_hand, led_suit, crime_card_obj)
                 penalty = 26 if game_mode == 'HOKUM' else 16
            else:
                 error_reason = "No led suit to revoke." if not led_suit else None

        elif violation_type == 'EAT':
             # Context for Eating
             if game_mode == 'HOKUM' and led_suit and led_suit != trump_suit:
                  winner_idx = ForensicReferee.get_partial_winner(cards_before, game_mode, trump_suit)
                  current_winner_pos = cards_before[winner_idx]['playedBy'] if winner_idx != -1 else None
                  
                  # Determine if partner winning
                  # Map positions to teams.
                  # This depends on players setup. Assuming Standard: Bottom/Top vs Right/Left
                  teams = {'Bottom': 'us', 'Top': 'us', 'Right': 'them', 'Left': 'them'}
                  suspect_pos = crime_card['playedBy']
                  suspect_team = teams.get(suspect_pos)
                  winner_team = teams.get(current_winner_pos) if current_winner_pos else None
                  
                  is_partner_winning = (suspect_team == winner_team) if winner_team else False
                  
                  error_reason = Referee.check_eating(game_mode, trump_suit, virtual_hand, led_suit, crime_card_obj,
                                                      current_winner_pos, None, is_partner_winning)
                  penalty = 26
             else:
                  # If Referee wouldn't flag it (e.g. not Hokum), we shouldn't either.
                  # But we call it anyway to see.
                  pass 

        elif violation_type == 'UNDERTRUMP':
             # Context
             highest_trump = None
             for cp in cards_before:
                  if cp['card']['suit'] == trump_suit:
                       # Find best.
                       # Simplified: Just pass the current highest seen?
                       # Referee expects 'current_highest_trump_rank'.
                       if highest_trump:
                            # Compare
                            if ORDER_HOKUM.index(cp['card']['rank']) > ORDER_HOKUM.index(highest_trump):
                                 highest_trump = cp['card']['rank']
                       else:
                            highest_trump = cp['card']['rank']
                            
             error_reason = Referee.check_undertrump(game_mode, trump_suit, virtual_hand, crime_card_obj,
                                                     highest_trump, False) # is_partner irrelevant for UT usually? or logic handles it
             penalty = 26

        elif violation_type == 'LOCKED_LEAD':
             is_locked = game_snapshot.get('isLocked', False) or game_snapshot.get('gameMode') == 'SUN' # Wait, Locked is Doubled.
             # check_locked_lead(is_locked, ...)
             # Need to know if game was locked.
             # game_snapshot['isLocked'] might be current state (True during Qayd).
             # We need state at time of play. 
             # Rough heuristic: check doublingLevel >= 2?
             was_locked = (game_snapshot.get('doublingLevel', 1) >= 2)
             
             # Also, check_locked_lead requires checking if they had ONLY trumps.
             # Virtual hand only has proof card.
             # If proof card is Non-Trump, and they led Trump -> Guilty.
             error_reason = Referee.check_locked_lead(was_locked, trump_suit, virtual_hand, crime_card_obj)
             penalty = 100 # usually usually game loss

        if error_reason:
             return {'success': True, 'is_guilty': True, 'reason': error_reason, 'penalty_score': penalty}
        else:
             return {'success': True, 'is_guilty': False, 'reason': "Move appears legal under strict rules."}


    @staticmethod
    def _find_card_played_index(history, card_dict):
        count = 0
        for trick in history:
             for cp in trick['cards']:
                  if cp['card']['suit'] == card_dict['suit'] and cp['card']['rank'] == card_dict['rank']:
                       return count
                  count += 1
        return -1

    @staticmethod
    def get_partial_winner(cards_played, game_mode, trump_suit):
        """Helper to find current winner of a partial trick."""
        if not cards_played: return -1
        
        lead_suit = cards_played[0]['card']['suit']
        best_idx = 0
        
        def get_strength(card):
             # 1. Trump (Hokum)
             if game_mode == 'HOKUM' and card['suit'] == trump_suit:
                  return 100 + ORDER_HOKUM.index(card['rank'])
             # 2. Lead Suit
             if card['suit'] == lead_suit:
                  return ORDER_SUN.index(card['rank'])
             return -1
             
        current_best = get_strength(cards_played[0]['card'])
        
        for i in range(1, len(cards_played)):
             s = get_strength(cards_played[i]['card'])
             if s > current_best:
                  current_best = s
                  best_idx = i
                  
        return best_idx
