import time

from ai_worker.strategies.components.base import StrategyComponent
from ai_worker.bot_context import BotContext
from game_engine.models.constants import ORDER_SUN


class ProjectStrategy(StrategyComponent):
    """Handles Sawa, Akka, and project declaration logic."""

    def __init__(self):
        self._akka_cooldowns = {}  # Map[player_index, dict(round, trick, time)]

    def get_decision(self, ctx: BotContext) -> dict | None:
        """Check Sawa first, then Akka."""
        sawa = self.check_sawa(ctx)
        if sawa:
            return sawa

        akka = self.check_akka(ctx)
        if akka:
            return akka

        return None

    def check_sawa(self, ctx: BotContext) -> dict | None:
        """Check if we are eligible for Sawa and should declare it."""
        from game_engine.logic.rules.sawa import check_sawa_eligibility

        # Gate: Sawa only available with ≤ 4 cards and leading the trick (empty table)
        if len(ctx.hand) > 4:
            return None
        if len(ctx.table_cards) > 0:
            return None


        played_cards = set()

        # 1. From Round History (Truth)
        history = ctx.raw_state.get('roundHistory', [])
        for trick in history:
            for c in trick.get('cards', []):
                card_obj = c.get('card', {}) if isinstance(c, dict) else c
                rank = card_obj.get('rank') if isinstance(card_obj, dict) else getattr(card_obj, 'rank', None)
                suit = card_obj.get('suit') if isinstance(card_obj, dict) else getattr(card_obj, 'suit', None)
                if rank and suit:
                    played_cards.add(f"{rank}{suit}")

        # 2. From Current Table
        for tc in ctx.table_cards:
            c = tc['card']
            played_cards.add(f"{c.rank}{c.suit}")

        eligible = check_sawa_eligibility(
            hand=ctx.hand,
            played_cards=played_cards,
            trump_suit=ctx.trump,
            game_mode=ctx.mode,
            phase=ctx.phase
        )

        if eligible:

            return {
                "action": "SAWA",
                "reasoning": f"Sawa! All {len(ctx.hand)} remaining cards are guaranteed winners."
            }


        return None

    def check_akka(self, ctx: BotContext) -> dict | None:
        """Checks if eligible for 'Akka' declaration."""
        if ctx.mode != 'HOKUM':
            return None

        if len(ctx.table_cards) > 0:
            return None

        if ctx.akka_state and ctx.akka_state.get('active'):
            return None

        if ctx.akka_state and ctx.akka_state.get('claimer') == ctx.position:
            return None

        # --- SPAM PROTECTION (Once per Trick per Player) ---
        # Akka cascades across tricks (Ace gone → 10 is Akka, then King, etc.)
        # So we only block re-declaration on the SAME trick.
        current_round = len(ctx.raw_state.get('pastRoundResults', []))
        current_trick = len(ctx.raw_state.get('roundHistory', []))

        cooldown = self._akka_cooldowns.get(ctx.player_index)

        if cooldown:
            # Block if already declared this exact trick
            if cooldown.get('round') == current_round and cooldown.get('trick') == current_trick:
                return None

        # Gather all played cards (Memory + Table)
        played = set(ctx.memory.played_cards)
        for tc in ctx.table_cards:
            c = tc['card']
            played.add(f"{c.rank}{c.suit}")

        # Scan Hand
        eligible = False

        my_suits = {}
        for c in ctx.hand:
            if c.suit not in my_suits:
                my_suits[c.suit] = []
            my_suits[c.suit].append(c)

        for suit, cards in my_suits.items():
            if suit == ctx.trump:
                continue

            rank_order = ORDER_SUN

            valid_cards = [c for c in cards if c.rank in rank_order]
            if not valid_cards:
                continue

            my_best = max(valid_cards, key=lambda c: rank_order.index(c.rank))

            if my_best.rank == 'A':
                continue

            my_strength = rank_order.index(my_best.rank)
            is_master = True

            for r in rank_order:
                strength = rank_order.index(r)
                if strength > my_strength:
                    sig = f"{r}{suit}"
                    if sig not in played:
                        is_master = False
                        break

            if is_master:
                eligible = True
                break

        if eligible:
            self._akka_cooldowns[ctx.player_index] = {
                'round': current_round,
                'trick': current_trick,
            }
            return {"action": "AKKA", "reasoning": "Declaring Master (Akka)"}

        return None

    @staticmethod
    def calculate_projects(ctx: BotContext, decision: dict):
        """Extracts project declaration logic (Clean Code: SRP)."""
        played_tricks = ctx.raw_state.get('currentRoundTricks', [])
        if len(played_tricks) == 0:
            from game_engine.logic.utils import scan_hand_for_projects
            projects = scan_hand_for_projects(ctx.hand, ctx.mode)
            if projects:
                serialized_projects = []
                for p in projects:
                    sp = p.copy()
                    if 'cards' in sp:
                        sp['cards'] = [c.to_dict() if hasattr(c, 'to_dict') else c for c in sp['cards']]
                    serialized_projects.append(sp)
                decision['declarations'] = serialized_projects
