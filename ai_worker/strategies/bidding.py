from game_engine.models.constants import SUITS, BiddingPhase, BidType, ORDER_SUN, ORDER_HOKUM
from ai_worker.bot_context import BotContext
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
        sun_score = self.calculate_sun_strength(ctx.hand)
        
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
                
            score = self.calculate_hokum_strength(ctx.hand, suit)
            if score > best_hokum_score:
                best_hokum_score = score
                best_suit = suit
        
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

        # ── SCORE-AWARE RISK MANAGEMENT ──
        # When match score is >100, doubling risk is devastating
        if ctx.match_score_us >= 100:
            sun_threshold += 3  # Protect the lead — tighter bidding
            hokum_threshold += 3
        elif ctx.match_score_them >= 100:
            sun_threshold -= 2  # Must gamble to catch up
            hokum_threshold -= 2

        # Desperate mode: more aggressive bidding
        if ctx.is_desperate:
            sun_threshold -= 3
            hokum_threshold -= 3
        # Protecting a big lead: conservative bidding
        elif ctx.is_protecting:
            sun_threshold += 4
            hokum_threshold += 4
        
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
        
        # 6. Defensive / Psychological Logic
        scores = ctx.raw_state.get('matchScores', {'us': 0, 'them': 0})
        them_score = scores.get('them', 0)
        us_score = scores.get('us', 0)
        
        is_danger_zone = them_score >= 120
        is_critical_zone = them_score >= 135
        
        if is_critical_zone:
             sun_threshold -= 4
             hokum_threshold -= 4
             
        # "Suicide Bid" / Project Denial
        if current_bid:
             bidder_pos = current_bid.get('bidder')
             if bidder_pos != self._get_partner_pos_name(ctx.position):
                  # Opponents bidding
                  if is_critical_zone or (them_score >= 100):
                       if current_bid.get('type') == 'SUN':
                            hokum_threshold -= 8
        
        # 7. Final Decision — Sun > Hokum priority
        if sun_score >= sun_threshold: 
            return {"action": "SUN", "reasoning": f"Strong Sun Hand (Score {sun_score})"}
            
        if not has_hokum_bid:
            if best_hokum_score >= hokum_threshold and best_suit:
                 reason = f"Good {best_suit} Suit (Score {best_hokum_score})"
                 if is_critical_zone: reason += " [Defensive]"
                 return {"action": "HOKUM", "suit": best_suit, "reasoning": reason}
        
        return {"action": "PASS", "reasoning": f"Hand too weak (Sun:{sun_score} Hokum:{best_hokum_score})"}

    def _detect_premium_pattern(self, ctx: BotContext):
        """
        Floor-card-aware pattern detection for premium hands.
        Checks the combined hand (5 cards) + floor card for:
        - Lockdown: Top 4 trumps in Hokum (J, 9, A, 10)
        - 400: 4 Aces in Sun (40-point project)
        - Miya: 5-card sequence (A-K-Q-J-10) in Sun (100 project)
        - Baloot: K+Q of trump for Hokum project bonus
        """
        if not ctx.floor_card:
            return None

        fc = ctx.floor_card
        hand_ranks = [c.rank for c in ctx.hand]
        combined_ranks = hand_ranks + [fc.rank]

        # Round 1: Can only buy floor card suit for Hokum
        if ctx.bidding_round == 1:
            floor_suit = fc.suit

            # === LOCKDOWN (Hokum): Top 4 trumps ===
            # In Hokum order: J > 9 > A > 10
            hand_trump_ranks = [c.rank for c in ctx.hand if c.suit == floor_suit]
            combined_trump = hand_trump_ranks + ([fc.rank] if True else [])
            lockdown_cards = {'J', '9', 'A', '10'}
            if lockdown_cards.issubset(set(combined_trump)):
                return {"action": "HOKUM", "suit": floor_suit,
                        "reasoning": f"LOCKDOWN: Top 4 trumps in {floor_suit} (J-9-A-10)"}

            # === BALOOT SETUP (Hokum): K+Q of trump + J ===
            if 'J' in hand_trump_ranks:  # Must have Jack for strength
                if 'K' in combined_trump and 'Q' in combined_trump:
                    return {"action": "HOKUM", "suit": floor_suit,
                            "reasoning": f"BALOOT Setup: J + K+Q of {floor_suit}"}

        # === 400 (Sun): 4 Aces ===
        if combined_ranks.count('A') >= 4:
            return {"action": "SUN",
                    "reasoning": "400 Project: 4 Aces (40-point bonus)"}

        # === MIYA (Sun): 5-card sequence A-K-Q-J-10 in same suit ===
        for suit in SUITS:
            suit_ranks = [c.rank for c in ctx.hand if c.suit == suit]
            if fc.suit == suit:
                suit_ranks.append(fc.rank)
            miya_set = {'A', 'K', 'Q', 'J', '10'}
            if miya_set.issubset(set(suit_ranks)):
                return {"action": "SUN",
                        "reasoning": f"MIYA: 5-card sequence in {suit} (100 project)"}

        # === RULER OF THE BOARD (Sun): 3+ Aces + 2+ Tens ===
        ace_count = combined_ranks.count('A')
        ten_count = combined_ranks.count('10')
        if ace_count >= 3 and ten_count >= 2:
            return {"action": "SUN",
                    "reasoning": f"Ruler: {ace_count} Aces + {ten_count} Tens"}

        return None

    def _get_partner_pos_name(self, my_pos):
        pairs = {'Bottom': 'Top', 'Top': 'Bottom', 'Right': 'Left', 'Left': 'Right'}
        return pairs.get(my_pos, 'Unknown')

    def _get_gablak_decision(self, ctx: BotContext):
        """Handle Gablak window — steal bid if we have a strong hand."""
        sun_score = self.calculate_sun_strength(ctx.hand)
        
        # Steal with Sun if we have a very strong hand
        if sun_score >= 28:
            return {"action": "SUN", "reasoning": f"Gablak Steal: Strong Sun ({sun_score})"}
        
        # Steal Hokum if we have dominant trump
        for suit in SUITS:
            if ctx.bidding_round == 1 and ctx.floor_card and suit != ctx.floor_card.suit:
                continue
            if ctx.bidding_round == 2 and ctx.floor_card and suit == ctx.floor_card.suit:
                continue
            score = self.calculate_hokum_strength(ctx.hand, suit)
            if score >= 24:
                return {"action": "HOKUM", "suit": suit, "reasoning": f"Gablak Steal: Strong {suit} ({score})"}
        
        return {"action": "PASS", "reasoning": "Waive Gablak"}

    def get_doubling_decision(self, ctx: BotContext):
        """Smart doubling — punish bad bids."""
        bid = ctx.raw_state.get('bid', {})
        bid_type = bid.get('type')
        bidder_pos = bid.get('bidder')
        
        # Am I on the defending team (opponent bid)?
        partner_pos = self._get_partner_pos_name(ctx.position)
        is_defending = (bidder_pos != ctx.position and bidder_pos != partner_pos)
        
        if not is_defending:
            return {"action": "PASS", "reasoning": "Our team bid — no double"}
        
        # Evaluate our defensive strength
        if bid_type == 'SUN':
            # Count Aces (key to blocking Sun)
            aces = sum(1 for c in ctx.hand if c.rank == 'A')
            tens = sum(1 for c in ctx.hand if c.rank == '10')
            
            # 3+ Aces = they can't win most tricks
            if aces >= 3:
                return {"action": "DOUBLE", "reasoning": f"Punishing Sun: {aces} Aces"}
            
            # 2 Aces + strong supporting honors
            if aces >= 2 and tens >= 2:
                return {"action": "DOUBLE", "reasoning": f"Punishing Sun: {aces}A + {tens}×10"}
                
        elif bid_type == 'HOKUM':
            trump = bid.get('suit')
            if trump:
                # Count our trumps
                my_trumps = [c for c in ctx.hand if c.suit == trump]
                trump_ranks = [c.rank for c in my_trumps]
                
                # Holding J or 9 of trump = we control the trump suit
                has_j = 'J' in trump_ranks
                has_9 = '9' in trump_ranks
                
                if has_j and has_9:
                    return {"action": "DOUBLE", "reasoning": f"Punishing Hokum: We hold J+9 of {trump}"}
                
                if has_j and len(my_trumps) >= 3:
                    return {"action": "DOUBLE", "reasoning": f"Trump wall: J + {len(my_trumps)} trumps"}
        
        return {"action": "PASS", "reasoning": "Not strong enough to double"}

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

    # ═══════════════════════════════════════════════════
    #  SUN STRENGTH EVALUATION
    # ═══════════════════════════════════════════════════
    
    def calculate_sun_strength(self, hand):
        """
        Advanced Sun hand evaluation.
        Analyzes: quick tricks, suit quality, stoppers, distribution, projects.
        Score roughly 0-50+. Threshold ~22 to bid.
        """
        score = 0
        
        # Group cards by suit
        suits = {}
        for c in hand:
            suits.setdefault(c.suit, []).append(c)
        
        # ── QUICK TRICKS ──
        # Each suit is evaluated for guaranteed winning tricks
        quick_tricks = 0
        for s, cards in suits.items():
            ranks = [c.rank for c in cards]
            
            if 'A' in ranks:
                quick_tricks += 1  # Ace = 1 guaranteed trick
                if 'K' in ranks:
                    quick_tricks += 0.5  # A-K = 1.5 tricks (K protected by A)
                if '10' in ranks:
                    quick_tricks += 0.5  # A-10 = Ace protects 10
            elif 'K' in ranks:
                # Unprotected King — risky, only half a trick
                if len(cards) >= 2:
                    quick_tricks += 0.5  # K with length = some chance
                # K alone in a suit = loser (opponent leads Ace)
        
        score += quick_tricks * 6  # Each quick trick ≈ 6 points of score
        
        # ── HIGH CARD POINTS ──
        rank_values = {'A': 5, '10': 4, 'K': 3, 'Q': 2, 'J': 1}
        hcp = sum(rank_values.get(c.rank, 0) for c in hand)
        score += hcp
        
        # ── SUIT QUALITY ──
        for s, cards in suits.items():
            ranks = [c.rank for c in cards]
            length = len(cards)
            
            # Long suit bonus — 4+ cards in a suit creates extra tricks
            if length >= 5:
                score += 4  # Very long suit, lots of tricks
            elif length >= 4:
                score += 2  # Good length
            
            # Isolated honors penalty — Q or K alone in a suit
            if length == 1:
                if ranks[0] in ['K', 'Q']:
                    score -= 3  # Bare King/Queen = loser
                elif ranks[0] in ['10']:
                    score -= 2  # Bare 10 = likely loser
                elif ranks[0] in ['7', '8', '9']:
                    score -= 1  # Singleton low = gets trumped (but this is Sun)
            
            # Honor combinations
            if 'A' in ranks and 'K' in ranks and '10' in ranks:
                score += 3  # A-K-10 = commanding suit
            elif 'A' in ranks and 'K' in ranks:
                score += 2  # A-K = solid control
            elif 'K' in ranks and 'Q' in ranks:
                score += 1  # K-Q = some control
            
            # Unguarded suits penalty (no honor at all in a 2-card suit)
            if length == 2 and not any(r in ['A', 'K', 'Q'] for r in ranks):
                score -= 1  # Doubleton with no honors
        
        # ── STOPPER COUNT ──
        # Suits where we can stop opponent's leads
        stoppers = 0
        for s, cards in suits.items():
            ranks = [c.rank for c in cards]
            if 'A' in ranks:
                stoppers += 1
            elif 'K' in ranks and len(cards) >= 2:
                stoppers += 1  # K with cover
            elif 'Q' in ranks and len(cards) >= 3:
                stoppers += 1  # Q with double cover
        
        if stoppers >= 4:
            score += 4  # All suits stopped — safe Sun hand
        elif stoppers >= 3:
            score += 2
        elif stoppers <= 1:
            score -= 3  # Too many exposed suits
        
        # ── PROJECTS ──
        from game_engine.logic.utils import scan_hand_for_projects
        projects = scan_hand_for_projects(hand, 'SUN')
        if projects:
             for p in projects:
                  raw_val = p.get('score', 0)
                  if raw_val >= 100:
                      score += 6  # Strong project bonus
                  elif raw_val >= 50:
                      score += 3
        
        # ── 4-OF-A-KIND BONUSES ──
        ranks_list = [c.rank for c in hand]
        if ranks_list.count('A') >= 3: score += 4
        if ranks_list.count('A') == 4: score += 8  # 4 Aces = dominant
        if ranks_list.count('10') >= 3: score += 2
        
        return max(0, score)

    # ═══════════════════════════════════════════════════
    #  HOKUM STRENGTH EVALUATION
    # ═══════════════════════════════════════════════════
    
    def calculate_hokum_strength(self, hand, trump_suit):
        """
        Advanced Hokum hand evaluation.
        Analyzes: trump power, trump length, distribution, side aces, losers.
        Score roughly 0-50+. Threshold ~18 to bid.
        """
        score = 0
        
        # Group cards by suit
        suits = {}
        for c in hand:
            suits.setdefault(c.suit, []).append(c)
        
        my_trumps = suits.get(trump_suit, [])
        trump_ranks = [c.rank for c in my_trumps]
        trump_count = len(my_trumps)
        
        # ── TRUMP POWER ──
        # J (20pts, rank 1) and 9 (14pts, rank 2) are the kings of Hokum
        has_j = 'J' in trump_ranks
        has_9 = '9' in trump_ranks
        has_a = 'A' in trump_ranks
        has_10 = '10' in trump_ranks
        has_k = 'K' in trump_ranks
        
        # Individual trump values
        if has_j:  score += 12  # Jack of trump = dominant
        if has_9:  score += 10  # 9 of trump = second strongest
        if has_a:  score += 5   # Ace of trump 
        if has_10: score += 4   # 10 of trump (high points)
        if has_k:  score += 2   # King of trump
        
        # ── TRUMP COMBOS ──
        if has_j and has_9:
            score += 6  # J-9 combo = near-unstoppable trump control
        if has_j and has_9 and has_a:
            score += 4  # J-9-A = completely dominant (extra bonus)
        if has_j and has_a and not has_9:
            score += 2  # J-A = strong but missing 9
        
        # ── TRUMP LENGTH ──
        if trump_count >= 5:
            score += 6  # 5+ trumps = can always ruff
        elif trump_count >= 4:
            score += 4  # 4 trumps = solid base
        elif trump_count >= 3:
            score += 2  # 3 trumps = minimum
        elif trump_count == 2:
            score -= 2  # Only 2 trumps = risky
        elif trump_count <= 1:
            score -= 8  # 0-1 trumps = terrible for Hokum
        
        # ── SIDE ACES ──
        # Non-trump Aces = guaranteed tricks that don't cost trumps
        side_aces = sum(1 for c in hand if c.rank == 'A' and c.suit != trump_suit)
        score += side_aces * 5  # Each side Ace = 5 points (very valuable)
        
        # Side Kings with Aces = extra strength
        for s, cards in suits.items():
            if s == trump_suit: continue
            ranks = [c.rank for c in cards]
            if 'A' in ranks and 'K' in ranks:
                score += 2  # A-K in same side suit = 2 tricks
            elif 'A' in ranks and '10' in ranks:
                score += 1  # A-10 in same side suit
        
        # ── DISTRIBUTION (Voids & Singletons) ──
        # Short side suits = can ruff with trumps
        for s in SUITS:
            if s == trump_suit: continue
            count = len(suits.get(s, []))
            if count == 0:
                score += 4  # Void = can ruff immediately
            elif count == 1:
                score += 2  # Singleton = ruff after 1 round
                # Singleton Ace is best — win the trick then ruff next
                singleton = suits[s][0] if suits.get(s) else None
                if singleton and singleton.rank == 'A':
                    score += 2  # Singleton Ace = win trick then void!
        
        # ── LOSER COUNT (inverted) ──
        # Count expected losing cards
        losers = 0
        for s, cards in suits.items():
            if s == trump_suit:
                # Trump losers = cards below J-9-A that aren't in the top
                for c in cards:
                    if c.rank in ['7', '8']:
                        losers += 0.5  # Low trumps sometimes lose
            else:
                ranks = [c.rank for c in cards]
                length = len(cards)
                if length == 0:
                    continue  # Void = good
                elif length == 1:
                    if ranks[0] not in ['A']:
                        losers += 1  # Singleton non-ace = loser
                elif length >= 2:
                    # Each card beyond the first that isn't A/K is a potential loser
                    covered = 0
                    if 'A' in ranks: covered += 1
                    if 'K' in ranks and length >= 2: covered += 1
                    losers += max(0, min(3, length - covered))  # Cap at 3 losers per suit
        
        # Low losers = strong hand
        if losers <= 2:
            score += 4
        elif losers <= 3:
            score += 2
        elif losers >= 6:
            score -= 4
        
        # ── PROJECTS ──
        from game_engine.logic.utils import scan_hand_for_projects
        projects = scan_hand_for_projects(hand, 'HOKUM')
        if projects:
             for p in projects:
                  raw_val = p.get('score', 0)
                  score += (raw_val / 10)  # 100-point project ≈ +10
        
        return max(0, score)
