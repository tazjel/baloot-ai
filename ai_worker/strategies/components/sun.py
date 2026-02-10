from ai_worker.strategies.components.base import StrategyComponent
from ai_worker.bot_context import BotContext
from game_engine.models.constants import POINT_VALUES_SUN, ORDER_SUN


class SunStrategy(StrategyComponent):
    """Handles all Sun mode playing logic (lead and follow)."""

    def get_decision(self, ctx: BotContext) -> dict | None:
        if not ctx.table_cards:
            # Check for Ashkal Signal first
            ashkal_move = self._check_ashkal_signal(ctx)
            if ashkal_move:
                return ashkal_move
            return self._get_sun_lead(ctx)
        else:
            return self._get_sun_follow(ctx)

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
            defensive = self._get_defensive_lead_sun(ctx)
            if defensive:
                return defensive

        # 0. Check for Collaborative Signals
        signal = self._check_partner_signals(ctx)
        if signal and signal['type'] == 'ENCOURAGE':
            target_suit = signal['suit']
            for i, c in enumerate(ctx.hand):
                if c.suit == target_suit:
                    return {
                        "action": "PLAY",
                        "cardIndex": i,
                        "reasoning": f"Answering Partner's Signal (Encourage {target_suit})"
                    }

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
