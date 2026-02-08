from ai_worker.strategies.components.base import StrategyComponent
from ai_worker.bot_context import BotContext
from game_engine.models.constants import POINT_VALUES_HOKUM, ORDER_HOKUM


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
        bidder_team = 'us' if ctx.bid_winner in [ctx.position, self._get_partner_pos(ctx.player_index)] else 'them'
        should_open_trump = (bidder_team == 'us')

        # SMART SAHN: Only open trumps if enemies still have them!
        opponents_might_have_trump = True  # Default assumption
        if should_open_trump:
            opponents_might_have_trump = False
            my_team = ctx.team
            for p in ctx.raw_state.get('players', []):
                if p.get('team') != my_team:
                    if not ctx.is_player_void(p.get('position'), trump):
                        opponents_might_have_trump = True
                        break

            if not opponents_might_have_trump:
                should_open_trump = False

        for i, c in enumerate(ctx.hand):
            score = 0
            is_trump = (c.suit == trump)

            # VOID AVOIDANCE
            is_danger = False
            my_team = ctx.team
            if not is_trump:
                for p in ctx.raw_state.get('players', []):
                    if p.get('team') != my_team:
                        if ctx.is_player_void(p.get('position'), c.suit):
                            is_danger = True
                            break

            if is_trump:
                if should_open_trump:
                    score += 40

                # Contextual Master Bonus (INDENTATION FIX APPLIED)
                master_bonus = 100

                if not opponents_might_have_trump:
                    master_bonus = 10  # Drastically reduce. Save it for ruffing.

                if ctx.is_master_card(c):
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
                if ctx.is_master_card(c):
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

            if score > max_score:
                max_score = score
                best_card_idx = i

        reason = "Hokum Lead"
        if ctx.is_master_card(ctx.hand[best_card_idx]):
            reason = "Leading Master Card"
        if ctx.hand[best_card_idx].suit == trump and should_open_trump:
            reason = "Smart Sahn (Drawing Trumps)"

        return {"action": "PLAY", "cardIndex": best_card_idx, "reasoning": reason}

    def _get_hokum_follow(self, ctx: BotContext):
        lead_suit = ctx.lead_suit
        winning_card = ctx.winning_card
        winner_pos = ctx.winner_pos
        trump = ctx.trump

        follows = [i for i, c in enumerate(ctx.hand) if c.suit == lead_suit]

        # 1. Void Clause
        if not follows:
            has_trumps = any(c.suit == trump for c in ctx.hand)
            partner_pos = self._get_partner_pos(ctx.player_index)
            is_partner_winning = (winner_pos == partner_pos)

            if has_trumps and not is_partner_winning:
                trumps = [i for i, c in enumerate(ctx.hand) if c.suit == trump]

                if winning_card.suit == trump:
                    over_trumps = [i for i in trumps if ctx._compare_ranks(ctx.hand[i].rank, winning_card.rank, 'HOKUM')]
                    if over_trumps:
                        best_idx = self._find_lowest_rank_card_hokum(ctx, over_trumps)
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Over-trumping"}
                    else:
                        return self._get_trash_card(ctx)
                else:
                    best_idx = self._find_lowest_rank_card_hokum(ctx, trumps)
                    return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Eating with Trump"}

            return self._get_trash_card(ctx)

        # 2. Follow Suit Clause
        partner_pos = self._get_partner_pos(ctx.player_index)
        is_partner_winning = (winner_pos == partner_pos)

        if is_partner_winning:
            best_idx = self._find_highest_point_card_hokum(ctx, follows)
            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Partner Winning - Feeding"}
        else:
            if winning_card.suit == trump and lead_suit != trump:
                best_idx = self._find_lowest_rank_card_hokum(ctx, follows)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Enemy Trumping - Ducking"}

            winners = []
            for idx in follows:
                c = ctx.hand[idx]
                if ctx._compare_ranks(c.rank, winning_card.rank, 'HOKUM'):
                    winners.append(idx)

            if winners:
                best_idx = self._find_best_winner_hokum(ctx, winners)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Beat Enemy"}
            else:
                best_idx = self._find_lowest_rank_card_hokum(ctx, follows)
                return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Ducking"}

    # --- Heuristic Helpers ---

    def _find_highest_point_card_hokum(self, ctx, indices):
        best_i = indices[0]
        best_pts = -1
        for i in indices:
            rank = ctx.hand[i].rank
            pts = POINT_VALUES_HOKUM.get(rank, 0)
            if pts > best_pts:
                best_pts = pts
                best_i = i
        return best_i

    def _find_best_winner_hokum(self, ctx, indices):
        best_i = indices[0]
        best_strength = -1
        for i in indices:
            strength = ORDER_HOKUM.index(ctx.hand[i].rank)
            if strength > best_strength:
                best_strength = strength
                best_i = i
        return best_i

    def _find_lowest_rank_card_hokum(self, ctx, indices):
        best_i = indices[0]
        min_strength = 999
        for i in indices:
            strength = ORDER_HOKUM.index(ctx.hand[i].rank)
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

    # --- Shared Helpers ---

    @staticmethod
    def _get_partner_pos(my_idx):
        partner_idx = (my_idx + 2) % 4
        positions = ['Bottom', 'Right', 'Top', 'Left']
        return positions[partner_idx]
