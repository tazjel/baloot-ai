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

        # Fallback: Standard Trash Logic (minimize value lost)
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

    @staticmethod
    def get_partner_pos(my_idx: int) -> str:
        """Get the position name of the partner (across the table)."""
        partner_idx = (my_idx + 2) % 4
        positions = ['Bottom', 'Right', 'Top', 'Left']
        return positions[partner_idx]
