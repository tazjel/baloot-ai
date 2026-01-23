import time
import json
import logging
from game_engine.logic.game import Game
from game_engine.models.player import Player
from ai_worker.strategies.playing import PlayingStrategy
from ai_worker.strategies.bidding import BiddingStrategy
from ai_worker.bot_context import BotContext
from game_engine.logic.utils import scan_hand_for_projects

# Configure logging for Arena (suppress debug noise)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Arena")

class Arena:
    def __init__(self):
        self.playing_strategy = PlayingStrategy()
        self.bidding_strategy = BiddingStrategy()

    def run_match(self, match_id="sim_1"):
        """
        Runs a full headless match between self-playing bots.
        Returns the full match history and result.
        """
        game = Game(room_id=match_id)
        
        # Add Players
        names = ["Bot_Bottom", "Bot_Right", "Bot_Top", "Bot_Left"]
        for i, name in enumerate(names):
            p = game.add_player(f"sid_{i}", name)
            p.is_bot = True
            
        # Start Game (Deals cards, sets phase to BIDDING)
        success = game.start_game()
        if not success:
            return {"error": "Failed to start game (not enough players?)"}
        
        steps = 0
        MAX_STEPS = 50000 # Safety limit (approx 2000 steps per game)
        
        while max(game.match_scores.values()) < 152 and steps < MAX_STEPS:
            steps += 1
            # 1. Get State
            if hasattr(game, 'bidding_engine') and game.bidding_engine:
                 game.bidding_engine.GABLAK_DURATION = -1 # Force Expiry
            
            if steps % 10000 == 0:
                 logger.info(f"Match {match_id} Step {steps}. Scores: {game.match_scores}")

            current_player_idx = game.current_turn
            
            # 1. Get State
            sid = game.players[current_player_idx].id
            state = game.get_game_state()
            ctx = BotContext(state, current_player_idx)
            
            decision = None
            
            # 2. Decision Logic
            # Note: We group all bidding-related phases
            if game.phase in ["BIDDING", "DOUBLING", "VARIANT_SELECTION", "GABLAK_WINDOW"]:
                try:
                    decision = self.bidding_strategy.get_decision(ctx)
                    action = decision.get('action')
                    suit = decision.get('suit')
                    
                    # Apply
                    res = game.handle_bid(current_player_idx, action, suit)
                    if res.get('error'):
                        logger.warning(f"Bid Error ({action}): {res}")
                        # Fallback to PASS to unblock
                        game.handle_bid(current_player_idx, "PASS")
                        
                except Exception as e:
                    logger.error(f"Bidding Crash: {e}")
                    game.handle_bid(current_player_idx, "PASS")
            elif game.phase == "PLAYING":
                try:
                    decision = self.playing_strategy.get_decision(ctx)
                    card_idx = decision.get('cardIndex', 0)
                    
                    # Calculate Projects if Trick 1
                    metadata = {}
                    if len(game.round_history) == 0:
                         # Scan for projects
                         # Note: ctx.hand is List[Card]. game.game_mode is 'SUN'/'HOKUM'
                         if game.game_mode:
                              projects = scan_hand_for_projects(ctx.hand, game.game_mode)
                              if projects:
                                   metadata['declarations'] = projects
                                   # logger.info(f"P{current_player_idx} Declarations: {[p['type'] for p in projects]}")

                    # Apply
                    res = game.play_card(current_player_idx, card_idx, metadata)
                    
                    if res.get('error'):
                         logger.warning(f"Play Error ({card_idx}): {res}")
                         # Fallback: Try playing card 0, then 1...
                         for k in range(len(ctx.hand)):
                             res_retry = game.play_card(current_player_idx, k)
                             if not res_retry.get('error'):
                                 break
                except Exception as e:
                     logger.error(f"Playing Crash: {e}")
                     # Try to recover?
                     pass
            
            elif game.phase == "FINISHED":
                 # Round Finished. Start Next Round.
                 # Note: start_game() in current engine preserves match scores but re-rolls dealer (known quirk)
                 game.start_game()
                 logger.info(f"Round Finished. Scores: {game.match_scores}. Starting next round.")
                 
            else:
                # Should not happen in headless unless phase drift
                logger.warning(f"Unknown Phase in Arena: {game.phase}")
                break

        return {
            "match_id": match_id,
            "winner": "us" if game.match_scores["us"] >= 152 else ("them" if game.match_scores["them"] >= 152 else None),
            "steps": steps,
            "final_scores": game.match_scores,
            "history_length": len(game.full_match_history),
            "match_history": game.full_match_history
        }

if __name__ == "__main__":
    arena = Arena()
    start = time.time()
    result = arena.run_match()
    duration = time.time() - start
    print(f"Match Finished in {duration:.2f}s")
    print(f"Winner: {result['winner']}")
    print(f"History Rounds: {result['history_length']}")
