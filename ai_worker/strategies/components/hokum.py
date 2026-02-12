from ai_worker.strategies.components.base import StrategyComponent
from ai_worker.bot_context import BotContext
from game_engine.models.constants import POINT_VALUES_HOKUM, ORDER_HOKUM, ORDER_SUN
from ai_worker.strategies.components.signaling import (
    get_role, should_attempt_kaboot, should_break_kaboot,
    get_barqiya_response
)
import logging

logger = logging.getLogger(__name__)


class HokumStrategy(StrategyComponent):
    """Handles all Hokum mode playing logic (lead and follow)."""

    def get_decision(self, ctx: BotContext) -> dict | None:
        if not ctx.table_cards:
            return self._get_hokum_lead(ctx)
        else:
            return self._get_hokum_follow(ctx)

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

        should_open_trump = (bidder_team == 'us')

        # SMART SAHN: Only open trumps if enemies still have them!
        opponents_might_have_trump = True  # Default assumption
        remaining_enemy_trumps = 0
        if should_open_trump:
            opponents_might_have_trump = False
            my_team = ctx.team
            for p in ctx.raw_state.get('players', []):
                if p.get('team') != my_team:
                    if not ctx.is_player_void(p.get('position'), trump):
                        opponents_might_have_trump = True
                        remaining_enemy_trumps += 1

            if not opponents_might_have_trump:
                should_open_trump = False

        # TRUMP ECONOMY: Count our trump strength vs theirs
        my_trump_count = sum(1 for c in ctx.hand if c.suit == trump)
        if my_trump_count <= 2 and remaining_enemy_trumps == 0:
            should_open_trump = False

        # CROSS-RUFF DETECTION: Check if opponent voids create a ruff danger pattern
        # An opponent void in suit X + has trumps = they'll ruff our X leads
        ruffable_suits = set()
        my_team = ctx.team
        for p in ctx.raw_state.get('players', []):
            if p.get('team') != my_team:
                pos = p.get('position')
                # If opponent is void in a suit but NOT void in trump → they'll ruff
                if pos and not ctx.is_player_void(pos, trump):
                    for s in ['♠', '♥', '♦', '♣']:
                        if s != trump and ctx.is_player_void(pos, s):
                            ruffable_suits.add(s)

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
                if not opponents_might_have_trump:
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
        trump = ctx.trump
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
        
        # TRICK VALUE: Calculate points on the table
        trick_points = 0
        for tc in ctx.table_cards:
            tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
            if isinstance(tc_card, dict):
                trick_points += POINT_VALUES_HOKUM.get(tc_card.get('rank', ''), 0)
            elif hasattr(tc_card, 'rank'):
                trick_points += POINT_VALUES_HOKUM.get(tc_card.rank, 0)

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

