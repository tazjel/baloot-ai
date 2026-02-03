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
        
        # Reconstruct "Virtual Hand" at the moment of the crime
        # Ideally, we rewind state. But for simple verification, we check if they HAD the card.
        # Check if proof_card exists in the snapshot hand?
        # ACTUALLY: We need the FULL HAND of the suspect to verify Revoke/Eat.
        # The 'proof_card' logic was "If I show you this card, it proves I could have played it".
        # But for "omniscient" Qayd, we check the ENTIRE hand.
        
        virtual_hand_objs = []
        
        # Identify Suspect
        suspect_pos = crime_card.get('playedBy')
        suspect_player = next((p for p in game_snapshot['players'] if p['position'] == suspect_pos), None)
        
        if not suspect_player:
             # Fallback if playedBy missing?
             return {'is_guilty': False, 'reason': "Suspect not found in snapshot."}
             
        # New Logic: Use Suspect's Actual Remaining Hand + The Card They Played (Crime Card)
        # Wait, crime card was played, so it's NOT in 'hand' anymore (it's in 'tableCards' or 'lastTrick').
        # But for 'check_revoke', we need the hand AS IT WAS before the play.
        # So we take 'hand' from snapshot (remaining) AND add the 'crime_card' back?
        # Game Snapshot is TAKEN AT TIME OF ACCUSATION (After play).
        # So 'hand' does NOT have 'crime_card'.
        # We must ADD 'crime_card' back to 'hand' to simulate the state BEFORE the play?
        # No, 'check_revoke' takes 'hand' containing OTHER cards.
        # Rule: "Must follow suit if possessed". 
        # If I played 'Spades' (crime), did I have 'Hearts' (led)?
        # I check the 'remaining hand'. If 'remaining hand' has Hearts, then Guilty.
        # So 'virtual_hand' should be the 'remaining hand' from the snapshot.
        
        current_hand_dicts = suspect_player.get('hand', [])
        virtual_hand_objs = [Card(c['suit'], c['rank']) for c in current_hand_dicts]
        
        # Legacy Support: If proof_card provided, ensure it's in the hand? 
        # If UI sends null, we just trust the snapshot hand.
        
        # Create Crime Card Object
        crime_card_obj = Card(crime_card['card']['suit'], crime_card['card']['rank'])

        
        # Virtual Hand: The suspect held the proof card.
        # Referee checks if "hand" had options.
        virtual_hand = [Card(proof_card['suit'], proof_card['rank'])] if proof_card else virtual_hand_objs
        
        if led_suit and crime_card_obj.suit != led_suit and (proof_card and virtual_hand[0].suit == led_suit):
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
        # Map UI aliases to internal logic
        mapped_violation = violation_type
        if violation_type == 'TRUMP_IN_CLOSED': mapped_violation = 'LOCKED_LEAD'
        elif violation_type == 'NO_TRUMP': mapped_violation = 'EAT'
        elif violation_type == 'NO_OVERTRUMP': mapped_violation = 'UNDERTRUMP'

        if mapped_violation == 'REVOKE':
            if led_suit:
                 error_reason = Referee.check_revoke(virtual_hand, led_suit, crime_card_obj)
                 penalty = 16 if game_mode == 'HOKUM' else 26
            else:
                 error_reason = "No led suit to revoke." if not led_suit else None

        elif mapped_violation == 'EAT':
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
                  penalty = 16
             else:
                  # If Referee wouldn't flag it (e.g. not Hokum), we shouldn't either.
                  # But we call it anyway to see.
                  pass 

        elif mapped_violation == 'UNDERTRUMP':
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
             penalty = 16

        elif mapped_violation == 'LOCKED_LEAD':
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
