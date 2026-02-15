from abc import ABC, abstractmethod
from ai_worker.bot_context import BotContext


class StrategyComponent(ABC):
    """Abstract base class for all strategy components."""

    @abstractmethod
    def get_decision(self, ctx: BotContext) -> dict | None:
        """
        Returns a decision dict or None if no decision can be made.
        Decision format: {"action": "PLAY", "cardIndex": int, "reasoning": str}
        """
        ...

    # ═══════════════════════════════════════════════════════════════════
    #  Shared Card Selection Utilities
    #  These are parameterized by point_values and rank_order so both
    #  Hokum and Sun strategies can reuse them without duplication.
    # ═══════════════════════════════════════════════════════════════════

    def find_highest_point_card(self, ctx: BotContext, indices: list, point_values: dict) -> int:
        """Return the index of the card with the highest point value."""
        best_i = indices[0]
        best_pts = -1
        for i in indices:
            rank = ctx.hand[i].rank
            pts = point_values.get(rank, 0)
            if pts > best_pts:
                best_pts = pts
                best_i = i
        return best_i

    def find_best_winner(self, ctx: BotContext, indices: list, rank_order: list) -> int:
        """Return the index of the highest-ranked card (strongest winner)."""
        best_i = indices[0]
        best_strength = -1
        for i in indices:
            strength = rank_order.index(ctx.hand[i].rank)
            if strength > best_strength:
                best_strength = strength
                best_i = i
        return best_i

    def find_lowest_rank_card(self, ctx: BotContext, indices: list, rank_order: list) -> int:
        """Return the index of the lowest-ranked card (weakest)."""
        best_i = indices[0]
        min_strength = 999
        for i in indices:
            strength = rank_order.index(ctx.hand[i].rank)
            if strength < min_strength:
                min_strength = strength
                best_i = i
        return best_i

    def find_lowest_point_card(self, ctx: BotContext, indices: list, point_values: dict) -> int:
        """Return the index of the card with the lowest point value — protects high-value cards when ducking."""
        best_i = indices[0]
        min_pts = 999
        for i in indices:
            rank = ctx.hand[i].rank
            pts = point_values.get(rank, 0)
            if pts < min_pts:
                min_pts = pts
                best_i = i
        return best_i

    def get_trash_card(self, ctx: BotContext) -> dict:
        """
        Smart Trash Selection with Al-Ta'sheer Signaling Protocol.
        
        Context-aware discarding:
        - TAHREEB (partner winning): Discard suit you DON'T want → negative signal
        - TANFEER (opponent winning): Discard suit you DO want → positive signal
        """
        from ai_worker.signals.manager import SignalManager
        from game_engine.models.constants import SUITS

        signal_mgr = SignalManager()
        trump = ctx.trump if ctx.mode == 'HOKUM' else None

        # Determine trick context: Who is winning?
        partner_pos = self.get_partner_pos(ctx.player_index)
        is_partner_winning = (ctx.winner_pos == partner_pos) if ctx.winner_pos else False

        if is_partner_winning:
            # === TAHREEB (Partner Winning) ===
            # Discard from suit you DON'T want → tells partner to avoid it
            # Strategy: Discard lowest card from weakest non-trump suit
            worst_suit = None
            worst_score = 999
            for s in SUITS:
                if s == trump:
                    continue
                suit_cards = [c for c in ctx.hand if c.suit == s]
                if not suit_cards:
                    continue
                # Evaluate suit "value" — lower = worse = better to discard
                suit_val = 0
                for c in suit_cards:
                    if c.rank == 'A': suit_val += 20
                    elif c.rank == '10': suit_val += 15
                    elif c.rank == 'K': suit_val += 10
                    elif ctx.is_master_card(c): suit_val += 25
                    else: suit_val += 1
                if suit_val < worst_score:
                    worst_score = suit_val
                    worst_suit = s

            if worst_suit:
                suit_cards_idx = [(i, ctx.hand[i]) for i in range(len(ctx.hand)) if ctx.hand[i].suit == worst_suit]
                if suit_cards_idx:
                    # Discard lowest value from the worst suit
                    suit_cards_idx.sort(key=lambda x: {'A': 7, '10': 6, 'K': 5, 'Q': 4, 'J': 3, '9': 2, '8': 1, '7': 0}.get(x[1].rank, 0))
                    idx = suit_cards_idx[0][0]
                    return {
                        "action": "PLAY",
                        "cardIndex": idx,
                        "reasoning": f"Tahreeb: Negative signal — avoid {worst_suit} ({ctx.hand[idx].rank})"
                    }
        else:
            # === TANFEER (Opponent Winning) ===
            # Discard from suit you DO want → tells partner to lead it
            for s in SUITS:
                if s == trump:
                    continue
                if signal_mgr.should_signal_encourage(ctx.hand, s, ctx.mode):
                    sig_card = signal_mgr.get_discard_signal_card(ctx.hand, s, ctx.mode)
                    if sig_card:
                        for i, c in enumerate(ctx.hand):
                            if c.suit == sig_card.suit and c.rank == sig_card.rank:
                                return {
                                    "action": "PLAY",
                                    "cardIndex": i,
                                    "reasoning": f"Tanfeer: Positive signal — want {s} ({c.rank})"
                                }

        # Fallback: Strategic Discard Logic (ruff → point-shed → void-create → safe-discard)
        from ai_worker.strategies.components.discard_logic import choose_discard

        # Calculate trick points from table cards
        trick_points = 0
        for tc in ctx.table_cards:
            tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
            rank = tc_card.rank if hasattr(tc_card, 'rank') else tc_card.get('rank', '')
            if ctx.mode == 'HOKUM':
                from game_engine.models.constants import POINT_VALUES_HOKUM
                trick_points += POINT_VALUES_HOKUM.get(rank, 0)
            else:
                from game_engine.models.constants import POINT_VALUES_SUN
                trick_points += POINT_VALUES_SUN.get(rank, 0)

        # Build table_cards in the format choose_discard expects
        raw_table = []
        for tc in ctx.table_cards:
            tc_card = tc.get('card', tc) if isinstance(tc, dict) else tc
            if hasattr(tc_card, 'rank'):
                raw_table.append({'card': {'rank': tc_card.rank, 'suit': tc_card.suit}, 'playedBy': tc.get('playedBy', '')})
            else:
                raw_table.append(tc)

        legal = list(range(len(ctx.hand)))
        best_idx = choose_discard(
            hand=ctx.hand,
            legal_indices=legal,
            table_cards=raw_table,
            mode=ctx.mode or 'SUN',
            trump_suit=trump,
            partner_winning=is_partner_winning,
            trick_points=trick_points,
            cards_remaining=len(ctx.hand),
        )
        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Smart Discard"}

    def _try_endgame(self, ctx: BotContext) -> dict | None:
        """Attempt minimax solve using ML or heuristic hand reconstruction.

        Shared by both HokumStrategy and SunStrategy for endgame positions (<=3 cards).
        """
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
                mode=ctx.mode or 'SUN',
                trump_suit=ctx.trump,
            )
            if result and result.get('reasoning', '').startswith('Minimax'):
                return {"action": "PLAY", "cardIndex": result['cardIndex'],
                        "reasoning": f"Endgame Solver: {result['reasoning']}"}
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Endgame solver skipped: {e}")
        return None

    @staticmethod
    def get_partner_pos(my_idx: int) -> str:
        """Get the position name of the partner (across the table)."""
        partner_idx = (my_idx + 2) % 4
        positions = ['Bottom', 'Right', 'Top', 'Left']
        return positions[partner_idx]
