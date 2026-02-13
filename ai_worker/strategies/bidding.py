from game_engine.models.constants import SUITS, BiddingPhase, BidType, ORDER_SUN, ORDER_HOKUM
from ai_worker.bot_context import BotContext
from ai_worker.strategies.components.sun_bidding import (
    calculate_sun_strength,
    detect_sun_premium_pattern,
    evaluate_sun_doubling
)
from ai_worker.strategies.components.hokum_bidding import (
    calculate_hokum_strength,
    detect_hokum_premium_pattern,
    evaluate_hokum_doubling
)
from ai_worker.strategies.components.score_pressure import (
    get_score_pressure, should_gamble
)
from ai_worker.strategies.components.trick_projection import project_tricks
from ai_worker.strategies.components.hand_shape import evaluate_shape
import logging

logger = logging.getLogger(__name__)

class BiddingStrategy:
    def get_decision(self, ctx: BotContext):
        # 1. Phase Dispatch
        phase = ctx.bidding_phase
        if phase == BiddingPhase.DOUBLING:
             return self.get_doubling_decision(ctx)
        elif phase == BiddingPhase.VARIANT_SELECTION:
             return self.get_variant_decision(ctx)
        elif phase == BiddingPhase.GABLAK_WINDOW:
             return self._get_gablak_decision(ctx)

        # 2. Floor-Card-Aware Hand Pattern Recognition
        # Check combined hand (5 cards + floor card) for premium patterns
        # When dealer: only use Hokum patterns here — Sun patterns should 
        # flow through the ASHKAL check below (ASHKAL > SUN for dealer)
        pattern = self._detect_premium_pattern(ctx)
        if pattern:
            if not ctx.is_dealer or pattern.get('action') == 'HOKUM':
                return pattern

        # 3. Score Calculation
        sun_score = calculate_sun_strength(ctx.hand)
        
        # 4. Best Hokum Suit (with Ace Trap protection)
        best_suit = None
        best_hokum_score = 0
        for suit in SUITS:
            # Round 1 Constraint: Only allow floor suit for Hokum
            if ctx.bidding_round == 1 and ctx.floor_card and suit != ctx.floor_card.suit:
                continue
                
            # Round 2 Constraint: Cannot bid floor suit
            if ctx.bidding_round == 2 and ctx.floor_card and suit == ctx.floor_card.suit:
                continue

            # ACE TRAP LOGIC: Never buy a floor Ace in Hokum unless we hold J or 9
            # The Ace is only 3rd strongest in Hokum (J > 9 > A) — it gets trapped
            if ctx.floor_card and ctx.floor_card.suit == suit and ctx.floor_card.rank == 'A':
                hand_trump_ranks = [c.rank for c in ctx.hand if c.suit == suit]
                if 'J' not in hand_trump_ranks and '9' not in hand_trump_ranks:
                    logger.info(f"[BIDDING] Ace Trap: Skipping {suit} — floor Ace without J or 9")
                    continue
                
            score = calculate_hokum_strength(ctx.hand, suit)
            if score > best_hokum_score:
                best_hokum_score = score
                best_suit = suit
        
        # 3b. Trick Projection — expected tricks for logging & confidence
        sun_proj = project_tricks(ctx.hand, 'SUN')
        hokum_proj = project_tricks(ctx.hand, 'HOKUM', best_suit) if best_suit else None
        sun_et = sun_proj['expected_tricks']
        hokum_et = hokum_proj['expected_tricks'] if hokum_proj else 0
        logger.debug(f"[BIDDING] Trick projection: SUN ET={sun_et} | HOKUM({best_suit}) ET={hokum_et}")

        # 3c. Hand Shape Analysis — distribution adjustments
        try:
            shape = evaluate_shape(ctx.hand, 'SUN')
            sun_score += shape['bid_adjustment']
            if best_suit:
                shape_h = evaluate_shape(ctx.hand, 'HOKUM', best_suit)
                best_hokum_score += shape_h['bid_adjustment']
            else:
                shape_h = None
            logger.debug(f"[BIDDING] Shape: {shape['pattern_label']} {shape['shape_type']} → SUN adj={shape['bid_adjustment']}, HOKUM adj={shape_h['bid_adjustment'] if shape_h else 0}")
        except Exception as e:
            logger.debug(f"Hand shape skipped: {e}")

        # 4. Contextual Checks (Ashkal)
        is_left_op = (ctx.player_index == (ctx.dealer_index + 3) % 4)
        can_ashkal = (ctx.is_dealer or is_left_op) and ctx.bidding_round <= 2
        
        # 5. Decision Thresholds
        
        # Partner Awareness: If partner currently holds the bid, raise thresholds
        current_bid = ctx.raw_state.get('bid', {})
        partner_has_proposal = False
        has_hokum_bid = False
        if current_bid:
             bidder_pos = current_bid.get('bidder')
             if bidder_pos == self._get_partner_pos_name(ctx.position):
                  partner_has_proposal = True
             if current_bid.get('type') == 'HOKUM':
                  has_hokum_bid = True
        
        # Position Awareness: Dealer = Last to speak
        is_last_to_speak = ctx.is_dealer
        
        # Base Thresholds (tuned for new scoring system)
        base_sun = 22
        base_hokum = 18
        
        # Apply Personality Bias
        sun_threshold = base_sun - ctx.personality.sun_bias
        hokum_threshold = base_hokum - ctx.personality.hokum_bias
        
        # ── DEALER-POSITION TACTICAL AWARENESS ──
        # Offensive position (first player or partner is first) = lower threshold
        if ctx.is_offensive:
            sun_threshold -= 2  # Leading first = advantage in Sun
            hokum_threshold -= 2  # Leading first = advantage in Hokum
        else:
            sun_threshold += 1  # Defensive = need slightly stronger hand
            hokum_threshold += 1

        # ── SCORE-AWARE RISK MANAGEMENT (via score_pressure module) ──
        pressure = get_score_pressure(ctx.match_score_us, ctx.match_score_them)
        situation = pressure['situation']
        bid_adj = pressure['bid_threshold_adjustment']
        # Apply normalized adjustment (scale from 0-1 range to threshold units)
        sun_threshold += int(bid_adj * -30)   # -0.15 → +4.5 lower threshold
        hokum_threshold += int(bid_adj * -25)
        logger.debug(f"[BIDDING] Score pressure: {situation}, bid_adj={bid_adj}")
        
        # Adjustments
        if partner_has_proposal:
             # Only take over partner if very strong
             sun_threshold += 8 
             hokum_threshold += 6
        elif is_last_to_speak and ctx.bidding_round == 2 and not current_bid:
             # Force Bid in last speaker of R2 to prevent infinite Pass Out
             sun_threshold -= 8
             hokum_threshold -= 8

        # Ashkal Check
        if can_ashkal:
             ranks = [c.rank for c in ctx.hand]
             has_strong_project = False
             
             # 4 Aces (400) or 4 Tens/Kings/Queens (100)
             if ranks.count('A') == 4: has_strong_project = True
             if ranks.count('10') == 4: has_strong_project = True
             if ranks.count('K') == 4: has_strong_project = True
             if ranks.count('Q') == 4: has_strong_project = True
             
             if has_strong_project:
                  if not (ctx.floor_card and ctx.floor_card.rank == 'A'):
                       return {"action": "ASHKAL", "reasoning": "Forced Ashkal: Strong Project"}

             if sun_score >= (sun_threshold + 4 - ctx.personality.ashkal_bias):
                  if not (ctx.floor_card and ctx.floor_card.rank == 'A'):
                       return {"action": "ASHKAL", "reasoning": f"Strong Sun Hand + Dealer Privilege (Score {sun_score})"}
        
        # 6. Defensive / Psychological Logic — "Suicide Bid" / Project Denial
        if current_bid:
             bidder_pos = current_bid.get('bidder')
             if bidder_pos != self._get_partner_pos_name(ctx.position):
                  # Opponents bidding in a critical situation
                  if situation in ('DESPERATE', 'MATCH_POINT'):
                       if current_bid.get('type') == 'SUN':
                            hokum_threshold -= 8
        
        # 7. Final Decision — Sun > Hokum priority
        # Check gamble override for borderline hands
        sun_normalized = sun_score / 35.0  # Normalize to 0-1 range
        hokum_normalized = best_hokum_score / 30.0
        
        if sun_score >= sun_threshold: 
            return {"action": "SUN", "reasoning": f"Strong Sun Hand (Score {sun_score}, ET={sun_et}) [{situation}]"}
        elif should_gamble(ctx.match_score_us, ctx.match_score_them, sun_normalized, 'SUN'):
            if sun_score >= sun_threshold - 4:  # Only gamble on near-threshold hands
                return {"action": "SUN", "reasoning": f"Gamble Sun (Score {sun_score}, ET={sun_et}) [{situation}]"}
            
        if not has_hokum_bid:
            if best_hokum_score >= hokum_threshold and best_suit:
                 reason = f"Good {best_suit} Suit (Score {best_hokum_score}, ET={hokum_et}) [{situation}]"
                 return {"action": "HOKUM", "suit": best_suit, "reasoning": reason}
            elif should_gamble(ctx.match_score_us, ctx.match_score_them, hokum_normalized, 'HOKUM'):
                if best_hokum_score >= hokum_threshold - 4 and best_suit:
                    return {"action": "HOKUM", "suit": best_suit, "reasoning": f"Gamble {best_suit} (Score {best_hokum_score}, ET={hokum_et}) [{situation}]"}
        
        return {"action": "PASS", "reasoning": f"Hand too weak (Sun:{sun_score} Hokum:{best_hokum_score}) [{situation}]"}

    def _detect_premium_pattern(self, ctx: BotContext):
        """
        Floor-card-aware pattern detection for premium hands.
        Delegates to focused components.
        """
        # Hokum patterns (Lockdown, Baloot) - Only in Round 1
        hokum_pattern = detect_hokum_premium_pattern(ctx)
        if hokum_pattern:
            return hokum_pattern

        # Sun patterns (400, Miya, Ruler)
        sun_pattern = detect_sun_premium_pattern(ctx)
        if sun_pattern:
            return sun_pattern

        return None

    def _get_partner_pos_name(self, my_pos):
        pairs = {'Bottom': 'Top', 'Top': 'Bottom', 'Right': 'Left', 'Left': 'Right'}
        return pairs.get(my_pos, 'Unknown')

    def _get_gablak_decision(self, ctx: BotContext):
        """Handle Gablak window — steal bid if we have a strong hand."""
        sun_score = calculate_sun_strength(ctx.hand)
        
        # Steal with Sun if we have a very strong hand
        if sun_score >= 28:
            return {"action": "SUN", "reasoning": f"Gablak Steal: Strong Sun ({sun_score})"}
        
        # Steal Hokum if we have dominant trump
        for suit in SUITS:
            if ctx.bidding_round == 1 and ctx.floor_card and suit != ctx.floor_card.suit:
                continue
            if ctx.bidding_round == 2 and ctx.floor_card and suit == ctx.floor_card.suit:
                continue
            score = calculate_hokum_strength(ctx.hand, suit)
            if score >= 24:
                return {"action": "HOKUM", "suit": suit, "reasoning": f"Gablak Steal: Strong {suit} ({score})"}
        
        return {"action": "PASS", "reasoning": "Waive Gablak"}

    def get_doubling_decision(self, ctx: BotContext):
        """Smart doubling — uses advanced doubling engine with score awareness."""
        from ai_worker.strategies.components.doubling_engine import should_double

        bid = ctx.raw_state.get('bid', {})
        bid_type = bid.get('type')
        bidder_pos = bid.get('bidder')
        trump_suit = bid.get('suit')

        # Am I on the defending team (opponent bid)?
        partner_pos = self._get_partner_pos_name(ctx.position)
        is_defending = (bidder_pos != ctx.position and bidder_pos != partner_pos)

        if not is_defending:
            return {"action": "PASS", "reasoning": "Our team bid — no double"}

        # Check if partner already passed on doubling
        partner_passed = True
        doubling_history = ctx.raw_state.get('doublingHistory', [])
        for dh in doubling_history:
            if dh.get('player') == partner_pos and dh.get('action') != 'PASS':
                partner_passed = False

        result = should_double(
            hand=ctx.hand,
            bid_type=bid_type or 'SUN',
            trump_suit=trump_suit,
            my_score=ctx.match_score_us,
            their_score=ctx.match_score_them,
            partner_passed=partner_passed,
        )
        logger.debug(f"[DOUBLING] {result['reasoning']}")

        if result['should_double']:
            return {"action": "DOUBLE", "reasoning": f"Double! {result['reasoning']}"}
        return {"action": "PASS", "reasoning": f"No double: {result['reasoning']}"}

    def get_variant_decision(self, ctx: BotContext):
        bid = ctx.raw_state.get('bid', {})
        trump_suit = bid.get('suit')
        if not trump_suit: return {"action": "OPEN"}
        
        trump_count = sum(1 for c in ctx.hand if c.suit == trump_suit)
        trump_ranks = [c.rank for c in ctx.hand if c.suit == trump_suit]
        
        # Strong trumps → OPEN (show confidence)
        has_j = 'J' in trump_ranks
        has_9 = '9' in trump_ranks
        
        if trump_count >= 4 or (has_j and has_9):
            return {"action": "OPEN", "reasoning": "Strong Trumps — Show Confidence"}
        elif trump_count <= 2:
            return {"action": "CLOSED", "reasoning": "Weak Trumps — Hide Hand"}
        else:
            # 3 trumps — check quality
            if has_j or has_9:
                return {"action": "OPEN", "reasoning": "Decent Trumps"}
            return {"action": "CLOSED", "reasoning": "Average Trumps"}

    # Wrapper methods for backward compatibility
    def calculate_sun_strength(self, hand):
        """
        Advanced Sun hand evaluation.
        Delegates to ai_worker.strategies.components.sun_bidding.calculate_sun_strength
        """
        return calculate_sun_strength(hand)

    def calculate_hokum_strength(self, hand, trump_suit):
        """
        Advanced Hokum hand evaluation.
        Delegates to ai_worker.strategies.components.hokum_bidding.calculate_hokum_strength
        """
        return calculate_hokum_strength(hand, trump_suit)
