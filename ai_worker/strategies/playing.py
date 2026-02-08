from ai_worker.bot_context import BotContext
from ai_worker.cognitive import CognitiveOptimizer
from ai_worker.strategies.components.sun import SunStrategy
from ai_worker.strategies.components.hokum import HokumStrategy
from ai_worker.strategies.components.projects import ProjectStrategy


class PlayingStrategy:
    def __init__(self, neural_strategy=None):
        self.cognitive = CognitiveOptimizer(neural_strategy=neural_strategy)
        self.use_mcts_endgame = True

        # Composable strategy components
        self.sun_logic = SunStrategy()
        self.hokum_logic = HokumStrategy()
        self.project_logic = ProjectStrategy()

    def get_decision(self, ctx: BotContext) -> dict:
        legal_indices = ctx.get_legal_moves()
        if not legal_indices:
            return {"cardIndex": -1, "reasoning": "No Legal Moves (Error)"}

        # --- SAWA CHECK (Grand Slam) ---
        sawa_decision = self.project_logic.check_sawa(ctx)
        if sawa_decision:
            return sawa_decision

        # --- AKKA CHECK (Master Declaration) ---
        akka_decision = self.project_logic.check_akka(ctx)
        if akka_decision:
            return akka_decision

        # --- COGNITIVE ENGINE (Oracle) ---
        if getattr(ctx, 'use_mcts', True):
            oracle_decision = self.cognitive.get_decision(ctx)
            if oracle_decision:
                return oracle_decision

        # --- STANDARD HEURISTICS ---
        # 0. Endgame Solver
        endgame_move = self.get_endgame_decision(ctx)
        if endgame_move:
            return endgame_move

        # 1. Strategy Dispatch
        decision = None
        if ctx.mode == 'SUN':
            decision = self.sun_logic.get_decision(ctx)
        elif ctx.mode == 'HOKUM':
            decision = self.hokum_logic.get_decision(ctx)

        if not decision:
            decision = {"action": "PLAY", "cardIndex": 0, "reasoning": "Fallback"}

        # 2. Declarations (Projects) - Trick 1 only
        self.project_logic.calculate_projects(ctx, decision)

        # 3. FINAL LEGALITY CHECK (Guardrail)
        self._validate_and_override_decision(ctx, decision)

        return decision

    def _validate_and_override_decision(self, ctx: BotContext, decision: dict):
        """Ensures the chosen move is legal, overriding if necessary."""
        if decision and decision.get('action') == 'PLAY':
            legal_indices = ctx.get_legal_moves()
            chosen_idx = decision.get('cardIndex')

            if chosen_idx not in legal_indices:
                if legal_indices:
                    import logging
                    logger = logging.getLogger("ai_worker")
                    logger.warning(
                        f"Bot {ctx.position} attempted ILLEGAL move: {ctx.hand[chosen_idx]}. "
                        f"Legal: {[ctx.hand[i] for i in legal_indices]}. OVERRIDING."
                    )
                    decision['cardIndex'] = legal_indices[0]
                    decision['reasoning'] += " (Legality Override)"

    def get_endgame_decision(self, ctx: BotContext):
        """Simple endgame check: all aces in Sun mode."""
        all_aces = all(c.rank == 'A' for c in ctx.hand)
        if all_aces and ctx.mode == 'SUN':
            return {"action": "PLAY", "cardIndex": 0, "reasoning": "Endgame Solver: All Masters"}
        return None
