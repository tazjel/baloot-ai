from game_engine.models.constants import SUITS, BiddingPhase, BidType
from ai_worker.bot_context import BotContext
import logging

logger = logging.getLogger(__name__)

class BiddingStrategy:
    def get_decision(self, ctx: BotContext):
        # 1. KAWESH CHECK (TODO: Move Kawesh logic here if needed, or keep in agent)
        # For now we assume standard bidding flow
        
        phase = ctx.bidding_phase
        if phase == BiddingPhase.DOUBLING:
             return self.get_doubling_decision(ctx)
        elif phase == BiddingPhase.VARIANT_SELECTION:
             return self.get_variant_decision(ctx)
        elif phase == BiddingPhase.GABLAK_WINDOW:
             return {"action": "PASS", "reasoning": "Bot Gablak not implemented"}

        # 2. Score Calculation
        sun_score = self.calculate_sun_strength(ctx.hand)
        
        # 3. Best Hokum Suit
        best_suit = None
        best_hokum_score = 0
        for suit in SUITS:
            score = self.calculate_hokum_strength(ctx.hand, suit)
            if score > best_hokum_score:
                best_hokum_score = score
                best_suit = suit
        
        # 4. Contextual Checks (Ashkal)
        is_left_op = (ctx.player_index == (ctx.dealer_index + 3) % 4)
        can_ashkal = (ctx.is_dealer or is_left_op) and ctx.bidding_round <= 2
        
        # 5. Decision Thresholds
        
        # Partner Awareness: If partner currently holds the bid, raise thresholds significantly
        current_bid = ctx.raw_state.get('bid')
        partner_has_proposal = False
        if current_bid:
             bidder_pos = current_bid.get('bidder')
             if bidder_pos == self._get_partner_pos_name(ctx.position):
                  partner_has_proposal = True
        
        # Position Awareness: If Dealer (Last to speak), lower thresholds slightly to avoid pass-out
        is_last_to_speak = ctx.is_dealer
        
        # Base Thresholds
        base_sun = 18
        base_hokum = 14
        base_ashkal = 20 # Implicit in logic below
        
        # Apply Personality Bias (Positive bias = Lower threshold = More Aggressive)
        sun_threshold = base_sun - ctx.personality.sun_bias
        hokum_threshold = base_hokum - ctx.personality.hokum_bias
        
        
        # Adjustments
        if partner_has_proposal:
             # Only take over partner if very strong
             sun_threshold += 6 
             hokum_threshold += 5
        elif is_last_to_speak:
             # Force Bid to prevent infinite Pass Out loops in Arena
             sun_threshold = -999 
             hokum_threshold = -999

        
        if can_ashkal:
             # Strong Project Override
             # Check for 4-of-a-kind (A, 10, K, Q)
             ranks = [c.rank for c in ctx.hand]
             has_strong_project = False
             
             # 4 Aces (400) or 4 Tens/Kings/Queens (100)
             if ranks.count('A') == 4: has_strong_project = True
             if ranks.count('10') == 4: has_strong_project = True
             if ranks.count('K') == 4: has_strong_project = True
             if ranks.count('Q') == 4: has_strong_project = True
             
             if has_strong_project:
                  if not (ctx.floor_card and ctx.floor_card.rank == 'A'): # Still respect Ace rule
                       return {"action": "ASHKAL", "reasoning": "Forced Ashkal: Strong Project"}

             if sun_score >= (sun_threshold + 2 - ctx.personality.ashkal_bias): # Normal Ashkal needs to be solid
                  if not (ctx.floor_card and ctx.floor_card.rank == 'A'):
                       return {"action": "ASHKAL", "reasoning": "Strong Sun Hand + Dealer Privilege"}
        
        # logger.info(f"Bid Logic: P{ctx.player_index} (Dealer? {is_last_to_speak}). SunScore: {sun_score} vs {sun_threshold}. Hokum: {best_hokum_score} vs {hokum_threshold}")

        if sun_score >= sun_threshold: 
            return {"action": "SUN", "reasoning": f"Strong Sun Hand (Score {sun_score})"}
            
        if best_hokum_score >= hokum_threshold and best_suit:
            # Round 1 Constraint
            if ctx.bidding_round == 1 and ctx.floor_card and best_suit != ctx.floor_card.suit:
                 if best_hokum_score >= hokum_threshold:
                      return {"action": "PASS", "reasoning": f"Waiting for Round 2 to bid {best_suit}"}
                 else:
                      pass 
            # Round 2 Constraint
            elif ctx.bidding_round == 2 and ctx.floor_card and ctx.floor_card.suit == best_suit:
                 pass 
            else:
                 return {"action": "HOKUM", "suit": best_suit, "reasoning": f"Good {best_suit} Suit (Score {best_hokum_score})"}
        
        return {"action": "PASS", "reasoning": "Hand too weak"}

    def _get_partner_pos_name(self, my_pos):
        # Map string positions? Or assuming standard Top/Bottom etc.
        # ctx.position is a label 'Bottom', 'Right', 'Top', 'Left'
        # Partner is opposite.
        pairs = {'Bottom': 'Top', 'Top': 'Bottom', 'Right': 'Left', 'Left': 'Right'}
        return pairs.get(my_pos, 'Unknown')

    def get_doubling_decision(self, ctx: BotContext):
        return {"action": "PASS", "reasoning": "Conservative Play"}

    def get_variant_decision(self, ctx: BotContext):
        # Default logic
        bid = ctx.raw_state.get('bid', {})
        trump_suit = bid.get('suit')
        if not trump_suit: return {"action": "OPEN"}
        
        trump_count = sum(1 for c in ctx.hand if c.suit == trump_suit)
        if trump_count < 3:
             return {"action": "CLOSED", "reasoning": "Weak Trumps"}
        else:
             return {"action": "OPEN", "reasoning": "Strong Trumps"}

    def calculate_sun_strength(self, hand):
        score = 0
        ranks = [c.rank for c in hand]
        suites = {}
        for c in hand:
            suites.setdefault(c.suit, []).append(c.rank)
        
        score += ranks.count('A') * 10
        score += ranks.count('10') * 5
        score += ranks.count('K') * 3
        score += ranks.count('Q') * 2
        
        if ranks.count('A') == 4: score += 20
        for r in ['K', 'Q', 'J', '10']:
             if ranks.count(r) == 4: score += 10
             
        # Length Bonus / Gap Penalty
        for s, s_ranks in suites.items():
            if len(s_ranks) > 3:
                score += (len(s_ranks) - 3) * 2
            
            if 'Q' in s_ranks and not ('K' in s_ranks or 'A' in s_ranks):
                score -= 2
            
        # Projects (Re-enabled)
        from game_engine.logic.utils import scan_hand_for_projects
        # Utils scan returns list of dicts. We need to score them.
        # Simplified scoring: 
        projects = scan_hand_for_projects(hand, 'SUN') # Assume SUN for generic project power
        if projects:
             for p in projects:
                  # p is {'type': ..., 'score': ...}
                  score += p.get('score', 0)
        
        return score

    def calculate_hokum_strength(self, hand, trump_suit):
        score = 0
        suites = {}
        for c in hand:
            suites.setdefault(c.suit, []).append(c)

        for c in hand:
            r = c.rank
            s = c.suit
            if s == trump_suit:
                if r == 'J': score += 12 
                elif r == '9': score += 10 
                elif r == 'A': score += 6
                elif r == '10': score += 5
                elif r in ['K', 'Q']: score += 2 
                else: score += 1 
            else:
                if r == 'A': score += 5
                elif r == 'K': score += 1
                
        score += sum(1 for c in hand if c.suit == trump_suit) * 2
        
        has_k = any(c.rank == 'K' and c.suit == trump_suit for c in hand)
        has_q = any(c.rank == 'Q' and c.suit == trump_suit for c in hand)
        if has_k and has_q: score += 5
        
        # Distribution
        from game_engine.models.constants import SUITS as ALL_SUITS
        for s in ALL_SUITS:
             if s == trump_suit: continue
             count = len(suites.get(s, []))
             if count == 0: score += 3
             elif count == 1: score += 1
        
        return score
