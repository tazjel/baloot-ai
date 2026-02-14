from ai_worker.strategies.components.base import StrategyComponent
from ai_worker.bot_context import BotContext
from game_engine.models.constants import POINT_VALUES_HOKUM, ORDER_HOKUM, ORDER_SUN
from ai_worker.strategies.components.signaling import (
    get_role, should_attempt_kaboot, should_break_kaboot,
    get_barqiya_response
)
from ai_worker.strategies.components.follow_optimizer import optimize_follow
from ai_worker.strategies.components.lead_selector import select_lead
from ai_worker.strategies.components.opponent_model import model_opponents
from ai_worker.strategies.components.trick_review import review_tricks
from ai_worker.strategies.components.cooperative_play import get_cooperative_lead, get_cooperative_follow
from ai_worker.strategies.components.bid_reader import infer_from_bids
from ai_worker.strategies.components.galoss_guard import galoss_check, get_emergency_action
import logging

logger = logging.getLogger(__name__)


class HokumStrategy(StrategyComponent):
    """Handles all Hokum mode playing logic (lead and follow)."""

    def get_decision(self, ctx: BotContext) -> dict | None:
        # ENDGAME SOLVER: Perfect play when ≤3 cards remain
        if len(ctx.hand) <= 3:
            endgame = self._try_endgame(ctx)
            if endgame:
                return endgame

        # ── Bayesian suit probabilities for opponents ──
        partner_pos = self.get_partner_pos(ctx.player_index)
        _suit_probs: dict[str, dict[str, float]] | None = None
        try:
            if ctx.memory and hasattr(ctx.memory, 'suit_probability') and ctx.memory.suit_probability:
                opp_positions = [p.get('position') for p in ctx.raw_state.get('players', [])
                                 if p.get('position') not in (ctx.position, partner_pos)]
                _suit_probs = {pos: ctx.memory.suit_probability.get(pos, {})
                               for pos in opp_positions if pos}
        except Exception:
            pass

        # ── TRICK REVIEW: Mid-round strategy adaptation ──
        self._trick_review = None
        try:
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            partner_pos = self.get_partner_pos(ctx.player_index)
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            self._trick_review = review_tricks(
                my_position=ctx.position, trick_history=tricks,
                mode='HOKUM', trump_suit=ctx.trump, we_are_buyers=(bidder_team == 'us'),
            )
            logger.debug(f"[TRICK_REVIEW] {self._trick_review['momentum']} {self._trick_review['our_tricks']}-{self._trick_review['their_tricks']} shift={self._trick_review['strategy_shift']}")
        except Exception as e:
            logger.debug(f"Trick review skipped: {e}")

        # ── OPPONENT MODEL: Threat assessment ──
        self._opp_model = None
        try:
            bid_hist = ctx.raw_state.get('bidHistory', [])
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            self._opp_model = model_opponents(
                my_position=ctx.position, bid_history=bid_hist,
                trick_history=tricks, mode='HOKUM', trump_suit=ctx.trump,
            )
            logger.debug(f"[OPP_MODEL] danger={self._opp_model['combined_danger']} safe={self._opp_model['safe_lead_suits']} avoid={self._opp_model['avoid_lead_suits']}")
        except Exception as e:
            logger.debug(f"Opponent model skipped: {e}")

        # ── BRAIN: Cross-module orchestration ──
        try:
            from ai_worker.strategies.components.brain import consult_brain
            trump = ctx.trump
            partner_pos = self.get_partner_pos(ctx.player_index)
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]
            table_dicts = []
            for tc in (ctx.table_cards or []):
                tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
                if isinstance(tc_card, dict):
                    table_dicts.append(tc_card)
                elif hasattr(tc_card, 'rank'):
                    table_dicts.append({"rank": tc_card.rank, "suit": tc_card.suit})
            voids: dict[str, list[str]] = {}
            for s in ['♠', '♥', '♦', '♣']:
                void_players = []
                for p in ctx.raw_state.get('players', []):
                    pos = p.get('position')
                    if pos and ctx.is_player_void(pos, s):
                        void_players.append(pos)
                if void_players:
                    voids[s] = void_players
            pi = None
            if hasattr(ctx, 'read_partner_info'):
                try:
                    pi = ctx.read_partner_info()
                except Exception:
                    pass
            brain = consult_brain(
                hand=ctx.hand, table_cards=table_dicts, mode='HOKUM',
                trump_suit=trump, position=ctx.position,
                we_are_buyers=(bidder_team == 'us'),
                partner_winning=ctx.is_partner_winning(),
                tricks_played=len(tricks), tricks_won_by_us=our_wins,
                master_indices=master_idx, tracker_voids=voids,
                partner_info=pi,
                legal_indices=ctx.get_legal_moves(),
                opponent_info=self._opp_model,
                trick_review_info=self._trick_review,
            )
            logger.debug(f"[BRAIN] conf={brain['confidence']} modules={brain['modules_consulted']} → {brain['reasoning']}")
            if brain['recommendation'] is not None and brain['confidence'] >= 0.7:
                return {"action": "PLAY", "cardIndex": brain['recommendation'],
                        "reasoning": f"BRAIN({brain['confidence']}): {brain['reasoning']}"}
        except Exception as e:
            logger.debug(f"Brain skipped: {e}")

        # ── GALOSS GUARD: Emergency mode detection ──
        self._galoss = None
        try:
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            partner_pos = self.get_partner_pos(ctx.player_index)
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            their_wins = len(tricks) - our_wins
            our_pts = sum(t.get('points', 0) for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            their_pts = sum(t.get('points', 0) for t in tricks if t.get('winner') not in (ctx.position, partner_pos))
            self._galoss = galoss_check(
                mode='HOKUM', we_are_buyers=(bidder_team == 'us'),
                tricks_played=len(tricks), our_points=our_pts, their_points=their_pts,
                our_tricks=our_wins, their_tricks=their_wins,
            )
            if self._galoss['emergency_mode']:
                logger.debug(f"[GALOSS] {self._galoss['risk_level']}: {self._galoss['reasoning']}")
                legal = ctx.get_legal_moves()
                is_leading = not ctx.table_cards
                emer = get_emergency_action(
                    hand=ctx.hand, legal_indices=legal, mode='HOKUM',
                    trump_suit=ctx.trump, we_are_buyers=(bidder_team == 'us'),
                    galoss_info=self._galoss, is_leading=is_leading,
                    partner_winning=ctx.is_partner_winning() if not is_leading else False,
                )
                if emer:
                    return {"action": "PLAY", "cardIndex": emer['card_index'],
                            "reasoning": f"Galoss/{emer['strategy']}: {emer['reasoning']}"}
        except Exception as e:
            logger.debug(f"Galoss guard skipped: {e}")

        if not ctx.table_cards:
            return self._get_hokum_lead(ctx)
        else:
            return self._get_hokum_follow(ctx)

    def _try_endgame(self, ctx: BotContext) -> dict | None:
        """Attempt minimax solve using ML or heuristic hand reconstruction."""
        try:
            from ai_worker.strategies.components.endgame_solver import solve_endgame
            known = ctx.guess_hands()
            if not known:
                return None
            leader = ctx.position if not ctx.table_cards else ctx.table_cards[0]['playedBy']
            result = solve_endgame(
                my_hand=ctx.hand,
                known_hands=known,
                my_position=ctx.position,
                leader_position=leader,
                mode=ctx.mode or 'HOKUM',
                trump_suit=ctx.trump,
            )
            if result and result.get('reasoning', '').startswith('Minimax'):
                return {"action": "PLAY", "cardIndex": result['cardIndex'],
                        "reasoning": f"Endgame Solver: {result['reasoning']}"}
        except Exception as e:
            logger.debug(f"Endgame solver skipped: {e}")
        return None

    def _get_hokum_lead(self, ctx: BotContext):
        best_card_idx = 0
        max_score = -100
        trump = ctx.trump

        # Determine if we (or partner) bought the project.
        bidder_team = 'us' if ctx.bid_winner in [ctx.position, self.get_partner_pos(ctx.player_index)] else 'them'

        # DEFENSIVE LEAD: When opponents won the bid, switch to defensive strategy
        if bidder_team == 'them':
            # KABOOT BREAKER: If opponents are sweeping, prioritize winning 1 trick
            if should_break_kaboot(ctx):
                for i, c in enumerate(ctx.hand):
                    if ctx.is_master_card(c):
                        return {"action": "PLAY", "cardIndex": i,
                                "reasoning": "KABOOT BREAKER: Leading master to deny sweep"}

            defensive = self._get_defensive_lead_hokum(ctx)
            if defensive:
                return defensive

        # ── KABOOT PURSUIT: Intelligent sweep strategy ──
        if bidder_team == 'us' and should_attempt_kaboot(ctx):
            from ai_worker.strategies.components.kaboot_pursuit import pursue_kaboot
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            partner_pos = self.get_partner_pos(ctx.player_index)
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]
            kp = pursue_kaboot(
                hand=ctx.hand, mode='HOKUM', trump_suit=trump,
                tricks_won_by_us=our_wins, tricks_played=len(tricks),
                master_cards=master_idx, partner_is_leading=False,
            )
            logger.debug(f"[KABOOT] {kp['status']}: {kp['reasoning']}")
            if kp['status'] in ('PURSUING', 'LOCKED') and kp['play_index'] is not None:
                return {"action": "PLAY", "cardIndex": kp['play_index'],
                        "reasoning": f"KABOOT {kp['status']}: {kp['reasoning']}"}

        # CHECK PARTNER SIGNALS (Hokum-specific)
        signal = self._check_partner_signals(ctx)
        if signal:
            # Handle Barqiya (urgent call) with timing awareness
            if signal.get('type') == 'URGENT_CALL':
                legal = ctx.get_legal_moves()
                barq = get_barqiya_response(ctx, signal, legal)
                if barq:
                    return barq
            elif signal.get('type') in ('ENCOURAGE', 'CONFIRMED_POSITIVE'):
                target_suit = signal.get('suit')
                if target_suit:
                    for i, c in enumerate(ctx.hand):
                        if c.suit == target_suit:
                            return {"action": "PLAY", "cardIndex": i,
                                    "reasoning": f"Answering partner signal: Lead {target_suit}"}

        # ── COOPERATIVE LEAD: Partner-aware lead override ──
        try:
            _pi = None
            if hasattr(ctx, 'read_partner_info'):
                try: _pi = ctx.read_partner_info()
                except Exception: pass
            if _pi:
                tricks = ctx.raw_state.get('currentRoundTricks', [])
                coop = get_cooperative_lead(
                    hand=ctx.hand, partner_info=_pi, mode='HOKUM',
                    trump_suit=trump, tricks_remaining=8 - len(tricks),
                    we_are_buyers=(bidder_team == 'us'),
                )
                if coop and coop.get('confidence', 0) >= 0.6:
                    logger.debug(f"[COOP_LEAD] {coop['strategy']}({coop['confidence']:.0%}): {coop['reasoning']}")
                    return {"action": "PLAY", "cardIndex": coop['card_index'],
                            "reasoning": f"CoopLead/{coop['strategy']}: {coop['reasoning']}"}
        except Exception as e:
            logger.debug(f"Cooperative lead skipped: {e}")

        # ── TRUMP MANAGEMENT ENGINE ──
        from ai_worker.strategies.components.trump_manager import manage_trumps

        my_trump_count = sum(1 for c in ctx.hand if c.suit == trump)
        my_team = ctx.team
        partner_pos = self.get_partner_pos(ctx.player_index)

        # Estimate enemy trumps using Bayesian probabilities + CardTracker
        enemy_void_suits = []
        partner_void_suits = []
        partner_trump_prob = 0.0
        for p in ctx.raw_state.get('players', []):
            pos = p.get('position')
            if p.get('team') != my_team:
                for s in ['♠', '♥', '♦', '♣']:
                    if s != trump and ctx.is_player_void(pos, s):
                        enemy_void_suits.append(s)
            elif pos == partner_pos:
                partner_trump_prob = ctx.memory.get_suit_probability(pos, trump)
                for s in ['♠', '♥', '♦', '♣']:
                    if s != trump and ctx.is_player_void(pos, s):
                        partner_void_suits.append(s)
        # Use CardTracker for precise remaining trump count (all unseen trumps)
        total_unseen_trumps = ctx.tracker.count_remaining_trump(trump)
        # Estimate partner trumps from Bayesian probability
        partner_trump_est = round(partner_trump_prob * min(total_unseen_trumps, 3))
        # Enemy trumps = total unseen minus estimated partner trumps
        remaining_enemy_trumps = max(0, total_unseen_trumps - partner_trump_est)

        tricks = ctx.raw_state.get('currentRoundTricks', [])
        tplan = manage_trumps(
            hand=ctx.hand, trump_suit=trump, my_trumps=my_trump_count,
            enemy_trumps_estimate=remaining_enemy_trumps,
            partner_trumps_estimate=partner_trump_est,
            tricks_played=len(tricks), we_are_buyers=(bidder_team == 'us'),
            partner_void_suits=partner_void_suits,
            enemy_void_suits=enemy_void_suits,
        )
        logger.debug(f"[TRUMP] {tplan['action']} phase={tplan.get('phase', '?')}: {tplan['reasoning']}")
        should_open_trump = tplan['lead_trump']
        ruffable_suits = set(enemy_void_suits)

        # ── TRUMP TIMING: CASH_SIDES phase override ──
        # When trump manager says cash side winners, lead Aces/Kings from safe suits
        if tplan.get('phase') == 'CASH_SIDES':
            cash_suits = tplan.get('side_winner_suits', [])
            for cs in cash_suits:
                for i, c in enumerate(ctx.hand):
                    if c.suit == cs and c.rank == 'A':
                        return {"action": "PLAY", "cardIndex": i,
                                "reasoning": f"Trump Timing Phase 2: Cash {c.rank}{cs} before enemy ruffs"}
            for cs in cash_suits:
                for i, c in enumerate(ctx.hand):
                    if c.suit == cs and c.rank == 'K':
                        return {"action": "PLAY", "cardIndex": i,
                                "reasoning": f"Trump Timing Phase 2: Cash {c.rank}{cs} (protected by Ace lead)"}
            logger.debug("[TRUMP] CASH_SIDES phase but no side winners found — falling through")

        # ── LEAD SELECTOR: Consult specialized lead module ──
        try:
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]
            # Collect opponent voids
            _opp_voids: dict[str, set] = {}
            for s in ['♠', '♥', '♦', '♣']:
                for p in ctx.raw_state.get('players', []):
                    if p.get('team') != my_team and ctx.is_player_void(p.get('position'), s):
                        _opp_voids.setdefault(s, set()).add(p.get('position'))
            # Partner read
            _pi = None
            if hasattr(ctx, 'read_partner_info'):
                try:
                    _pi = ctx.read_partner_info()
                except Exception:
                    pass
            # Merge opponent model's avoid suits into voids for lead_selector
            if self._opp_model:
                for avoid_s in self._opp_model.get('avoid_lead_suits', []):
                    if avoid_s not in _opp_voids:
                        _opp_voids[avoid_s] = {'opp_model'}
            # Merge trick_review avoid_suits into voids
            if self._trick_review:
                for avoid_s in self._trick_review.get('avoid_suits', []):
                    if avoid_s not in _opp_voids:
                        _opp_voids[avoid_s] = {'trick_review'}
            # ── BID INFERENCE: Use bid history for card reading ──
            try:
                bid_hist = ctx.raw_state.get('bidHistory', [])
                _fc = ctx.floor_card
                _fc_dict = {'suit': _fc.suit, 'rank': _fc.rank} if _fc else None
                bid_reads = infer_from_bids(
                    my_position=ctx.position, bid_history=bid_hist,
                    floor_card=_fc_dict, bidding_round=ctx.bidding_round,
                )
                for avoid_s in bid_reads.get('avoid_suits', []):
                    if avoid_s not in _opp_voids:
                        _opp_voids[avoid_s] = {'bid_reader'}
                logger.debug(f"[BID_READ] decl={bid_reads.get('declarer_position')} avoid={bid_reads.get('avoid_suits')} target={bid_reads.get('target_suits')}")
            except Exception as e:
                logger.debug(f"Bid reader skipped: {e}")
            # Build defense_info from opponent model
            _def_info = None
            if self._opp_model and not (bidder_team == 'us'):
                safe = self._opp_model.get('safe_lead_suits', [])
                _def_info = {
                    'priority_suit': safe[0] if safe else None,
                    'avoid_suit': self._opp_model.get('avoid_lead_suits', [None])[0] if self._opp_model.get('avoid_lead_suits') else None,
                    'reasoning': self._opp_model.get('reasoning', ''),
                }
            ls_result = select_lead(
                hand=ctx.hand, mode='HOKUM', trump_suit=trump,
                we_are_buyers=(bidder_team == 'us'),
                tricks_played=len(tricks), tricks_won_by_us=our_wins,
                master_indices=master_idx, partner_info=_pi,
                defense_info=_def_info, trump_info=tplan,
                opponent_voids=_opp_voids,
                suit_probs=_suit_probs,
            )
            # Adjust confidence threshold based on trick_review strategy_shift
            _ls_threshold = 0.65
            if self._trick_review:
                shift = self._trick_review.get('strategy_shift', 'NONE')
                if shift == 'AGGRESSIVE':
                    _ls_threshold = 0.50
                elif shift == 'DAMAGE_CONTROL':
                    _ls_threshold = 0.75
            if ls_result and ls_result.get('confidence', 0) >= _ls_threshold:
                logger.debug(f"[LEAD_SEL] {ls_result['strategy']}({ls_result['confidence']:.0%}): {ls_result['reasoning']}")
                return {"action": "PLAY", "cardIndex": ls_result['card_index'],
                        "reasoning": f"LeadSel/{ls_result['strategy']}: {ls_result['reasoning']}"}
        except Exception as e:
            logger.debug(f"Lead selector skipped: {e}")

        for i, c in enumerate(ctx.hand):
            score = 0
            is_trump = (c.suit == trump)
            is_master = ctx.is_master_card(c)

            # VOID AVOIDANCE: Check if opponents are void in this suit
            is_danger = False
            if not is_trump:
                for p in ctx.raw_state.get('players', []):
                    if p.get('team') != my_team:
                        if ctx.is_player_void(p.get('position'), c.suit):
                            is_danger = True
                            break

            if is_trump:
                if should_open_trump:
                    score += 40

                master_bonus = 100
                if not (remaining_enemy_trumps > 0):
                    master_bonus = 10  # Save for ruffing

                if is_master:
                    score += master_bonus
                elif c.rank == 'J':
                    if should_open_trump:
                        score += 80
                    else:
                        score += 10
                elif c.rank == '9':
                    if should_open_trump:
                        score += 60
                    else:
                        score += 5
                else:
                    score += 10
            else:
                # Non-Trump
                if is_master:
                    score += 50
                elif c.rank == 'A':
                    score += 30
                else:
                    has_ace = any(x.rank == 'A' and x.suit == c.suit for x in ctx.hand)
                    if not has_ace:
                        if c.rank == 'K': score -= 15
                        elif c.rank == 'Q': score -= 10
                        elif c.rank == 'J': score -= 5

                if is_danger:
                    score -= 200  # NUCLEAR DETERRENT

                # CROSS-RUFF PENALTY: If this suit is ruffable, heavy penalty
                if c.suit in ruffable_suits:
                    score -= 50

                # CARD COUNTING: Use memory to check remaining cards
                if ctx.memory:
                    remaining = ctx.memory.get_remaining_in_suit(c.suit)
                    remaining_ranks = [r['rank'] for r in remaining if r['rank'] != c.rank]
                    
                    # Penalize leading non-masters into contested suits
                    if not is_master and remaining_ranks:
                        higher_exists = False
                        for r in remaining_ranks:
                            try:
                                from game_engine.models.constants import ORDER_SUN
                                if ORDER_SUN.index(r) > ORDER_SUN.index(c.rank):
                                    higher_exists = True
                                    break
                            except ValueError:
                                continue
                        if higher_exists:
                            score -= 10
                    
                    # SINGLETON DANGER: A lone non-master card gets eaten
                    suit_count = sum(1 for x in ctx.hand if x.suit == c.suit)
                    if suit_count == 1 and not is_master:
                        score -= 20  # Lone card that can't win

                # SUIT LENGTH: Prefer leading from long suits
                suit_count = sum(1 for x in ctx.hand if x.suit == c.suit)
                score += suit_count * 3

            if score > max_score:
                max_score = score
                best_card_idx = i

        reason = "Hokum Lead"
        if ctx.is_master_card(ctx.hand[best_card_idx]):
            reason = "Leading Master Card"
        if ctx.hand[best_card_idx].suit == trump and should_open_trump:
            reason = "Smart Sahn (Drawing Trumps)"

        return {"action": "PLAY", "cardIndex": best_card_idx, "reasoning": reason}

    def _get_defensive_lead_hokum(self, ctx: BotContext):
        """Defensive lead when OPPONENTS won the Hokum bid.
        Strategy: Lead suits to create ruff opportunities, avoid feeding declarer."""
        from ai_worker.strategies.components.defense_plan import plan_defense
        trump = ctx.trump

        # Consult defensive planner for strategy guidance
        tricks = ctx.raw_state.get('currentRoundTricks', [])
        partner_pos = self.get_partner_pos(ctx.player_index)
        our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
        their_wins = len(tricks) - our_wins
        # Collect buyer's void suits from CardTracker for defense_plan
        buyer_void_suits = []
        buyer_pos = ctx.bid_winner or ''
        if buyer_pos:
            for s in ['♠', '♥', '♦', '♣']:
                if ctx.is_player_void(buyer_pos, s):
                    buyer_void_suits.append(s)
        dplan = plan_defense(
            my_hand=ctx.hand, mode='HOKUM', trump_suit=trump,
            buyer_position=buyer_pos, partner_position=partner_pos,
            tricks_played=len(tricks), tricks_won_by_us=our_wins, tricks_won_by_them=their_wins,
            void_suits=buyer_void_suits,
        )
        logger.debug(f"[DEFENSE] {dplan['reasoning']}")

        best_idx = 0
        max_score = -100

        # Suit analysis
        suit_lengths = {}
        for s in ['♠', '♥', '♦', '♣']:
            suit_lengths[s] = sum(1 for c in ctx.hand if c.suit == s)

        # Check how many trumps WE have
        my_trump_count = suit_lengths.get(trump, 0)

        for i, c in enumerate(ctx.hand):
            score = 0
            is_trump = (c.suit == trump)
            is_master = ctx.is_master_card(c)
            length = suit_lengths.get(c.suit, 0)

            if is_trump:
                # DON'T lead trumps on defense — that helps declarer!
                # Exception: if we have J-9 (strongest trumps), lead to force their trumps out
                if c.rank in ['J', '9'] and my_trump_count >= 3:
                    score += 20  # We can afford to draw trumps with dominant position
                else:
                    score -= 40  # Don't waste trumps on defense
            else:
                # Non-trump leads
                if is_master:
                    # Cash masters immediately — before declarer can ruff them
                    score += 70
                    if length <= 2:
                        score += 20  # Short-suit master = cash and get void fast

                # PRIORITY: Lead SHORT suits to create ruff opportunities
                if length == 1 and not is_master:
                    score += 35  # Singleton — void yourself, ruff next time!
                elif length == 2 and not is_master:
                    score += 20  # Doubleton

                # PENALTY: Don't lead bare honors into declarer's strength
                if c.rank == 'K' and not any(x.rank == 'A' and x.suit == c.suit for x in ctx.hand):
                    score -= 25  # Bare King eaten by Ace
                if c.rank in ['10', 'A'] and not is_master:
                    score -= 10  # Don't gift big points

                # BONUS: Lead suits where opponents are void (partner might ruff!)
                my_team = ctx.team
                partner_pos = self.get_partner_pos(ctx.player_index)
                partner_might_ruff = False
                for p in ctx.raw_state.get('players', []):
                    if p.get('position') == partner_pos:
                        if ctx.is_player_void(partner_pos, c.suit):
                            # Partner is void in this suit and might have trumps!
                            if not ctx.is_player_void(partner_pos, trump):
                                partner_might_ruff = True
                if partner_might_ruff:
                    score += 40  # Feed partner a ruff opportunity!

            if score > max_score:
                max_score = score
                best_idx = i

        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Defensive Lead (Hokum)"}

    def _get_hokum_follow(self, ctx: BotContext):
        lead_suit = ctx.lead_suit
        winning_card = ctx.winning_card
        winner_pos = ctx.winner_pos
        trump = ctx.trump

        follows = [i for i, c in enumerate(ctx.hand) if c.suit == lead_suit]

        # SEAT-AWARE POSITIONAL PLAY
        seat = len(ctx.table_cards) + 1  # 2nd, 3rd, or 4th seat
        is_last_to_play = (seat == 4)
        
        # POINT DENSITY: Evaluate trick's point value
        from ai_worker.strategies.components.point_density import evaluate_trick_value
        _table_dicts = []
        for tc in ctx.table_cards:
            tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
            if isinstance(tc_card, dict):
                _table_dicts.append(tc_card)
            elif hasattr(tc_card, 'rank'):
                _table_dicts.append({"rank": tc_card.rank, "suit": tc_card.suit})
        _trick_ev = evaluate_trick_value(_table_dicts, 'HOKUM')
        trick_points = _trick_ev['current_points']
        logger.debug(f"[POINTS] {_trick_ev['density']} ({trick_points}pts, {_trick_ev['point_cards_on_table']} pt-cards)")

        # ── COOPERATIVE FOLLOW: Partner-aware follow override ──
        try:
            _pi = None
            if hasattr(ctx, 'read_partner_info'):
                try: _pi = ctx.read_partner_info()
                except Exception: pass
            if _pi:
                partner_pos = self.get_partner_pos(ctx.player_index)
                is_partner_winning = (winner_pos == partner_pos)
                coop_f = get_cooperative_follow(
                    hand=ctx.hand, legal_indices=follows if follows else list(range(len(ctx.hand))),
                    partner_info=_pi, led_suit=lead_suit, mode='HOKUM',
                    trump_suit=trump, partner_winning=is_partner_winning,
                    trick_points=trick_points,
                )
                if coop_f and coop_f.get('confidence', 0) >= 0.6:
                    logger.debug(f"[COOP_FOLLOW] {coop_f['tactic']}({coop_f['confidence']:.0%}): {coop_f['reasoning']}")
                    return {"action": "PLAY", "cardIndex": coop_f['card_index'],
                            "reasoning": f"CoopFollow/{coop_f['tactic']}: {coop_f['reasoning']}"}
        except Exception as e:
            logger.debug(f"Cooperative follow skipped: {e}")

        # 1. Void Clause
        if not follows:
            has_trumps = any(c.suit == trump for c in ctx.hand)
            partner_pos = self.get_partner_pos(ctx.player_index)
            is_partner_winning = (winner_pos == partner_pos)

            if has_trumps and not is_partner_winning:
                trumps = [i for i, c in enumerate(ctx.hand) if c.suit == trump]

                if winning_card.suit == trump:
                    over_trumps = [i for i in trumps if ctx._compare_ranks(ctx.hand[i].rank, winning_card.rank, 'HOKUM')]
                    if over_trumps:
                        best_idx = self.find_lowest_rank_card(ctx, over_trumps, ORDER_HOKUM)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Over-trumping (Economy)"}
                    else:
                        return self.get_trash_card(ctx)
                else:
                    # SMART TRUMPING: Consider trick value and seat position
                    low_trumps = [i for i in trumps if ctx.hand[i].rank in ['7', '8', 'Q', 'K']]
                    high_trumps = [i for i in trumps if ctx.hand[i].rank in ['J', '9', 'A', '10']]
                    
                    if seat == 4:
                        # 4TH SEAT: Guaranteed win — use lowest trump always
                        best_idx = self.find_lowest_rank_card(ctx, trumps, ORDER_HOKUM)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "4th Seat: Guaranteed Trump"}
                    elif seat == 2:
                        # 2ND SEAT: Conservative trumping — only trump high-value tricks
                        if trick_points >= 10 or not high_trumps:
                            if low_trumps:
                                best_idx = self.find_lowest_rank_card(ctx, low_trumps, ORDER_HOKUM)
                                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Cheap Trump (Worth It)"}
                            else:
                                best_idx = self.find_lowest_rank_card(ctx, trumps, ORDER_HOKUM)
                                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Forced Trump"}
                        else:
                            # Low value, partner might handle it — discard instead
                            return self.get_trash_card(ctx)
                    else:
                        # 3RD SEAT: Aggressive trumping
                        if trick_points >= 10 or not high_trumps:
                            best_idx = self.find_lowest_rank_card(ctx, trumps, ORDER_HOKUM)
                            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Eating with Trump"}
                        elif low_trumps:
                            best_idx = self.find_lowest_rank_card(ctx, low_trumps, ORDER_HOKUM)
                            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Cheap Trump Eat"}
                        else:
                            return self.get_trash_card(ctx)
            
            # Partner winning or no trumps — discard smart
            if has_trumps and is_partner_winning:
                return self.get_trash_card(ctx)

            return self.get_trash_card(ctx)

        # 2. Follow Suit Clause
        partner_pos = self.get_partner_pos(ctx.player_index)
        is_partner_winning = (winner_pos == partner_pos)

        if is_partner_winning:
            # ── FOLLOW OPTIMIZER: Partner winning path ──
            try:
                bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
                _fo_table = []
                for tc in ctx.table_cards:
                    tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
                    if isinstance(tc_card, dict):
                        _fo_table.append({"rank": tc_card.get('rank', ''), "suit": tc_card.get('suit', ''), "position": tc.get('playedBy', '')})
                    elif hasattr(tc_card, 'rank'):
                        _fo_table.append({"rank": tc_card.rank, "suit": tc_card.suit, "position": tc.get('playedBy', '')})
                _partner_card_idx = None
                for ti, tc in enumerate(ctx.table_cards):
                    if tc.get('playedBy') == partner_pos:
                        _partner_card_idx = ti
                        break
                tricks = ctx.raw_state.get('currentRoundTricks', [])
                fo_result = optimize_follow(
                    hand=ctx.hand, legal_indices=follows, table_cards=_fo_table,
                    led_suit=lead_suit, mode='HOKUM', trump_suit=trump, seat=seat,
                    partner_winning=True, partner_card_index=_partner_card_idx,
                    trick_points=trick_points, tricks_remaining=8 - len(tricks),
                    we_are_buyers=(bidder_team == 'us'),
                    suit_probs=_suit_probs,
                )
                if fo_result and fo_result.get('confidence', 0) >= 0.6:
                    logger.debug(f"[FOLLOW_OPT] {fo_result['tactic']}({fo_result['confidence']:.0%}): {fo_result['reasoning']}")
                    return {"action": "PLAY", "cardIndex": fo_result['card_index'],
                            "reasoning": f"FollowOpt/{fo_result['tactic']}: {fo_result['reasoning']}"}
            except Exception as e:
                logger.debug(f"Follow optimizer skipped: {e}")
            best_idx = self.find_highest_point_card(ctx, follows, POINT_VALUES_HOKUM)
            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Partner Winning - Feeding"}
        else:
            if winning_card.suit == trump and lead_suit != trump:
                best_idx = self.find_lowest_point_card(ctx, follows, POINT_VALUES_HOKUM)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Enemy Trumping - Point Protection"}

            winners = []
            for idx in follows:
                c = ctx.hand[idx]
                if ctx._compare_ranks(c.rank, winning_card.rank, 'HOKUM'):
                    winners.append(idx)

            if winners:
                # ── FOLLOW OPTIMIZER: Competitive path ──
                try:
                    bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
                    _fo_table = []
                    for tc in ctx.table_cards:
                        tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
                        if isinstance(tc_card, dict):
                            _fo_table.append({"rank": tc_card.get('rank', ''), "suit": tc_card.get('suit', ''), "position": tc.get('playedBy', '')})
                        elif hasattr(tc_card, 'rank'):
                            _fo_table.append({"rank": tc_card.rank, "suit": tc_card.suit, "position": tc.get('playedBy', '')})
                    _partner_card_idx = None
                    for ti, tc in enumerate(ctx.table_cards):
                        if tc.get('playedBy') == partner_pos:
                            _partner_card_idx = ti
                            break
                    tricks = ctx.raw_state.get('currentRoundTricks', [])
                    fo_result = optimize_follow(
                        hand=ctx.hand, legal_indices=follows, table_cards=_fo_table,
                        led_suit=lead_suit, mode='HOKUM', trump_suit=trump, seat=seat,
                        partner_winning=False, partner_card_index=_partner_card_idx,
                        trick_points=trick_points, tricks_remaining=8 - len(tricks),
                        we_are_buyers=(bidder_team == 'us'),
                        suit_probs=_suit_probs,
                    )
                    if fo_result and fo_result.get('confidence', 0) >= 0.6:
                        logger.debug(f"[FOLLOW_OPT] {fo_result['tactic']}({fo_result['confidence']:.0%}): {fo_result['reasoning']}")
                        return {"action": "PLAY", "cardIndex": fo_result['card_index'],
                                "reasoning": f"FollowOpt/{fo_result['tactic']}: {fo_result['reasoning']}"}
                except Exception as e:
                    logger.debug(f"Follow optimizer skipped: {e}")
                if seat == 4:
                    # 4TH SEAT: Guaranteed win — finesse with lowest winner
                    best_idx = self.find_lowest_rank_card(ctx, winners, ORDER_HOKUM)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "4th Seat Finesse"}
                elif seat == 3:
                    # 3RD SEAT: Aggressive — use stronger card for important tricks
                    if trick_points >= 10:
                        best_idx = self.find_best_winner(ctx, winners, ORDER_HOKUM)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Securing Big Trick"}
                    else:
                        best_idx = self.find_lowest_rank_card(ctx, winners, ORDER_HOKUM)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Economy Win"}
                else:
                    # 2ND SEAT: Conservative — only commit masters or high-stakes
                    master_winners = [i for i in winners if ctx.is_master_card(ctx.hand[i])]
                    if master_winners:
                        best_idx = self.find_lowest_rank_card(ctx, master_winners, ORDER_HOKUM)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Playing Master"}
                    elif trick_points >= 15:
                        best_idx = self.find_lowest_rank_card(ctx, winners, ORDER_HOKUM)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: High-Stakes Commit"}
                    else:
                        best_idx = self.find_lowest_point_card(ctx, follows, POINT_VALUES_HOKUM)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Ducking for Partner"}
            else:
                best_idx = self.find_lowest_point_card(ctx, follows, POINT_VALUES_HOKUM)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Ducking (Point Protection)"}

    def _check_partner_signals(self, ctx: BotContext):
        """
        Scan previous tricks for partner discard signals (Hokum-specific).
        
        Hokum additions over Sun:
        - Trump discard by partner = "draw out their trumps" signal
        - Interpret Tahreeb vs Tanfeer context
        """
        tricks = ctx.raw_state.get('currentRoundTricks', [])
        if not tricks:
            return None

        partner_pos = self.get_partner_pos(ctx.player_index)
        trump = ctx.trump

        # Scan recent tricks (most recent first) for partner discards
        for trick in reversed(tricks):
            if not trick.get('cards'):
                continue

            # Find the led suit
            first_card = trick['cards'][0]
            fc = first_card if 'rank' in first_card else first_card.get('card', {})
            led_suit = fc.get('suit')

            # Determine trick winner for Tahreeb/Tanfeer context
            trick_winner = trick.get('winner')

            for i, c_data in enumerate(trick.get('cards', [])):
                c_inner = c_data if 'rank' in c_data else c_data.get('card', {})
                player_pos = c_data.get('playedBy')
                if not player_pos:
                    played_by_list = trick.get('playedBy', [])
                    if i < len(played_by_list):
                        player_pos = played_by_list[i]

                if player_pos != partner_pos:
                    continue

                card_suit = c_inner.get('suit')
                card_rank = c_inner.get('rank')

                # Partner didn't follow suit — this is a signal!
                if card_suit and led_suit and card_suit != led_suit:
                    # Was partner winning when they discarded? (Tahreeb vs Tanfeer)
                    partner_won = (trick_winner == partner_pos)

                    if not partner_won:
                        # TANFEER: Opponent won — partner signaling a want
                        if card_rank == 'A':
                            # BARQIYA! Sacrificing an Ace = urgent call
                            return {'type': 'URGENT_CALL', 'suit': card_suit, 'strength': 'HIGH'}
                        elif card_rank in ('K', 'Q', '10'):
                            return {'type': 'ENCOURAGE', 'suit': card_suit, 'strength': 'MEDIUM'}
                        else:
                            return {'type': 'ENCOURAGE', 'suit': card_suit, 'strength': 'LOW'}
                    else:
                        # TAHREEB: Partner won — partner signaling to avoid
                        return {'type': 'NEGATIVE_DISCARD', 'suit': card_suit}

        return None

