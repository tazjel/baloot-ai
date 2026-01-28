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

    def get_signal_for_card(self, card, is_partner_winning, mode='SUN'):
        """
        Analyzes a discarded card to see what signal it sends.
        Advanced Tahreeb/Tanfeer Logic:
        - If Partner Winning (Tahreeb): 
             - Discard = NEGATIVE (Don't want this).
             - Implies PREFER_SAME_COLOR (Want the other suit of same color).
        - If Enemy Winning (Tanfeer):
             - Discard = POSITIVE (Encourage).
             - Ace Discard = URGENT_CALL (Barqiya).
        """
        rank = card.rank
        
        if is_partner_winning:
             # TAHREEB (Negative Signaling)
             # "Any card you discard means you don't want it."
             # Also implies "Same Color, Opposite Shape" -> PREFER_SAME_COLOR
             return SignalType.NEGATIVE_DISCARD
             
        else:
             # TANFEER (Positive Signaling)
             # "If you 'shun' (discard), it means you want the suit."
             
             # BARQIYA (The Telegraph) - Ultra High Urgency
             if rank == 'A':
                  return SignalType.URGENT_CALL
             
             # Standard Encouragement
             if rank in ['10', 'K', 'Q', 'J']: # Even J/Q can be signals in Tanfeer
                  return SignalType.ENCOURAGE
             
             # Low cards in Tanfeer?
             # Usually Tanfeer requires a "Power Card" to show strength.
             # Discarding a 7 in Tanfeer might just be trash/ducking.
             # Research: "If you 'Tanfeer,' it means you want that suit OR you have the Ace"
             # So usually high cards. 
             # Let's keep 7,8,9 as NONE or maybe weak encourage?
             # Implementation Plan said: "Enemy plays Ace (Wins). Bot discards 10s -> Encourage".
             # Bot discards 7 -> Probably just trash.
             pass
             
        return SignalType.NONE

    def analyze_directional_signal(self, discards, suit_of_interest):
        """
        Analyzes a sequence of discards (same suit) to detect Directional Signaling.
        
        Args:
            discards: List of dicts [{'rank': '7', 'suit': 'S', 'trick_idx': 1}, ...]
                      Must be sorted by trick_idx.
            suit_of_interest: The suit we are checking signals for.
            
        Returns:
            SignalType.CONFIRMED_POSITIVE (Low -> High)
            SignalType.CONFIRMED_NEGATIVE (High -> Low)
            SignalType.NONE
        """
        relevant_discards = [d for d in discards if d['suit'] == suit_of_interest]
        
        # We need at least 2 cards to form a directional signal
        if len(relevant_discards) < 2:
            return SignalType.NONE
            
        # Get the first two discards of this suit
        # Note: 'discards' list passed in should be chronological.
        d1 = relevant_discards[0]
        d2 = relevant_discards[1]
        
        # Check Ranks
        # We need a rank comparison helper. 
        # Since this is generic signaling (usually applied in Sun or Hokum indiscriminately for directional logic),
        # we'll use Sun Order (A > 10 > K...) or just simple ordering?
        # Research says: "Small to Big" means "7 then J" or "7 then 9".
        # It usually implies standard geometric size, but in Baloot "Big" usually means Power (A, 10, K).
        # Let's use the standard Sun Order indices for "Value".
        # But wait, 7 is smaller than 8? Yes.
        # A (Index 0) is Biggest. 7 (Index 7) is Smallest.
        # So "Low to High" means: Small Card (High Index) -> Big Card (Low Index).
        
        from game_engine.models.constants import ORDER_SUN
        
        try:
            val1 = ORDER_SUN.index(d1['rank']) # Lower index = Higher Power
            val2 = ORDER_SUN.index(d2['rank'])
            
            # Logic:
            # ORDER_SUN is Ascending Power (0=7, 7=A).
            # Low (Index 0) -> High (Index 7)
            # So if val1 < val2 (First card was weaker), then SIGNAL IS INCREASING POWER.
            # "Low to High" = "Small then Big" = CONFIRMED_POSITIVE.
            
            if val1 < val2:
                return SignalType.CONFIRMED_POSITIVE
                
            # Logic:
            # High (Index 7) -> Low (Index 0)
            # So if val1 > val2 (First card was stronger), then SIGNAL IS DECREASING POWER.
            # "High to Low" = "Big then Small" = CONFIRMED_NEGATIVE.
            
            if val1 > val2:
                return SignalType.CONFIRMED_NEGATIVE
                
        except ValueError:
            pass
            
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
                 # In Tanfeer, K signal means "I have A" or "I want this".
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
