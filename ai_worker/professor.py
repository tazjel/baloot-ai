import logging
import random
from ai_worker.agent import BotAgent, bot_agent
from game_engine.logic.game import Game
from game_engine.models.card import Card

logger = logging.getLogger(__name__)

class Professor:
    def __init__(self):
        self.agent = bot_agent # Reuse the existing singleton agent
        self.enabled = True 
        # Thresholds
        self.blunder_threshold = 0.8 # Probability diff? Or Score diff?
        
    def check_move(self, game: Game, player_index: int, card_index: int) -> dict | None:
        """
        Analyzes the human's intended move.
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
            
            # 1. Ask the Expert (Bot) what it would do
            # We need to give the bot the full state
            game_state = game.get_game_state()
            
            # The agent usually returns { 'action': 'PLAY', 'cardIndex': i, 'reasoning': ... }
            # We want the BEST move.
            # NOTE: BotAgent.get_decision includes randomness or personality traits.
            # For the Professor, we might want the "Optimal" move (e.g., MCTS or 'Balanced' profile).
            
            # For now, let's trust the standard BotAgent decision logic.
            # Ideally, we should enable maximum strength here.
            
            bot_decision = self.agent.get_decision(game_state, player_index)
            
            if bot_decision.get('action') != 'PLAY':
                return None
            
            bot_card_idx = bot_decision.get('cardIndex')
            if bot_card_idx is None:
                return None
                
            bot_card = player.hand[bot_card_idx]
            
            # 2. Compare
            if human_card.id == bot_card.id:
                return None # Human played exactly what Bot recommends. Good job!
                
            # 3. Simple Heuristic Blunder Check (Placeholder for MCTS Value Analysis)
            # If Human plays non-trump while holding Ace of led suit?
            # If Human plays low trump when they could eat?
            
            # For Phase 1 (MVP):
            # If Bot is VERY strict about a rule (e.g. Legal move), game engine handles it.
            # Professor checks for STRATEGIC blunders.
            
            # EXAMPLE: "You played a King but the Ace is still out!"
            # This requires inspecting memory or state.
            
            reason = bot_decision.get('reasoning', 'I would have played differently.')
            
            # Random chance to intervene to avoid annoyance (or only on 'High Confidence' diffs)
            # For demo/MVP, let's intervene if move is different and reasoned.
            
            # IMPORTANT: Don't interrupt trivial differences.
            # How to measure triviality?
            # If both are legal and similar rank?
            
            return {
                "type": "BLUNDER",
                "message": f"Professor: Wait! I wouldn't play {human_card}. {reason}",
                "better_card": bot_card.to_dict(),
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Professor Error: {e}")
            return None

# Singleton
professor = Professor()
