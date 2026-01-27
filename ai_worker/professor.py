import logging
import random
from ai_worker.agent import BotAgent, bot_agent
from ai_worker.cognitive import CognitiveOptimizer
from ai_worker.bot_context import BotContext
from game_engine.logic.game import Game
from game_engine.models.card import Card

logger = logging.getLogger(__name__)

class Professor:
    def __init__(self):
        self.agent = bot_agent # Reuse the existing singleton agent
        self.cognitive = CognitiveOptimizer(use_inference=True)
        self.enabled = True 
        # Thresholds
        self.blunder_threshold = 0.20 # EV Difference triggering a "Blunder"
        self.mistake_threshold = 0.10 # EV Difference triggering a "Mistake"
        self.minor_threshold = 0.05   # EV Difference triggering a "Note"
        
        # Responses
        self.responses = {
            "BLUNDER": [
                "Whoa! That move is risky.",
                "I wouldn't recommend that.",
                "Are you sure? That loses significant value."
            ],
            "MISTAKE": [
                "There is a better option.",
                "Think twice about that.",
                "I see a stronger play."
            ]
        }
        
    def check_move(self, game: Game, player_index: int, card_index: int) -> dict | None:
        """
        Analyzes the human's intended move using MCTS.
        Returns None if move is fine.
        Returns dict with { 'warning': str, 'better_move': str } if it's a blunder.
        """
        if not self.enabled:
            return None
            
        try:
            player = game.players[player_index]
            if card_index < 0 or card_index >= len(player.hand):
                return None 
            
            human_card = player.hand[card_index]
            
            # 1. Create Context for Human
            game_state = game.get_game_state()
            ctx = BotContext(game_state, player_index) # Personality checks not needed for MCTS
            
            # 2. Run MCTS Analysis
            # logger.debug(f"Professor: Analyzing position for {player.name} playing {human_card}...")
            
            analysis = self.cognitive.analyze_position(ctx)
            
            if not analysis:
                # Fallback to simple check if MCTS fails
                return None
                
            best_move_idx = analysis['best_move']
            move_values = analysis['move_values']
            
            if card_index == best_move_idx:
                return None # Human played the optimal move!
                
            # 3. Compare EV (Expected Value)
            human_stats = move_values.get(card_index)
            best_stats = move_values.get(best_move_idx)
            
            if not human_stats or not best_stats:
                return None
                
            human_ev = human_stats['win_rate'] # Normalized 0-1 (Wins / Visits)
            best_ev = best_stats['win_rate']
            human_visits = human_stats['visits']
            best_visits = best_stats['visits']
            
            diff = best_ev - human_ev
            
            if diff > 0.05:
                logger.debug(f"PROFESSOR: Human={human_card} ({human_ev:.2f}, {human_visits}v) Best={player.hand[best_move_idx]} ({best_ev:.2f}, {best_visits}v) Diff={diff:.2f}")
            
            # 4. Determine Blunder Level
            blunder_type = None
            if diff >= self.blunder_threshold:
                blunder_type = "BLUNDER"
            elif diff >= self.mistake_threshold:
                blunder_type = "MISTAKE"
            # elif diff >= self.minor_threshold:
            #     blunder_type = "NOTE" 
            
            if not blunder_type:
                return None
                
            # 5. Construct Message
            best_card = player.hand[best_move_idx]
            
            intro = random.choice(self.responses[blunder_type])
            reason = f"Playing {best_card} is calculated to be +{int(diff*100)}% better."
            
            intervention = {
                "type": blunder_type,
                "message": f"Professor: {intro} {reason}",
                "better_card": best_card.to_dict(),
                "reason": reason,
                "diff": diff
            }
            logger.info(f"Professor: Triggering Intervention: {intervention}")
            return intervention
            
        except Exception as e:
            logger.error(f"Professor Error: {e}", exc_info=True)
            return None

# Singleton
professor = Professor()
