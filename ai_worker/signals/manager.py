from ai_worker.signals.definitions import SignalType, SignalStrength
from game_engine.models.constants import POINT_VALUES_SUN, POINT_VALUES_HOKUM, SUITS
import logging

logger = logging.getLogger(__name__)

class SignalManager:
    """
    Manages the emission and detection of collaborative signals.
    """
    
    def __init__(self):
        pass

    def get_signal_for_card(self, card, mode='SUN'):
        """
        Analyzes a discarded card to see what signal it sends.
        """
        rank = card.rank
        
        # High Cards = ENCOURAGE
        if rank in ['A', '10', 'K']:
            return SignalType.ENCOURAGE
        
        # Low Cards = PREFER_OPPOSITE_COLOR Signal
        if rank in ['7', '8', '9']: # J?
            return SignalType.PREFER_OPPOSITE_COLOR
            
        return SignalType.NONE

    def get_discard_signal_card(self, hand, target_suit, mode='SUN'):
        """
        Selects the best card to discard to signal ENCOURAGE for target_suit.
        """
        # Find cards of target_suit
        candidates = [c for c in hand if c.suit == target_suit]
        if not candidates:
            return None
            
        # Preference Order for Signaling "Come Here":
        # 1. Ten (10) - Classic "Call". High value but not Master (usually).
        # 2. King (K) - Strong but safer than 10.
        # 3. Queen (Q)
        # 4. Ace (A) - risky to discard Master unless we have others.
        
        # Sort candidates by suitability for signaling
        # We need a scoring function based on Rank
        
        best_c = None
        max_score = -1
        
        # Analyze Hand Strength for Signal Selection
        ranks = [c.rank for c in candidates]
        has_ace = 'A' in ranks
        has_ten = '10' in ranks
        has_king = 'K' in ranks
        
        is_solid_run = has_ace and has_ten and (has_king or 'Q' in ranks)
        
        for c in candidates:
            score = 0
            
            # SIGNAL PRIORITY SCORING
            
            # Ace (Master)
            if c.rank == 'A':
                 if is_solid_run:
                      # If we have the rest, Ace is the BEST PRO signal.
                      score = 200 
                 else:
                      # Risky to throw Ace if we don't have the rest.
                      score = 20 
                      
            # Ten (Standard Call)
            elif c.rank == '10':
                 if has_ace: score = 100 # Standard "I have Ace"
                 else: score = 50 # Strong card, but risky signal if no Ace
            
            # King
            elif c.rank == 'K': 
                 if has_ace: score = 90 # Good backup signal
                 elif has_ten and 'Q' in ranks: score = 80 # Signal sequence
                 else: score = 40
                 
            # Queen     
            elif c.rank == 'Q': score = 60
            
            # Low Cards (Opposite Color Signal)
            # They don't signal ENCOURAGE for *this* suit.
            # But the manager might be asked: "What is best card to signal X?"
            # If we want to signal X, we shouldn't return a low card of X?
            # Correct. get_discard_signal_card is for "ENCOURAGE TARGET SUIT".
            # So low cards should have score 0 here.
            else: score = 0 
            
            if score > max_score:
                max_score = score
                best_c = c
                
        if max_score > 0:
            return best_c
            
        return None

    def should_signal_encourage(self, hand, suit, mode='SUN'):
        """
        Determines if we hold a hand strong enough to warrant a signal.
        """
        # We should only signal if we have the Master (Ace) OR valid control
        # e.g. A, K... or A, 10... or K, Q, J (if Ace is gone?)
        
        cards = [c for c in hand if c.suit == suit]
        ranks = [c.rank for c in cards]
        
        has_ace = 'A' in ranks
        has_ten = '10' in ranks
        has_king = 'K' in ranks
        
        # Logic: Signal "Encourage" if we have strong control.
        
        # Scenario 1: "I have the rest" (Ace Signal)
        # Requires: Ace AND (10 AND King) OR (Ace AND 10 AND Q/J etc)
        # Basically a very strong run.
        if has_ace and has_ten and (has_king or 'Q' in ranks):
            return True
            
        # Scenario 2: "I have the Ace" (Standard Call)
        # Use 10 or King to signal.
        # Requires: Ace AND (King OR Queen OR J) to justify saving it?
        # Actually any Ace + backup is worth signaling.
        if has_ace and (has_king or has_ten or 'Q' in ranks):
            return True
            
        # Scenario 3: Sequence without Ace (K, Q, J, 10)
        # Signal to draw out the Ace?
        if has_king and 'Q' in ranks and 'J' in ranks:
             return True
            
        return False
