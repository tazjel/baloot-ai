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
            logger.debug(f"PROFESSOR: Analyzing for {player.name} ({player_index}). Hand: {[str(c) for c in player.hand]}")
            logger.debug(f"PROFESSOR: Table Context: {[f'{tc.get('playedBy')}:{str(tc.get('card'))}' for tc in game.table_cards]}")
            
            analysis = self.cognitive.analyze_position(ctx)
            
            if not analysis:
                logger.warning("PROFESSOR: MCTS returned NO analysis.")
                return None
                
            best_move_idx = analysis['best_move']
            move_values = analysis['move_values']
            
            # DEBUG LOG: Dump all considered moves and their legality
            if hasattr(game, 'is_valid_move'):
                 for m_idx, stats in move_values.items():
                      c_card = player.hand[m_idx]
                      is_real_legal = game.is_valid_move(c_card, player.hand)
                      suffix = " (ILLEGAL in Real Game!)" if not is_real_legal else ""
                      if not is_real_legal:
                           logger.error(f"PROFESSOR BUG: MCTS considers ILLEGAL move {c_card} as valid candidate! Stats: {stats}")
                      else:
                           logger.debug(f"MCTSCandidate: {c_card} -> WinRate: {stats['win_rate']:.2f} ({stats['visit_count'] if 'visit_count' in stats else stats.get('visits')}v)")

            
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
                logger.info(f"PROFESSOR: Opportunity Detected! Human={human_card} ({human_ev:.2f}) vs Best={player.hand[best_move_idx]} ({best_ev:.2f}). Diff={diff:.2f}")
            
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
            
            # [NEW] Generate Puzzle for Blunders
            best_card = player.hand[best_move_idx]
            
            if blunder_type == "BLUNDER":
                try:
                    # Lazy init to avoid circular deps if any
                    from ai_worker.learning.puzzle_generator import PuzzleGenerator
                    pgen = PuzzleGenerator()
                    pgen.create_from_blunder(ctx, human_card, best_card, analysis)
                except Exception as e:
                    logger.error(f"Professor failed to generate puzzle: {e}")

            # 5. Construct Message
            # Safety Check: Is the "Better Card" actually legal?
            if hasattr(game, 'is_valid_move') and not game.is_valid_move(best_card, player.hand):
                 logger.critical(f"PROFESSOR FATAL: Suggested ILLEGAL MOVE {best_card} as better option! Aborting intervention.")
                 return None

            intro = random.choice(self.responses[blunder_type])
            percentage = int(diff * 100)
            reason = f"Playing {best_card} is {percentage}% better."
            
            # ... rest of code (Candidate extraction) ...
            
            # 4b. Extract Candidate Moves (Holographic Thought)
            candidates = []
            sorted_moves = sorted(move_values.items(), key=lambda item: item[1]['win_rate'], reverse=True)
            
            for rank, (m_idx, stats) in enumerate(sorted_moves[:3]):
                # Skip if it is the played card
                if m_idx == card_index:
                    continue
                    
                c_card = player.hand[m_idx]
                
                # Double check candidate legality
                if hasattr(game, 'is_valid_move') and not game.is_valid_move(c_card, player.hand):
                     continue # Skip illegal candidates from UI suggestion

                c_diff = stats['win_rate'] - human_ev
                
                candidates.append({
                    "card": c_card.to_dict(),
                    "win_rate": stats['win_rate'],
                    "visits": stats['visits'],
                    "diff": c_diff,
                    "rank": rank + 1
                })

            intervention = {
                "type": blunder_type,
                "message": f"Professor: {intro} {reason}",
                "better_card": best_card.to_dict(),
                "reason": reason,
                "diff": diff,
                "candidates": candidates
            }
            logger.info(f"Professor: Triggering Intervention: {intervention}")
            return intervention
            
        except Exception as e:
            logger.error(f"Professor Error: {e}", exc_info=True)
            return None

# Singleton
professor = Professor()
