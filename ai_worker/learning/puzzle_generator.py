
import os
import json
import time
import copy
import logging
from game_engine.models.card import Card

logger = logging.getLogger(__name__)

class PuzzleGenerator:
    """
    Converts live game blunders into Academy Puzzles.
    """
    def __init__(self, puzzle_dir="server/content/puzzles"):
        self.puzzle_dir = puzzle_dir
        os.makedirs(puzzle_dir, exist_ok=True)
        
    def create_from_blunder(self, ctx, human_card, best_card, analysis):
        """
        Creates a JSON puzzle from a detected blunder.
        
        Args:
            ctx (BotContext): The state when the blunder occurred.
            human_card (Card): The suboptimal card played.
            best_card (Card): The optimal card suggested.
            analysis (dict): MCTS analysis details.
        """
        try:
            # 1. Unique ID
            ts = int(time.time())
            game_id = ctx.raw_state.get('gameId', 'unknown')
            round_num = len(ctx.raw_state.get('roundHistory', [])) + 1
            # Sanitized ID
            safe_game_id = "".join(c for c in game_id if c.isalnum() or c in '_-')
            puzzle_id = f"exam_{ts}_{safe_game_id}"
            
            # 2. Sanitize State (Hide Opponent Info)
            initial_state = copy.deepcopy(ctx.raw_state)
            
            # Identify "Me" (The Human at ctx.player_index)
            # ctx.player_index is the human who blundered
            human_idx = ctx.player_index
            
            for p in initial_state.get('players', []):
                # BotContext players usually have 'index' or we infer from position order?
                # GameState players: { "id", "name", "position", "hand": [...], "score"... }
                # We can't rely on 'id' matching ctx.player_index directly without strict logic.
                # However, ctx.player_index matches the index in game.players list.
                # Let's hope initial_state['players'] is ordered list? YES (game.py line 91).
                
                # Logic: If this is NOT the human, clear their hand.
                # Find index of this player dict
                try:
                    p_idx = initial_state['players'].index(p)
                    if p_idx != human_idx:
                         p['hand'] = [] # Hide cards
                         # We could populate 'faceDown' placeholders if frontend supports it
                except ValueError:
                    pass
            
            # 3. Description
            mode = ctx.mode
            desc = f"You played {human_card}. The Professor found a better line. Can you find it?"
            
            # 4. Construct Puzzle
            puzzle = {
                "id": puzzle_id,
                "title": f"Professor's Exam: {mode} Blunder",
                "description": desc,
                "difficulty": "Intermediate", 
                "tags": ["Professor", mode, "Blunder"],
                "initial_state": initial_state,
                "solution": {
                    "type": "sequence",
                    "data": [str(best_card)]
                }
            }
            
            self.save_puzzle(puzzle)
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate puzzle: {e}", exc_info=True)
            return False

    def save_puzzle(self, puzzle_dict):
        fname = f"{puzzle_dict['id']}.json"
        path = os.path.join(self.puzzle_dir, fname)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(puzzle_dict, f, indent=4)
        logger.info(f"Generated Puzzle: {path}")
