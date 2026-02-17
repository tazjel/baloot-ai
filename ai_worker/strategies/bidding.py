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
from ai_worker.strategies.components.bid_analysis import analyze_opponent_bids, evaluate_gablak
from ai_worker.strategies.components.pro_data import (
    get_pro_bid_frequency, get_pro_win_rate, get_position_multiplier,
    SCORE_BID_ADJUSTMENT, PRO_PASS_RATE,
)
from ai_worker.strategies.difficulty import get_bid_noise
import logging

logger = logging.getLogger(__name__)


def _classify_score_state(us: int, them: int) -> str:
    """Map match score to pro_data score-state key."""
    diff = us - them
    if abs(diff) <= 15:
        return "tied"
    if diff > 30:
        return "far_ahead"
    if diff > 0:
        return "slightly_ahead"
    if diff < -30:
        return "far_behind"
    return "slightly_behind"


def _count_high_cards_hokum(hand, trump_suit: str, floor_card=None) -> tuple[int, int]:
    """Count trumps and high cards (J,9,A in trump + side Aces) for pro lookup."""
    effective = list(hand)
    if floor_card and floor_card.suit == trump_suit:
        effective.append(floor_card)

    trump_count = sum(1 for c in effective if c.suit == trump_suit)
    high_cards = 0
    for c in effective:
        if c.suit == trump_suit and c.rank in ('J', '9', 'A'):
            high_cards += 1
        elif c.suit != trump_suit and c.rank == 'A':
            high_cards += 1
    return trump_count, high_cards

