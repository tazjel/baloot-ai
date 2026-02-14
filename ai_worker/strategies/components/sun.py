from ai_worker.strategies.components.base import StrategyComponent
from ai_worker.bot_context import BotContext
from game_engine.models.constants import POINT_VALUES_SUN, ORDER_SUN
from ai_worker.strategies.components.signaling import (
    get_role, should_attempt_kaboot, should_break_kaboot,
    get_barqiya_response, get_ten_management_play
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


class SunStrategy(StrategyComponent):
    """Handles all Sun mode playing logic (lead and follow)."""

    def get_decision(self, ctx: BotContext) -> dict | None:
        partner_pos = self.get_partner_pos(ctx.player_index)

        # ENDGAME SOLVER: Perfect play when ≤3 cards remain
        if len(ctx.hand) <= 3:
            endgame = self._try_endgame(ctx)
            if endgame:
                return endgame

        # ── Bayesian suit probabilities for opponents ──
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
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            self._trick_review = review_tricks(
                my_position=ctx.position, trick_history=tricks,
                mode='SUN', trump_suit=None, we_are_buyers=(bidder_team == 'us'),
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
                trick_history=tricks, mode='SUN', trump_suit=None,
            )
            logger.debug(f"[OPP_MODEL] danger={self._opp_model['combined_danger']} safe={self._opp_model['safe_lead_suits']} avoid={self._opp_model['avoid_lead_suits']}")
        except Exception as e:
            logger.debug(f"Opponent model skipped: {e}")

        # ── BRAIN: Cross-module orchestration ──
        try:
            from ai_worker.strategies.components.brain import consult_brain
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]
            # Build table card dicts
            table_dicts = []
            for tc in (ctx.table_cards or []):
                tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
                if isinstance(tc_card, dict):
                    table_dicts.append(tc_card)
                elif hasattr(tc_card, 'rank'):
                    table_dicts.append({"rank": tc_card.rank, "suit": tc_card.suit})
            # Tracker voids
            voids: dict[str, list[str]] = {}
            for s in ['♠', '♥', '♦', '♣']:
                void_players = []
                for p in ctx.raw_state.get('players', []):
                    pos = p.get('position')
                    if pos and ctx.is_player_void(pos, s):
                        void_players.append(pos)
                if void_players:
                    voids[s] = void_players
            # Partner info
            pi = None
            if hasattr(ctx, 'read_partner_info'):
                try:
                    pi = ctx.read_partner_info()
                except Exception:
                    pass
            brain = consult_brain(
                hand=ctx.hand, table_cards=table_dicts, mode='SUN',
                trump_suit=None, position=ctx.position,
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
            # Calculate points from trick history
            our_pts = sum(t.get('points', 0) for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            their_pts = sum(t.get('points', 0) for t in tricks if t.get('winner') not in (ctx.position, partner_pos))
            self._galoss = galoss_check(
                mode='SUN', we_are_buyers=(bidder_team == 'us'),
                tricks_played=len(tricks), our_points=our_pts, their_points=their_pts,
                our_tricks=our_wins, their_tricks=their_wins,
            )
            if self._galoss['emergency_mode']:
                logger.debug(f"[GALOSS] {self._galoss['risk_level']}: {self._galoss['reasoning']}")
                # Try emergency action
                legal = ctx.get_legal_moves()
                is_leading = not ctx.table_cards
                emer = get_emergency_action(
                    hand=ctx.hand, legal_indices=legal, mode='SUN',
                    trump_suit=None, we_are_buyers=(bidder_team == 'us'),
                    galoss_info=self._galoss, is_leading=is_leading,
                    partner_winning=ctx.is_partner_winning() if not is_leading else False,
                )
                if emer:
                    return {"action": "PLAY", "cardIndex": emer['card_index'],
                            "reasoning": f"Galoss/{emer['strategy']}: {emer['reasoning']}"}
        except Exception as e:
            logger.debug(f"Galoss guard skipped: {e}")

        if not ctx.table_cards:
            # Check for Ashkal Signal first
            ashkal_move = self._check_ashkal_signal(ctx)
            if ashkal_move:
                return ashkal_move
            return self._get_sun_lead(ctx)
        else:
            return self._get_sun_follow(ctx)

    def _try_endgame(self, ctx: BotContext) -> dict | None:
        """Attempt minimax solve using ML or heuristic hand reconstruction."""
        try:
            from ai_worker.strategies.components.endgame_solver import solve_endgame
            known = ctx.guess_hands()
            if not known:
                return None
            # Determine leader: if table is empty, we lead; otherwise first player on table
            leader = ctx.position if not ctx.table_cards else ctx.table_cards[0]['playedBy']
            result = solve_endgame(
                my_hand=ctx.hand,
                known_hands=known,
                my_position=ctx.position,
                leader_position=leader,
                mode=ctx.mode or 'SUN',
                trump_suit=ctx.trump,
            )
            if result and result.get('reasoning', '').startswith('Minimax'):
                return {"action": "PLAY", "cardIndex": result['cardIndex'],
                        "reasoning": f"Endgame Solver: {result['reasoning']}"}
        except Exception as e:
            logger.debug(f"Endgame solver skipped: {e}")
        return None

    def _check_ashkal_signal(self, ctx: BotContext):
        """
        Check if the game is in Ashkal state and if we need to respond to a color request.
        """
        bid = ctx.raw_state.get('bid', {})
        if not bid.get('isAshkal'):
            return None

        bidder_pos = bid.get('bidder')
        partner_pos = self.get_partner_pos(ctx.player_index)

        if bidder_pos != partner_pos:
            return None  # We only signal for partner's Ashkal

        round_num = bid.get('round', 1)

        floor_suit = None
        if ctx.floor_card:
            floor_suit = ctx.floor_card.suit
        elif ctx.raw_state.get('floorCard'):
            floor_suit = ctx.raw_state['floorCard'].get('suit')

        if not floor_suit:
            return None

        colors = {'♥': 'RED', '♦': 'RED', '♠': 'BLACK', '♣': 'BLACK'}
        floor_color = colors.get(floor_suit)

        target_color = None
        if round_num == 1:
            target_color = floor_color  # Same Color
        else:
            target_color = 'BLACK' if floor_color == 'RED' else 'RED'

        target_suits = [s for s, c in colors.items() if c == target_color]

        best_idx = -1
        max_score = -100

        for i, c in enumerate(ctx.hand):
            if c.suit in target_suits:
                score = 0
                if c.rank == 'A': score += 10
                elif c.rank == '10': score += 8
                elif c.rank == 'K': score += 6
                elif c.rank == 'Q': score += 4
                elif c.rank == 'J': score += 2
                else: score += 0

                if score > max_score:
                    max_score = score
                    best_idx = i

        if best_idx != -1:
            return {
                "action": "PLAY",
                "cardIndex": best_idx,
                "reasoning": f"Ashkal Response (Round {round_num}): Playing {target_color} for Partner"
            }

        return None

    def _get_sun_lead(self, ctx: BotContext):
        # DEFENSIVE LEAD: When opponents won the bid, play defensively
        bidder_team = 'us' if ctx.bid_winner in [ctx.position, self.get_partner_pos(ctx.player_index)] else 'them'
        if bidder_team == 'them':
            # KABOOT BREAKER: If opponents are sweeping, use masters to deny
            if should_break_kaboot(ctx):
                for i, c in enumerate(ctx.hand):
                    if ctx.is_master_card(c):
                        return {"action": "PLAY", "cardIndex": i,
                                "reasoning": "KABOOT BREAKER: Leading master to deny sweep"}

            defensive = self._get_defensive_lead_sun(ctx)
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
                hand=ctx.hand, mode='SUN', trump_suit=None,
                tricks_won_by_us=our_wins, tricks_played=len(tricks),
                master_cards=master_idx, partner_is_leading=False,
            )
            logger.debug(f"[KABOOT] {kp['status']}: {kp['reasoning']}")
            if kp['status'] in ('PURSUING', 'LOCKED') and kp['play_index'] is not None:
                return {"action": "PLAY", "cardIndex": kp['play_index'],
                        "reasoning": f"KABOOT {kp['status']}: {kp['reasoning']}"}

        # CHECK PARTNER SIGNALS with Barqiya timing awareness
        signal = self._check_partner_signals(ctx)
        if signal:
            sig_type = signal.get('type')
            if sig_type == 'URGENT_CALL':
                # BARQIYA: Use timing-aware response
                legal = ctx.get_legal_moves()
                barq = get_barqiya_response(ctx, signal, legal)
                if barq:
                    return barq
            elif sig_type in ('ENCOURAGE', 'CONFIRMED_POSITIVE'):
                target_suit = signal.get('suit')
                if target_suit:
                    for i, c in enumerate(ctx.hand):
                        if c.suit == target_suit:
                            return {
                                "action": "PLAY",
                                "cardIndex": i,
                                "reasoning": f"Answering Partner's Signal ({sig_type} {target_suit})"
                            }

        # 10-MANAGEMENT: Check for Sira sequence protection
        legal = ctx.get_legal_moves()
        ten_play = get_ten_management_play(ctx, legal)
        if ten_play:
            return ten_play

        # ── COOPERATIVE LEAD: Partner-aware lead override ──
        try:
            _pi = None
            if hasattr(ctx, 'read_partner_info'):
                try: _pi = ctx.read_partner_info()
                except Exception: pass
            if _pi:
                tricks = ctx.raw_state.get('currentRoundTricks', [])
                coop = get_cooperative_lead(
                    hand=ctx.hand, partner_info=_pi, mode='SUN',
                    trump_suit=None, tricks_remaining=8 - len(tricks),
                    we_are_buyers=(bidder_team == 'us'),
                )
                if coop and coop.get('confidence', 0) >= 0.6:
                    logger.debug(f"[COOP_LEAD] {coop['strategy']}({coop['confidence']:.0%}): {coop['reasoning']}")
                    return {"action": "PLAY", "cardIndex": coop['card_index'],
                            "reasoning": f"CoopLead/{coop['strategy']}: {coop['reasoning']}"}
        except Exception as e:
            logger.debug(f"Cooperative lead skipped: {e}")

        # ── LEAD SELECTOR: Consult specialized lead module ──
        try:
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            our_wins = sum(1 for t in tricks if t.get('winner') in (ctx.position, partner_pos))
            master_idx = [i for i, c in enumerate(ctx.hand) if ctx.is_master_card(c)]
            # Collect opponent voids
            _opp_voids: dict[str, set] = {}
            my_team = ctx.team
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
                # Merge bid inference avoid suits (declarer's strong suits)
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
                hand=ctx.hand, mode='SUN', trump_suit=None,
                we_are_buyers=(bidder_team == 'us'),
                tricks_played=len(tricks), tricks_won_by_us=our_wins,
                master_indices=master_idx, partner_info=_pi,
                defense_info=_def_info, trump_info=None,
                opponent_voids=_opp_voids,
                suit_probs=_suit_probs,
            )
            # Adjust confidence threshold based on trick_review strategy_shift
            _ls_threshold = 0.65
            if self._trick_review:
                shift = self._trick_review.get('strategy_shift', 'NONE')
                if shift == 'AGGRESSIVE':
                    _ls_threshold = 0.50  # Accept riskier leads when behind
                elif shift == 'DAMAGE_CONTROL':
                    _ls_threshold = 0.75  # Require higher confidence when collapsing
            if ls_result and ls_result.get('confidence', 0) >= _ls_threshold:
                logger.debug(f"[LEAD_SEL] {ls_result['strategy']}({ls_result['confidence']:.0%}): {ls_result['reasoning']}")
                return {"action": "PLAY", "cardIndex": ls_result['card_index'],
                        "reasoning": f"LeadSel/{ls_result['strategy']}: {ls_result['reasoning']}"}
        except Exception as e:
            logger.debug(f"Lead selector skipped: {e}")

        best_card_idx = 0
        max_score = -100

        for i, c in enumerate(ctx.hand):
            score = 0
            is_master = ctx.is_master_card(c)
            
            if is_master:
                score += 100

            rank = c.rank
            if rank == 'A': score += 20
            elif rank == '10': score += 15
            elif rank == 'K':
                if any(x.rank == 'A' and x.suit == c.suit for x in ctx.hand): score += 18
                else: score += 5

            if rank in ['7', '8']: score += 2
            if rank in ['Q', 'J'] and not any(x.rank in ['A', 'K'] and x.suit == c.suit for x in ctx.hand):
                score -= 10

            # CARD COUNTING: Check remaining cards in this suit
            if ctx.memory:
                remaining_in_suit = ctx.memory.get_remaining_in_suit(c.suit)
                remaining_ranks = [r['rank'] for r in remaining_in_suit if r['rank'] != c.rank]
                
                # Penalize leading non-master cards into suits with higher remaining cards
                if not is_master and remaining_ranks:
                    higher_exists = False
                    for r in remaining_ranks:
                        try:
                            if ORDER_SUN.index(r) > ORDER_SUN.index(c.rank):
                                higher_exists = True
                                break
                        except ValueError:
                            continue
                    if higher_exists:
                        score -= 15
                
                # BONUS: If suit has only 1-2 remaining cards and we have the master
                if is_master and len(remaining_in_suit) <= 3:
                    score += 10

            # VOID DANGER: Avoid leading suits where opponents are void
            my_team = ctx.team
            for p in ctx.raw_state.get('players', []):
                if p.get('team') != my_team:
                    if ctx.is_player_void(p.get('position'), c.suit):
                        score -= 30
                        break

            # SUIT LENGTH: Prefer leading from long suits (more control)
            suit_count = sum(1 for x in ctx.hand if x.suit == c.suit)
            score += suit_count * 3

            if score > max_score:
                max_score = score
                best_card_idx = i

        reason = "Sun Lead"
        if ctx.is_master_card(ctx.hand[best_card_idx]):
            reason = "Leading Master Card"

        return {"action": "PLAY", "cardIndex": best_card_idx, "reasoning": reason}

    def _get_defensive_lead_sun(self, ctx: BotContext):
        """Defensive lead when OPPONENTS won the Sun bid.
        Strategy: Lead short suits to create voids, attack weak spots."""
        from ai_worker.strategies.components.defense_plan import plan_defense

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
            my_hand=ctx.hand, mode='SUN',
            buyer_position=buyer_pos, partner_position=partner_pos,
            tricks_played=len(tricks), tricks_won_by_us=our_wins, tricks_won_by_them=their_wins,
            void_suits=buyer_void_suits,
        )
        logger.debug(f"[DEFENSE] {dplan['reasoning']}")

        best_idx = 0
        max_score = -100

        # Calculate suit lengths
        suit_lengths = {}
        for s in ['♠', '♥', '♦', '♣']:
            suit_lengths[s] = sum(1 for c in ctx.hand if c.suit == s)

        for i, c in enumerate(ctx.hand):
            score = 0
            is_master = ctx.is_master_card(c)
            length = suit_lengths.get(c.suit, 0)

            # PRIORITY 1: Cash guaranteed masters — they can't lose
            if is_master:
                score += 80
                # Bonus for masters in short suits (extract value then get void)
                if length <= 2:
                    score += 30

            # PRIORITY 2: Lead SHORT suits to create voids for future tricks
            if length == 1 and not is_master:
                score += 25  # Singleton — lead to void yourself
            elif length == 2:
                score += 15  # Doubleton

            # PRIORITY 3: Lead through declarer's WEAK suits
            # Attack suits where opponents showed weakness (discards)
            my_team = ctx.team
            for p in ctx.raw_state.get('players', []):
                if p.get('team') != my_team:
                    # Bonus for leading suits where opponent is weak
                    if ctx.memory:
                        remaining = ctx.memory.get_remaining_in_suit(c.suit)
                        if len(remaining) <= 2:  # Suit is nearly exhausted
                            score += 10

            # PENALTY: Don't lead unsupported honors (K without A, Q without K-A)
            if c.rank == 'K' and not any(x.rank == 'A' and x.suit == c.suit for x in ctx.hand):
                score -= 20  # Bare King = gift to opponents
            if c.rank == 'Q' and not any(x.rank in ['A', 'K'] and x.suit == c.suit for x in ctx.hand):
                score -= 15

            # PENALTY: Don't lead 10s and Aces into long contested suits (point hemorrhage)
            if c.rank in ['A', '10'] and not is_master and length >= 3:
                score -= 10

            if score > max_score:
                max_score = score
                best_idx = i

        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Defensive Lead (Sun)"}

    def _get_sun_follow(self, ctx: BotContext):
        lead_suit = ctx.lead_suit
        winning_card = ctx.winning_card
        winner_pos = ctx.winner_pos

        follows = [i for i, c in enumerate(ctx.hand) if c.suit == lead_suit]
        if not follows:
            return self.get_trash_card(ctx)

        partner_pos = self.get_partner_pos(ctx.player_index)
        is_partner_winning = (winner_pos == partner_pos)
        
        # SEAT-AWARE POSITIONAL PLAY
        seat = len(ctx.table_cards) + 1  # 2nd, 3rd, or 4th seat
        is_last_to_play = (seat == 4)
        
        # TRICK VALUE: Calculate how many points are on the table
        trick_points = 0
        for tc in ctx.table_cards:
            tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
            if isinstance(tc_card, dict):
                trick_points += POINT_VALUES_SUN.get(tc_card.get('rank', ''), 0)
            elif hasattr(tc_card, 'rank'):
                trick_points += POINT_VALUES_SUN.get(tc_card.rank, 0)

        # ── COOPERATIVE FOLLOW: Partner-aware follow override ──
        try:
            _pi = None
            if hasattr(ctx, 'read_partner_info'):
                try: _pi = ctx.read_partner_info()
                except Exception: pass
            if _pi:
                coop_f = get_cooperative_follow(
                    hand=ctx.hand, legal_indices=follows, partner_info=_pi,
                    led_suit=lead_suit, mode='SUN', trump_suit=None,
                    partner_winning=is_partner_winning, trick_points=trick_points,
                )
                if coop_f and coop_f.get('confidence', 0) >= 0.6:
                    logger.debug(f"[COOP_FOLLOW] {coop_f['tactic']}({coop_f['confidence']:.0%}): {coop_f['reasoning']}")
                    return {"action": "PLAY", "cardIndex": coop_f['card_index'],
                            "reasoning": f"CoopFollow/{coop_f['tactic']}: {coop_f['reasoning']}"}
        except Exception as e:
            logger.debug(f"Cooperative follow skipped: {e}")

        # ── FOLLOW OPTIMIZER: Consult specialized follow-suit module ──
        try:
            bidder_team = 'us' if ctx.bid_winner in [ctx.position, partner_pos] else 'them'
            # Build table_cards dicts for the optimizer
            _fo_table = []
            for tc in ctx.table_cards:
                tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
                if isinstance(tc_card, dict):
                    _fo_table.append({"rank": tc_card.get('rank', ''), "suit": tc_card.get('suit', ''), "position": tc.get('playedBy', '')})
                elif hasattr(tc_card, 'rank'):
                    _fo_table.append({"rank": tc_card.rank, "suit": tc_card.suit, "position": tc.get('playedBy', '')})
            # Find partner's card index in table_cards
            _partner_card_idx = None
            for ti, tc in enumerate(ctx.table_cards):
                if tc.get('playedBy') == partner_pos:
                    _partner_card_idx = ti
                    break
            tricks = ctx.raw_state.get('currentRoundTricks', [])
            fo_result = optimize_follow(
                hand=ctx.hand, legal_indices=follows, table_cards=_fo_table,
                led_suit=lead_suit, mode='SUN', trump_suit=None, seat=seat,
                partner_winning=is_partner_winning, partner_card_index=_partner_card_idx,
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

        if is_partner_winning:
            safe_feeds = []
            overtaking_feeds = []

            for idx in follows:
                c = ctx.hand[idx]
                if ctx._compare_ranks(c.rank, winning_card.rank, 'SUN'):
                    overtaking_feeds.append(idx)
                else:
                    safe_feeds.append(idx)

            if safe_feeds:
                best_idx = self.find_highest_point_card(ctx, safe_feeds, POINT_VALUES_SUN)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Partner winning - Safe Feed"}
            else:
                best_idx = self.find_lowest_rank_card(ctx, overtaking_feeds, ORDER_SUN)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Overtaking Partner (Forced)"}
        else:
            winners = []
            for idx in follows:
                c = ctx.hand[idx]
                if ctx._compare_ranks(c.rank, winning_card.rank, 'SUN'):
                    winners.append(idx)

            if winners:
                if seat == 4:
                    # 4TH SEAT: Guaranteed win — finesse with lowest winner
                    best_idx = self.find_lowest_rank_card(ctx, winners, ORDER_SUN)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "4th Seat Finesse"}
                elif seat == 3:
                    # 3RD SEAT: Partner already played, one opponent left.
                    # Play aggressively — use strongest winner to survive the last player
                    if trick_points >= 10:
                        # High-value trick — secure it with a strong card
                        best_idx = self.find_best_winner(ctx, winners, ORDER_SUN)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Securing High-Value Trick"}
                    else:
                        best_idx = self.find_lowest_rank_card(ctx, winners, ORDER_SUN)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "3rd Seat: Economy Win"}
                else:
                    # 2ND SEAT: Be conservative — partner hasn't played yet.
                    # Only commit if we have the master (guaranteed win)
                    master_winners = [i for i in winners if ctx.is_master_card(ctx.hand[i])]
                    if master_winners:
                        best_idx = self.find_lowest_rank_card(ctx, master_winners, ORDER_SUN)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Playing Master"}
                    elif trick_points >= 15:
                        # High stakes — worth committing
                        best_idx = self.find_lowest_rank_card(ctx, winners, ORDER_SUN)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: High-Stakes Commit"}
                    else:
                        # Low stakes, duck and let partner handle it
                        best_idx = self.find_lowest_point_card(ctx, follows, POINT_VALUES_SUN)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "2nd Seat: Ducking for Partner"}
            else:
                # Can't win — POINT PROTECTION
                best_idx = self.find_lowest_point_card(ctx, follows, POINT_VALUES_SUN)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": f"Seat {seat}: Ducking (Point Protection)"}

    def _check_partner_signals(self, ctx: BotContext):
        """Scans previous tricks to see if partner sent a signal."""
        from ai_worker.signals.manager import SignalManager
        from ai_worker.signals.definitions import SignalType

        tricks = ctx.raw_state.get('currentRoundTricks', [])
        if not tricks: return None

        partner_pos = self.get_partner_pos(ctx.player_index)
        signal_mgr = SignalManager()

        last_trick = tricks[-1]
        cards = last_trick.get('cards', [])

        partner_card = None
        for c_data in cards:
            p_idx = c_data.get('playerIndex')
            my_idx = ctx.player_index
            partner_idx = (my_idx + 2) % 4

            if p_idx == partner_idx:
                from game_engine.models.card import Card
                partner_card = Card(c_data['suit'], c_data['rank'])
                break

        if not partner_card: return None

        if not cards: return None
        first_card_data = cards[0]
        actual_lead_suit = first_card_data['suit']

        if partner_card.suit != actual_lead_suit:
            winner_idx = last_trick.get('winner')
            is_tahreeb_context = (winner_idx == ctx.player_index)

            sig_type = signal_mgr.get_signal_for_card(partner_card, is_tahreeb_context)

            discards = ctx.memory.discards.get(partner_pos, [])
            directional_sig = signal_mgr.analyze_directional_signal(discards, partner_card.suit)

            if directional_sig == SignalType.CONFIRMED_POSITIVE:
                return {'suit': partner_card.suit, 'type': 'CONFIRMED_POSITIVE'}
            elif directional_sig == SignalType.CONFIRMED_NEGATIVE:
                return {'suit': partner_card.suit, 'type': 'CONFIRMED_NEGATIVE'}

            if sig_type == SignalType.URGENT_CALL:
                return {'suit': partner_card.suit, 'type': 'URGENT_CALL'}
            elif sig_type == SignalType.ENCOURAGE:
                return {'suit': partner_card.suit, 'type': 'ENCOURAGE'}
            elif sig_type == SignalType.NEGATIVE_DISCARD:
                discard_suit = partner_card.suit
                colors = {'♥': 'RED', '♦': 'RED', '♠': 'BLACK', '♣': 'BLACK'}
                my_color = colors.get(discard_suit)

                target_suits = []
                for s, color in colors.items():
                    if color == my_color and s != discard_suit:
                        target_suits.append(s)

                return {'suits': target_suits, 'type': 'PREFER_SAME_COLOR', 'negated': discard_suit}
            elif sig_type == SignalType.PREFER_OPPOSITE_COLOR:
                discard_suit = partner_card.suit
                colors = {'♥': 'RED', '♦': 'RED', '♠': 'BLACK', '♣': 'BLACK'}
                my_color = colors.get(discard_suit)

                target_suits = []
                for s, color in colors.items():
                    if color != my_color:
                        target_suits.append(s)

                return {'suits': target_suits, 'type': 'PREFER_OPPOSITE'}

        return None
