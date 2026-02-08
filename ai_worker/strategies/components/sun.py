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
        partner_pos = self._get_partner_pos(ctx.player_index)

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
            if ctx.is_master_card(c):
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

            if score > max_score:
                max_score = score
                best_card_idx = i

        reason = "Sun Lead"
        if ctx.is_master_card(ctx.hand[best_card_idx]):
            reason = "Leading Master Card"

        return {"action": "PLAY", "cardIndex": best_card_idx, "reasoning": reason}

    def _get_sun_follow(self, ctx: BotContext):
        lead_suit = ctx.lead_suit
        winning_card = ctx.winning_card
        winner_pos = ctx.winner_pos

        follows = [i for i, c in enumerate(ctx.hand) if c.suit == lead_suit]
        if not follows:
            return self._get_trash_card(ctx)

        partner_pos = self._get_partner_pos(ctx.player_index)
        is_partner_winning = (winner_pos == partner_pos)

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
                best_idx = self._find_highest_point_card_sun(ctx, safe_feeds)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Partner winning - Safe Feed"}
            else:
                best_idx = self._find_best_winner_sun(ctx, overtaking_feeds)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Overtaking Partner (Forced)"}
        else:
            winners = []
            for idx in follows:
                c = ctx.hand[idx]
                if ctx._compare_ranks(c.rank, winning_card.rank, 'SUN'):
                    winners.append(idx)

            if winners:
                best_idx = self._find_best_winner_sun(ctx, winners)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Cutting Enemy"}
            else:
                best_idx = self._find_lowest_rank_card_sun(ctx, follows)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Ducking (Can't Win)"}

    # --- Heuristic Helpers ---

    def _find_highest_point_card_sun(self, ctx, indices):
        best_i = indices[0]
        best_pts = -1
        for i in indices:
            rank = ctx.hand[i].rank
            pts = POINT_VALUES_SUN.get(rank, 0)
            if pts > best_pts:
                best_pts = pts
                best_i = i
        return best_i

    def _find_best_winner_sun(self, ctx, indices):
        best_i = indices[0]
        best_strength = -1
        for i in indices:
            strength = ORDER_SUN.index(ctx.hand[i].rank)
            if strength > best_strength:
                best_strength = strength
                best_i = i
        return best_i

    def _find_lowest_rank_card_sun(self, ctx, indices):
        best_i = indices[0]
        min_strength = 999
        for i in indices:
            strength = ORDER_SUN.index(ctx.hand[i].rank)
            if strength < min_strength:
                min_strength = strength
                best_i = i
        return best_i

    def _get_trash_card(self, ctx):
        """Smart Trash Selection with Collaborative Signaling."""
        from ai_worker.signals.manager import SignalManager
        from game_engine.models.constants import SUITS

        signal_mgr = SignalManager()
        trump = ctx.trump if ctx.mode == 'HOKUM' else None

        for s in SUITS:
            if s == trump: continue

            if signal_mgr.should_signal_encourage(ctx.hand, s, ctx.mode):
                sig_card = signal_mgr.get_discard_signal_card(ctx.hand, s, ctx.mode)

                if sig_card:
                    for i, c in enumerate(ctx.hand):
                        if c.suit == sig_card.suit and c.rank == sig_card.rank:
                            return {
                                "action": "PLAY",
                                "cardIndex": i,
                                "reasoning": f"Collaborative Signal: Encourage {s} (Discarding {c.rank})"
                            }

        # Fallback: Standard Trash Logic
        best_idx = 0
        min_value = 1000

        for i, c in enumerate(ctx.hand):
            score = 0

            if c.rank == 'A': score += 20
            elif c.rank == '10': score += 15
            elif c.rank == 'K': score += 10
            elif c.rank == 'Q': score += 5
            elif c.rank == 'J': score += 2
            elif c.rank == '9': score += 1
            else: score += 0

            if ctx.mode == 'HOKUM':
                if c.suit == trump:
                    score += 50
                    if c.rank == 'J': score += 100
                    if c.rank == '9': score += 80

            if ctx.is_master_card(c): score += 30

            if score < min_value:
                min_value = score
                best_idx = i

        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Smart Trash"}

    def _check_partner_signals(self, ctx: BotContext):
        """Scans previous tricks to see if partner sent a signal."""
        from ai_worker.signals.manager import SignalManager
        from ai_worker.signals.definitions import SignalType

        tricks = ctx.raw_state.get('currentRoundTricks', [])
        if not tricks: return None

        partner_pos = self._get_partner_pos(ctx.player_index)
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

    # --- Shared Helpers ---

    @staticmethod
    def _get_partner_pos(my_idx):
        partner_idx = (my_idx + 2) % 4
        positions = ['Bottom', 'Right', 'Top', 'Left']
        return positions[partner_idx]
