from typing import List, Dict, Optional, Tuple
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_HOKUM, ORDER_SUN
from game_engine.logic.referee import Referee

class ForensicReferee:
    """
    Handles POST-GAME or PAUSED-GAME forensic analysis.
    Used for 'Qayd' challenges where players accuse specific moves.
    """

    @staticmethod
    def validate_accusation(game_snapshot: Dict, 
                            crime_card: Dict, 
                            proof_card: Dict, 
                            violation_type: str) -> Dict:
        """
        Validates if the 'proof_card' proves that 'crime_card' was illegal.
        
        Args:
            game_snapshot: The full game state history.
            crime_card: The card played (The illegal move).
            proof_card: The card that proves the illegality (e.g. held suit).
            violation_type: 'REVOKE', 'EAT', 'UNDERTRUMP', 'LOCKED_LEAD'
            
        Returns:
             { 'success': bool, 'is_guilty': bool, 'reason': str, 'penalty_score': int }
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
        # We need: Led Suit, Winning Card, Winning Team, Trump Suit
        
        # Get cards played BEFORE the crime in that trick
        cards_before = []
        for cp in crime_trick['cards']:
            if cp['card'] == crime_card: break # reached crime
            cards_before.append(cp)
            
        led_suit = cards_before[0]['card']['suit'] if cards_before else None
        
        # Determine strict game context
        game_mode = game_snapshot['gameMode']
        trump_suit = game_snapshot['trumpSuit']
        
        # 3. Validate based on Type
        reason = ""
        is_guilty = False
        
        # --- REVOKE VALIDATION ---
        if violation_type == 'REVOKE':
            # Proof must be:
            # a) In the SAME HAND as the criminal player
            # b) Have the SAME SUIT as the LED SUIT
            # c) The CRIME card must NOT match the LED SUIT
            
            if not led_suit:
                return {'success': True, 'is_guilty': False, 'reason': "No led suit (First card). Cannot revoke."}
                
            if crime_card['suit'] == led_suit:
                return {'success': True, 'is_guilty': False, 'reason': "Crime card followed suit. No revoke."}
                
            if proof_card['suit'] != led_suit:
                return {'success': True, 'is_guilty': False, 'reason': f"Proof card ({proof_card['suit']}) is not loop suit ({led_suit})."}
                
            # Crucially: Did they hold the proof card AT THAT MOMENT?
            # We assume the proof_card is currently in their hand or played LATER.
            # If played EARLIER, it doesn't prove anything.
            
            proof_played_trick_index = -1
            # Check if proof was played
            for idx, trick in enumerate(game_snapshot['roundHistory']):
                for cp in trick['cards']:
                     if cp['card']['suit'] == proof_card['suit'] and cp['card']['rank'] == proof_card['rank']:
                         proof_played_trick_index = idx
                         break
            
            # If proof played earlier -> INVALID
            if proof_played_trick_index != -1 and proof_played_trick_index < trick_index:
                 return {'success': True, 'is_guilty': False, 'reason': "Proof card was played BEFORE the crime."}
                 
            # Valid Revoke
            return {'success': True, 'is_guilty': True, 
                    'reason': f"REVOKE PROVEN: Player held {proof_card['suit']} but played {crime_card['suit']}.",
                    'penalty_score': 26 if game_mode == 'HOKUM' else 16} # Simplified scoring

        # --- EAT (CUT) VALIDATION ---
        elif violation_type == 'EAT':
             # Rules (Hokum):
             # 1. Led Suit is NOT Trump (handled by Revoke otherwise).
             # 2. Player is VOID in Led Suit.
             # 3. OPPONENT is currently winning the trick.
             # 4. Player HOLDS a Trump (The Proof).
             # 5. Player played NON-Trump (The Crime).
             
             if game_mode != 'HOKUM':
                  return {'success': True, 'is_guilty': False, 'reason': "Eating rule applies only to Hokum."}
                  
             if not led_suit or led_suit == trump_suit:
                  return {'success': True, 'is_guilty': False, 'reason': "Led suit was Trump or None. Cannot compel Eat."}
                  
             if crime_card['suit'] == led_suit:
                  return {'success': True, 'is_guilty': False, 'reason': "Player followed suit. No need to Eat."}
                  
             if crime_card['suit'] == trump_suit:
                  return {'success': True, 'is_guilty': False, 'reason': "Player DID Eat (Played Trump)."}
                  
             # Check if Proof is a Trump
             if proof_card['suit'] != trump_suit:
                  return {'success': True, 'is_guilty': False, 'reason': "Proof card is NOT a Trump. Cannot prove failure to Eat."}
                  
             # THE CRITICAL CONTEXT: Was Opponent Winning?
             # We need to calculate the winner of the PARTIAL trick (cards_before)
             winner_idx = ForensicReferee.get_partial_winner(cards_before, game_mode, trump_suit)
             if winner_idx == -1: # No cards before -> I am leading -> Cannot Eat
                  return {'success': True, 'is_guilty': False, 'reason': "Player led the trick."}
                  
             # Check Team
             winning_play = cards_before[winner_idx]
             winner_pos = winning_play['playedBy']
             
             # Need Player Teams from game_snapshot
             # For now, simple logic: Bottom/Top vs Left/Right
             def get_team(pos): return 'US' if pos in ['Bottom', 'Top'] else 'THEM'
             
             criminal_team = get_team(crime_card['playedBy'])
             winner_team = get_team(winner_pos)
             
             if criminal_team == winner_team:
                  return {'success': True, 'is_guilty': False, 'reason': "Partner was winning. Not forced to Eat."}
                  
             # GUILTY
             return {'success': True, 'is_guilty': True, 'reason': "FAILURE TO EAT: Opponent winning, void in led suit, held Trump but discarded.", 'penalty_score': 26}


        # --- UNDERTRUMP VALIDATION ---
        elif violation_type == 'UNDERTRUMP':
             # Rules (Hokum):
             # 1. Trump Led (or Trump played earlier).
             # 2. Player PLAYS a Trump (The Crime).
             # 3. Crime Trump is LOWER than current highest Trump.
             # 4. Player HOLDS a HIGHER Trump (The Proof).
             
             if game_mode != 'HOKUM':
                  return {'success': True, 'is_guilty': False, 'reason': "Undertrump rule applies only to Hokum."}
                  
             if crime_card['suit'] != trump_suit:
                  return {'success': True, 'is_guilty': False, 'reason': "Crime card is not a Trump."}
                  
             if proof_card['suit'] != trump_suit:
                  return {'success': True, 'is_guilty': False, 'reason': "Proof card is not a Trump."}

             # Check History for current Highest Trump
             highest_trump_rank = None
             for cp in cards_before:
                  c = cp['card']
                  if c['suit'] == trump_suit:
                       if not highest_trump_rank:
                            highest_trump_rank = c['rank']
                       else:
                            s_curr = ORDER_HOKUM.index(c['rank'])
                            s_high = ORDER_HOKUM.index(highest_trump_rank)
                            if s_curr > s_high: # Higher index = stronger in ORDER_HOKUM? Check constants.
                                # Wait, typically index 7 (J) is strongest. So higher index is stronger.
                                highest_trump_rank = c['rank']
                                
             # Wait, typical Baloot ORDER: 7,8,Q,K,10,A,9,J. Index 0 is weak, Index 7 is strong.
             # Correct.
             
             if not highest_trump_rank: 
                  # No trumps played before me. I cannot undertrump nothing.
                  # (Unless led trump and held higher? No, if led trump, I just follow. Undertrump applies when BEATING.)
                  return {'success': True, 'is_guilty': False, 'reason': "No previous trumps to undertrump."}
                  
             crime_strength = ORDER_HOKUM.index(crime_card['rank'])
             highest_strength = ORDER_HOKUM.index(highest_trump_rank)
             proof_strength = ORDER_HOKUM.index(proof_card['rank'])
             
             if crime_strength > highest_strength:
                  return {'success': True, 'is_guilty': False, 'reason': "Player Overtrumped (Beat the high card). Legal."}
                  
             # Crime < Highest. Undertrumping.
             # Did they define the Proof?
             if proof_strength > highest_strength:
                  return {'success': True, 'is_guilty': True, 'reason': f"UNDERTRUMP: Held {proof_card['rank']} (Stronger) but played {crime_card['rank']} (Weaker).", 'penalty_score': 26}
             
             return {'success': True, 'is_guilty': False, 'reason': "Proof card also weaker than current high. Forced undertrump."}

        return {'success': True, 'is_guilty': False, 'reason': "Invalid Violation Type."}

    @staticmethod
    def get_partial_winner(cards_played, game_mode, trump_suit):
        """Helper to find current winner of a partial trick."""
        if not cards_played: return -1
        
        lead_suit = cards_played[0]['card']['suit']
        best_idx = 0
        
        # Simple Winner Logic (Duplicated from TrickManager but lightweight)
        # Using indices from imported constants
        
        def get_strength(card):
             # 1. Trump (Hokum)
             if game_mode == 'HOKUM' and card['suit'] == trump_suit:
                  return 100 + ORDER_HOKUM.index(card['rank'])
             # 2. Lead Suit
             if card['suit'] == lead_suit:
                  return ORDER_SUN.index(card['rank']) # Uses Sun order even in Hokum for non-trump
             return -1
             
        current_best = get_strength(cards_played[0]['card'])
        
        for i in range(1, len(cards_played)):
             s = get_strength(cards_played[i]['card'])
             if s > current_best:
                  current_best = s
                  best_idx = i
                  
        return best_idx
