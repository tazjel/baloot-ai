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
                
            # Include floor card in R1 evaluation (dealer picks it up)
            fc_for_eval = ctx.floor_card if ctx.bidding_round == 1 else None
            score = calculate_hokum_strength(ctx.hand, suit, floor_card=fc_for_eval)
            if score > best_hokum_score:
                best_hokum_score = score
                best_suit = suit
        
        # 3b. Trick Projection — expected tricks for confidence & score adjustment
        # For Hokum R1, include floor card in trick projection if it's trump
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

        # Loser penalty — high losers = hand won't deliver even with good HCP
        if sun_losers >= 5:
            sun_score -= 3  # Too many losers for SUN
        elif sun_losers >= 4:
            sun_score -= 1
        if hokum_losers >= 5:
            best_hokum_score -= 2  # Too many losers for HOKUM
        elif hokum_losers >= 4:
            best_hokum_score -= 1

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

        # 3d. Difficulty noise — add randomness to bid evaluation for lower levels
        try:
            noise = get_bid_noise(ctx.difficulty)
            if noise:
                sun_score += noise
                best_hokum_score += noise
                logger.debug(f"[BIDDING] Difficulty noise: {noise:+d} (level={ctx.difficulty.name})")
        except Exception:
            pass

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

        # ── EMPIRICAL POSITION MULTIPLIER (from 109 pro games) ──
        # Pros: Pos 1 bids 9.9%, Pos 4 (dealer) bids 26.7% — 2.7x advantage.
        # We map bidding position to a threshold adjustment:
        #   Pos 1 (first, conservative): raise threshold
        #   Pos 4 (dealer, last to speak): lower threshold significantly
        try:
            # Determine bidding position (1-4, relative to dealer)
            bid_position = ((ctx.player_index - ctx.dealer_index) % 4) or 4
            pos_mult = get_position_multiplier(bid_position)
            # Convert multiplier to threshold adjustment:
            # mult=0.85 (pos 1) → +3 (raise threshold → conservative)
            # mult=1.40 (pos 4) → -8 (lower threshold → aggressive)
            pos_adj = int((1.0 - pos_mult) * 20)
            sun_threshold += pos_adj
            hokum_threshold += pos_adj
            logger.debug(f"[BIDDING] Position {bid_position}: mult={pos_mult} → adj={pos_adj:+d}")
        except Exception:
            pass  # Fall through with no position adjustment

        # ── EMPIRICAL SCORE-STATE ADJUSTMENT (from 109 pro games) ──
        # Pros adjust bidding frequency based on match score:
        #   tied → most aggressive (+3%), far_ahead → most conservative (-3%)
        try:
            score_state = _classify_score_state(ctx.match_score_us, ctx.match_score_them)
            score_adj_raw = SCORE_BID_ADJUSTMENT.get(score_state, 0.0)
            # Scale empirical adjustment (±0.03 range) to threshold units (±2)
            score_adj = int(score_adj_raw * -60)  # +0.03 → -1.8 (lower threshold)
            sun_threshold += score_adj
            hokum_threshold += score_adj
            logger.debug(f"[BIDDING] Score state '{score_state}': adj={score_adj:+d}")
        except Exception:
            pass

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
        
        # 6. Defensive Bidding Inference — read opponent bid history
        # Analyze what opponents have bid to adjust our strategy
        bid_history = ctx.raw_state.get('bidHistory', [])
        partner_pos = self._get_partner_pos_name(ctx.position)
        opp_bid_info = analyze_opponent_bids(bid_history, ctx.position, partner_pos)

        if opp_bid_info['opponent_bid_sun']:
            # Opponent bid SUN — they have a strong balanced hand
            # Lower our SUN threshold to compete (counter-bid)
            # but raise HOKUM threshold (their strength is in raw honors)
            sun_threshold -= 2  # Compete aggressively for SUN
            hokum_threshold += 2  # Their honors hurt us in Hokum too
            logger.debug(f"[BIDDING] Opp bid SUN — competing SUN (-2), cautious HOKUM (+2)")

        if opp_bid_info['opponent_bid_hokum_suit']:
            opp_trump = opp_bid_info['opponent_bid_hokum_suit']
            # Opponent showed trump preference — they likely hold J/9 in that suit
            # If we're considering the same suit, be very cautious
            if best_suit == opp_trump:
                hokum_threshold += 6  # Very dangerous to bid same suit as opponent
                logger.debug(f"[BIDDING] Opp bid {opp_trump} — same suit! Raise threshold +6")
            else:
                # Different suit — opponent's trump commitment means fewer honors elsewhere
                hokum_threshold -= 1  # Slight advantage in a different suit

        if opp_bid_info['opponent_passed_r1'] and ctx.bidding_round == 2:
            # Both opponents passed R1 — they're weak in floor suit
            # This means our side suits are safer; slightly lower thresholds
            sun_threshold -= 1
            hokum_threshold -= 1
            logger.debug("[BIDDING] Both opps passed R1 — field is weak, lower thresholds")

        if opp_bid_info['partner_bid_and_opp_competed']:
            # Partner bid but opponent competed over them — opponent is strong
            # Be cautious about overbidding
            sun_threshold += 2
            hokum_threshold += 2
            logger.debug("[BIDDING] Opp competed over partner — cautious (+2)")

        # 6b. Defensive / Psychological Logic — "Suicide Bid" / Project Denial
        if current_bid:
             bidder_pos = current_bid.get('bidder')
             if bidder_pos != partner_pos:
                  # Opponents bidding in a critical situation
                  if situation in ('DESPERATE', 'MATCH_POINT'):
                       if current_bid.get('type') == 'SUN':
                            hokum_threshold -= 8
        
        # 6c. EMPIRICAL PRO BID FREQUENCY VALIDATION
        # Cross-reference our hand shape against what pros actually bid
        # from 10,698 human bids in 109 games. If pros almost never bid
        # this hand shape, apply a penalty. If they always bid it, apply a boost.
        try:
            if best_suit:
                tc, hc = _count_high_cards_hokum(ctx.hand, best_suit,
                                                  ctx.floor_card if ctx.bidding_round == 1 else None)
                pro_freq = get_pro_bid_frequency(tc, hc)
                pro_wr = get_pro_win_rate(tc, hc, 'HOKUM')

                if pro_freq >= 0.60:
                    best_hokum_score += 4  # Pros bid this shape 60%+ → strong shape
                    logger.debug(f"[PRO] Hokum {tc}t_{hc}h: freq={pro_freq:.0%} WR={pro_wr:.0%} → +4")
                elif pro_freq >= 0.30:
                    best_hokum_score += 2  # Pros bid 30-60% → decent shape
                    logger.debug(f"[PRO] Hokum {tc}t_{hc}h: freq={pro_freq:.0%} WR={pro_wr:.0%} → +2")
                elif pro_freq <= 0.01 and pro_freq > 0:
                    best_hokum_score -= 3  # Pros almost never bid this → danger
                    logger.debug(f"[PRO] Hokum {tc}t_{hc}h: freq={pro_freq:.0%} → -3 (pros avoid)")
                elif pro_freq == 0:
                    best_hokum_score -= 5  # Pros NEVER bid this shape
                    logger.debug(f"[PRO] Hokum {tc}t_{hc}h: freq=0% → -5 (never bid by pros)")

                # Win rate validation: if pros have low win rate, penalize
                if pro_wr < 0.65 and pro_freq > 0:
                    best_hokum_score -= 2
                    logger.debug(f"[PRO] Low win rate {pro_wr:.0%} → -2")
                elif pro_wr >= 0.85:
                    best_hokum_score += 2
                    logger.debug(f"[PRO] High win rate {pro_wr:.0%} → +2")
        except Exception as e:
            logger.debug(f"Pro bid frequency check skipped: {e}")

        # 7. Final Decision — Sun > Hokum priority
        # Trick projection as bid safety gate: require minimum expected tricks
        # to avoid bidding on hands with high HCP but no trick-taking shape
        is_desperate = situation in ('DESPERATE', 'MATCH_POINT')
        sun_trick_ok = sun_et >= 2.5 or is_desperate
        hokum_trick_ok = hokum_et >= 2.0 or is_desperate

        # Graduated trick bonus/penalty (reward trick-rich hands, penalize mirages)
        # SUN: need ≥3 tricks to be viable, ≥4 to be strong
        if sun_et >= 5.0:
            sun_score += 5  # Dominant trick count
        elif sun_et >= 4.0:
            sun_score += 3
        elif sun_et >= 3.0:
            sun_score += 1
        elif sun_et < 2.0 and not is_desperate:
            sun_score -= 3  # HCP mirage: high points but can't win tricks

        # HOKUM: need ≥2.5 tricks to be viable
        if hokum_et >= 5.0:
            best_hokum_score += 5  # Dominant
        elif hokum_et >= 4.0:
            best_hokum_score += 3
        elif hokum_et >= 3.0:
            best_hokum_score += 1
        elif hokum_et < 1.5 and not is_desperate:
            best_hokum_score -= 3  # Weak shape despite trump honors

        # Quick trick confidence: min_tricks is the floor (guaranteed wins)
        sun_min = sun_proj.get('min_tricks', 0)
        hokum_min = hokum_proj.get('min_tricks', 0) if hokum_proj else 0
        if sun_min >= 3:
            sun_score += 2  # 3+ guaranteed tricks = very safe
        if hokum_min >= 3:
            best_hokum_score += 2

        # Check gamble override for borderline hands
        sun_normalized = sun_score / 35.0  # Normalize to 0-1 range
        hokum_normalized = best_hokum_score / 30.0

        if sun_score >= sun_threshold and sun_trick_ok:
            return {"action": "SUN", "reasoning": f"Strong Sun Hand (Score {sun_score}, ET={sun_et}) [{situation}]"}
        elif should_gamble(ctx.match_score_us, ctx.match_score_them, sun_normalized, 'SUN'):
            if sun_score >= sun_threshold - 4 and sun_trick_ok:
                return {"action": "SUN", "reasoning": f"Gamble Sun (Score {sun_score}, ET={sun_et}) [{situation}]"}

        if not has_hokum_bid:
            if best_hokum_score >= hokum_threshold and best_suit and hokum_trick_ok:
                 reason = f"Good {best_suit} Suit (Score {best_hokum_score}, ET={hokum_et}) [{situation}]"
                 return {"action": "HOKUM", "suit": best_suit, "reasoning": reason}
            elif should_gamble(ctx.match_score_us, ctx.match_score_them, hokum_normalized, 'HOKUM'):
                if best_hokum_score >= hokum_threshold - 4 and best_suit and hokum_trick_ok:
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