class BiddingStrategy:
    def get_decision(self, ctx: BotContext):
        # 1. Phase Dispatch
        phase = ctx.bidding_phase
        if phase == BiddingPhase.DOUBLING:
             return self.get_doubling_decision(ctx)
        elif phase == BiddingPhase.VARIANT_SELECTION:
             return self.get_variant_decision(ctx)
        elif phase == BiddingPhase.GABLAK_WINDOW:
             return evaluate_gablak(ctx.hand, ctx.floor_card, ctx.bidding_round,
                                    SUITS, calculate_sun_strength, calculate_hokum_strength)

        # 2. Premium Pattern Check
        pattern = self._detect_premium_pattern(ctx)
        if pattern:
            if not ctx.is_dealer or pattern.get('action') == 'HOKUM':
                return pattern

        # 3. Evaluate hand scores + trick projections
        scores = self._evaluate_hand_scores(ctx)
        sun_score = scores['sun_score']
        best_hokum_score = scores['hokum_score']
        best_suit = scores['best_suit']
        sun_proj = scores['sun_proj']
        hokum_proj = scores['hokum_proj']
        sun_et = scores['sun_et']
        hokum_et = scores['hokum_et']
        situation = scores['situation']

        # 4. Compute adjusted thresholds
        thresholds = self._compute_thresholds(ctx, best_suit, best_hokum_score, situation)
        sun_threshold = thresholds['sun_threshold']
        hokum_threshold = thresholds['hokum_threshold']
        has_hokum_bid = thresholds['has_hokum_bid']

        # 5. Ashkal Check
        is_left_op = (ctx.player_index == (ctx.dealer_index + 3) % 4)
        can_ashkal = (ctx.is_dealer or is_left_op) and ctx.bidding_round <= 2
        if can_ashkal:
             ranks = [c.rank for c in ctx.hand]
             has_strong_project = any(ranks.count(r) == 4 for r in ('A', '10', 'K', 'Q'))
             if has_strong_project:
                  if not (ctx.floor_card and ctx.floor_card.rank == 'A'):
                       return {"action": "ASHKAL", "reasoning": "Forced Ashkal: Strong Project"}
             if sun_score >= (sun_threshold + 4 - ctx.personality.ashkal_bias):
                  if not (ctx.floor_card and ctx.floor_card.rank == 'A'):
                       return {"action": "ASHKAL", "reasoning": f"Strong Sun Hand + Dealer Privilege (Score {sun_score})"}

        # 6. Pro bid frequency validation (adjust hokum score)
        best_hokum_score = self._apply_pro_frequency_validation(
            ctx, best_suit, best_hokum_score)

        # 7. Final Decision — apply trick bonuses and decide
        return self._make_final_decision(
            sun_score, best_hokum_score, best_suit,
            sun_threshold, hokum_threshold, has_hokum_bid,
            sun_et, hokum_et, sun_proj, hokum_proj, situation,
            ctx.match_score_us, ctx.match_score_them)

    def _evaluate_hand_scores(self, ctx: BotContext) -> dict:
        """Evaluate SUN and HOKUM hand scores with trick projections."""
        sun_score = calculate_sun_strength(ctx.hand)

        # Best Hokum Suit (with Ace Trap protection)
        best_suit = None
        best_hokum_score = 0
        for suit in SUITS:
            if ctx.bidding_round == 1 and ctx.floor_card and suit != ctx.floor_card.suit:
                continue
            if ctx.bidding_round == 2 and ctx.floor_card and suit == ctx.floor_card.suit:
                continue
            # Ace Trap: skip floor Ace without J or 9
            if ctx.floor_card and ctx.floor_card.suit == suit and ctx.floor_card.rank == 'A':
                hand_trump_ranks = [c.rank for c in ctx.hand if c.suit == suit]
                if 'J' not in hand_trump_ranks and '9' not in hand_trump_ranks:
                    logger.info(f"[BIDDING] Ace Trap: Skipping {suit} — floor Ace without J or 9")
                    continue
            fc_for_eval = ctx.floor_card if ctx.bidding_round == 1 else None
            score = calculate_hokum_strength(ctx.hand, suit, floor_card=fc_for_eval)
            if score > best_hokum_score:
                best_hokum_score = score
                best_suit = suit

        # Trick Projection
        hokum_proj_hand = list(ctx.hand)
        if best_suit and ctx.floor_card and ctx.bidding_round == 1 and ctx.floor_card.suit == best_suit:
            hokum_proj_hand.append(ctx.floor_card)
        sun_proj = project_tricks(ctx.hand, 'SUN')
        hokum_proj = project_tricks(hokum_proj_hand, 'HOKUM', best_suit) if best_suit else None
        sun_et = sun_proj['expected_tricks']
        sun_losers = sun_proj.get('losers', 8)
        hokum_et = hokum_proj['expected_tricks'] if hokum_proj else 0
        hokum_losers = hokum_proj.get('losers', 8) if hokum_proj else 8
        logger.debug(f"[BIDDING] Trick projection: SUN ET={sun_et} L={sun_losers} | HOKUM({best_suit}) ET={hokum_et} L={hokum_losers}")

        # Loser penalty
        if sun_losers >= 5: sun_score -= 3
        elif sun_losers >= 4: sun_score -= 1
        if hokum_losers >= 5: best_hokum_score -= 2
        elif hokum_losers >= 4: best_hokum_score -= 1

        # Hand Shape Analysis
        try:
            shape = evaluate_shape(ctx.hand, 'SUN')
            sun_score += shape['bid_adjustment']
            if best_suit:
                shape_h = evaluate_shape(ctx.hand, 'HOKUM', best_suit)
                best_hokum_score += shape_h['bid_adjustment']
        except Exception:
            pass

        # Difficulty noise
        try:
            noise = get_bid_noise(ctx.difficulty)
            if noise:
                sun_score += noise
                best_hokum_score += noise
        except Exception:
            pass

        # Score pressure situation
        pressure = get_score_pressure(ctx.match_score_us, ctx.match_score_them)
        situation = pressure['situation']

        return {
            'sun_score': sun_score, 'hokum_score': best_hokum_score,
            'best_suit': best_suit, 'sun_proj': sun_proj, 'hokum_proj': hokum_proj,
            'sun_et': sun_et, 'hokum_et': hokum_et, 'situation': situation,
        }

    def _compute_thresholds(self, ctx: BotContext, best_suit, best_hokum_score, situation) -> dict:
        """Compute adjusted bid thresholds from position, score, opponents."""
        partner_pos = self._get_partner_pos_name(ctx.position)
        current_bid = ctx.raw_state.get('bid', {})
        partner_has_proposal = False
        has_hokum_bid = False
        if current_bid:
             bidder_pos = current_bid.get('bidder')
             if bidder_pos == partner_pos:
                  partner_has_proposal = True
             if current_bid.get('type') == 'HOKUM':
                  has_hokum_bid = True

        # Base thresholds + personality
        sun_threshold = 22 - ctx.personality.sun_bias
        hokum_threshold = 18 - ctx.personality.hokum_bias

        # Position multiplier (from 109 pro games)
        try:
            bid_position = ((ctx.player_index - ctx.dealer_index) % 4) or 4
            pos_mult = get_position_multiplier(bid_position)
            pos_adj = int((1.0 - pos_mult) * 20)
            sun_threshold += pos_adj
            hokum_threshold += pos_adj
        except Exception:
            pass

        # Score-state adjustment
        try:
            score_state = _classify_score_state(ctx.match_score_us, ctx.match_score_them)
            score_adj = int(SCORE_BID_ADJUSTMENT.get(score_state, 0.0) * -60)
            sun_threshold += score_adj
            hokum_threshold += score_adj
        except Exception:
            pass

        # Score pressure
        pressure = get_score_pressure(ctx.match_score_us, ctx.match_score_them)
        bid_adj = pressure['bid_threshold_adjustment']
        sun_threshold += int(bid_adj * -30)
        hokum_threshold += int(bid_adj * -25)

        # Partner/dealer adjustments
        if partner_has_proposal:
             sun_threshold += 8
             hokum_threshold += 6
        elif ctx.is_dealer and ctx.bidding_round == 2 and not current_bid:
             sun_threshold -= 8
             hokum_threshold -= 8

        # Opponent bid inference
        bid_history = ctx.raw_state.get('bidHistory', [])
        opp_bid_info = analyze_opponent_bids(bid_history, ctx.position, partner_pos)

        if opp_bid_info['opponent_bid_sun']:
            sun_threshold -= 2
            hokum_threshold += 2
        if opp_bid_info['opponent_bid_hokum_suit']:
            opp_trump = opp_bid_info['opponent_bid_hokum_suit']
            if best_suit == opp_trump:
                hokum_threshold += 6
            else:
                hokum_threshold -= 1
        if opp_bid_info['opponent_passed_r1'] and ctx.bidding_round == 2:
            sun_threshold -= 1
            hokum_threshold -= 1
        if opp_bid_info['partner_bid_and_opp_competed']:
            sun_threshold += 2
            hokum_threshold += 2

        # Defensive / psychological: suicide bid
        if current_bid:
             bidder_pos = current_bid.get('bidder')
             if bidder_pos != partner_pos:
                  if situation in ('DESPERATE', 'MATCH_POINT'):
                       if current_bid.get('type') == 'SUN':
                            hokum_threshold -= 8

        return {
            'sun_threshold': sun_threshold, 'hokum_threshold': hokum_threshold,
            'has_hokum_bid': has_hokum_bid,
        }

    def _apply_pro_frequency_validation(self, ctx, best_suit, best_hokum_score):
        """Validate hokum bid against pro frequency data."""
        try:
            if best_suit:
                tc, hc = _count_high_cards_hokum(
                    ctx.hand, best_suit,
                    ctx.floor_card if ctx.bidding_round == 1 else None)
                pro_freq = get_pro_bid_frequency(tc, hc)
                pro_wr = get_pro_win_rate(tc, hc, 'HOKUM')
                if pro_freq >= 0.60: best_hokum_score += 4
                elif pro_freq >= 0.30: best_hokum_score += 2
                elif pro_freq <= 0.01 and pro_freq > 0: best_hokum_score -= 3
                elif pro_freq == 0: best_hokum_score -= 5
                if pro_wr < 0.65 and pro_freq > 0: best_hokum_score -= 2
                elif pro_wr >= 0.85: best_hokum_score += 2
        except Exception:
            pass
        return best_hokum_score

    def _make_final_decision(self, sun_score, best_hokum_score, best_suit,
                             sun_threshold, hokum_threshold, has_hokum_bid,
                             sun_et, hokum_et, sun_proj, hokum_proj, situation,
                             score_us, score_them):
        """Apply trick bonuses and make the final bid decision."""
        is_desperate = situation in ('DESPERATE', 'MATCH_POINT')
        sun_trick_ok = sun_et >= 2.5 or is_desperate
        hokum_trick_ok = hokum_et >= 2.0 or is_desperate

        # Graduated trick bonus/penalty
        for et, target in [(sun_et, 'sun'), (hokum_et, 'hokum')]:
            bonus = 5 if et >= 5.0 else 3 if et >= 4.0 else 1 if et >= 3.0 else 0
            if target == 'sun':
                sun_score += bonus
                if et < 2.0 and not is_desperate: sun_score -= 3
            else:
                best_hokum_score += bonus
                if et < 1.5 and not is_desperate: best_hokum_score -= 3

        # Quick trick confidence
        sun_min = sun_proj.get('min_tricks', 0)
        hokum_min = hokum_proj.get('min_tricks', 0) if hokum_proj else 0
        if sun_min >= 3: sun_score += 2
        if hokum_min >= 3: best_hokum_score += 2

        # Gamble check
        sun_normalized = sun_score / 35.0
        hokum_normalized = best_hokum_score / 30.0

        if sun_score >= sun_threshold and sun_trick_ok:
            return {"action": "SUN", "reasoning": f"Strong Sun Hand (Score {sun_score}, ET={sun_et}) [{situation}]"}
        elif should_gamble(score_us, score_them, sun_normalized, 'SUN'):
            if sun_score >= sun_threshold - 4 and sun_trick_ok:
                return {"action": "SUN", "reasoning": f"Gamble Sun (Score {sun_score}, ET={sun_et}) [{situation}]"}

        if not has_hokum_bid:
            if best_hokum_score >= hokum_threshold and best_suit and hokum_trick_ok:
                 return {"action": "HOKUM", "suit": best_suit,
                         "reasoning": f"Good {best_suit} Suit (Score {best_hokum_score}, ET={hokum_et}) [{situation}]"}
            elif should_gamble(score_us, score_them, hokum_normalized, 'HOKUM'):
                if best_hokum_score >= hokum_threshold - 4 and best_suit and hokum_trick_ok:
                    return {"action": "HOKUM", "suit": best_suit,
                            "reasoning": f"Gamble {best_suit} (Score {best_hokum_score}, ET={hokum_et}) [{situation}]"}

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

        # Personality: doubling_confidence adjusts the threshold
        # < 1.0 = bold (doubles on lower confidence), > 1.0 = cautious
        dc = getattr(ctx.personality, 'doubling_confidence', 1.0)
        effective_confidence = result.get('confidence', 0.0)
        should = result['should_double']
        if dc != 1.0 and effective_confidence > 0:
            # Bold personality: accept lower confidence; cautious: require higher
            adjusted_conf = effective_confidence / dc
            should = adjusted_conf >= 0.5
            logger.debug(f"[DOUBLING] Personality adj: conf={effective_confidence:.2f}/dc={dc:.1f}={adjusted_conf:.2f} -> {'DOUBLE' if should else 'PASS'}")

        if should:
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
