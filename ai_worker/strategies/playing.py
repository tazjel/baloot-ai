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
        """Smart endgame solver for last few tricks."""
        hand_size = len(ctx.hand)
        
        # 1. LAST TRICK: Only one card — play it
        if hand_size == 1:
            return {"action": "PLAY", "cardIndex": 0, "reasoning": "Endgame: Last Card"}
        
        # Only activate for endgame (≤3 cards)
        if hand_size > 3:
            return None
        
        # 2. ALL MASTERS: If every card is a master, lead highest-value first
        all_masters = all(ctx.is_master_card(c) for c in ctx.hand)
        if all_masters and not ctx.table_cards:
            # Leading — play highest point value master first to extract max points
            from game_engine.models.constants import POINT_VALUES_SUN, POINT_VALUES_HOKUM
            pv = POINT_VALUES_HOKUM if ctx.mode == 'HOKUM' else POINT_VALUES_SUN
            
            best_idx = 0
            best_pts = -1
            for i, c in enumerate(ctx.hand):
                pts = pv.get(c.rank, 0)
                if pts > best_pts:
                    best_pts = pts
                    best_idx = i
            return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Endgame: Cashing Masters (Highest Value)"}
        
        # 3. HOKUM ENDGAME: If we hold all remaining trumps + side masters,
        #    lead trumps first to clear, then cash side masters
        if ctx.mode == 'HOKUM' and not ctx.table_cards:
            trump = ctx.trump
            my_trumps = [i for i, c in enumerate(ctx.hand) if c.suit == trump]
            my_non_trumps = [i for i, c in enumerate(ctx.hand) if c.suit != trump]
            
            if my_trumps and my_non_trumps:
                # Check if all non-trumps are masters
                non_trump_all_masters = all(ctx.is_master_card(ctx.hand[i]) for i in my_non_trumps)
                if non_trump_all_masters:
                    # Check if opponents might still have trumps
                    opponents_have_trump = False
                    my_team = ctx.team
                    for p in ctx.raw_state.get('players', []):
                        if p.get('team') != my_team:
                            if not ctx.is_player_void(p.get('position'), trump):
                                opponents_have_trump = True
                                break
                    
                    if opponents_have_trump:
                        # Lead trump to clear enemy trumps, then cash side masters
                        from game_engine.models.constants import ORDER_HOKUM
                        best_trump = my_trumps[0]
                        best_strength = -1
                        for i in my_trumps:
                            try:
                                s = ORDER_HOKUM.index(ctx.hand[i].rank)
                                if s > best_strength:
                                    best_strength = s
                                    best_trump = i
                            except ValueError:
                                continue
                        return {"action": "PLAY", "cardIndex": best_trump, "reasoning": "Endgame: Drawing Trump Before Cashing"}
                    else:
                        # No enemy trumps — cash highest-value side master
                        from game_engine.models.constants import POINT_VALUES_SUN
                        best_idx = my_non_trumps[0]
                        best_pts = -1
                        for i in my_non_trumps:
                            pts = POINT_VALUES_SUN.get(ctx.hand[i].rank, 0)
                            if pts > best_pts:
                                best_pts = pts
                                best_idx = i
                        return {"action": "PLAY", "cardIndex": best_idx, "reasoning": "Endgame: Cashing Side Master"}
        
        return None
