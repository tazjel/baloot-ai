import os
import time
import logging
import traceback

# New Modular Imports
from ai_worker.bot_context import BotContext
from ai_worker.strategies.bidding import BiddingStrategy
from ai_worker.strategies.playing import PlayingStrategy
from ai_worker.strategies.neural import NeuralStrategy
from ai_worker.personality import PROFILES, BALANCED
from ai_worker.memory import CardMemory

# Core Architecture Modules
from ai_worker.brain_client import BrainClient
from ai_worker.referee_observer import RefereeObserver

# Logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BotAgent:
    def __init__(self):
        self.memory = CardMemory()
        self.current_game_id = None
        
        # Personality
        self.personality = BALANCED # Default
        
        # Neural Brain
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'strategy_net_best.pth')
        self.neural_strategy = NeuralStrategy(model_path)

        # Strategies
        self.bidding_strategy = BiddingStrategy()
        self.playing_strategy = PlayingStrategy(neural_strategy=self.neural_strategy)

        # Core Components
        self.brain = BrainClient()
        self.referee = RefereeObserver()
        
    def get_decision(self, game_state, player_index):
        try:
             # DEBUG: Trace Illegal Flags
             table = game_state.get('tableCards', [])
             for tc in table:
                  if (tc.get('metadata') or {}).get('is_illegal'):
                       logger.error(f"[BOT-EYE] SAW ILLEGAL MOVE! {tc}")

             # Determine Personality
             p_data = game_state['players'][player_index]
             
             # Context Wrapper
             ctx = BotContext(game_state, player_index)

             # 1. REFEREE: Check Mandatory Rules (Sawa/Qayd)

             # 1.1 Sawa Response
             if sawa_resp := self.referee.check_sawa(ctx, game_state):
                 return sawa_resp

             # 1.2 Qayd Claim (Sherlock Logic)
             qayd_state = game_state.get('qaydState') or game_state.get('qayd_state') # Handle snake_case
             is_qayd_active = qayd_state and qayd_state.get('active')

             if is_qayd_active:
                 reporter_pos = qayd_state.get('reporter')
                 if reporter_pos != ctx.position:
                      # Not the reporter -> Wait
                      return {"action": "WAIT", "reason": "Qayd Investigation"}

             elif ctx.phase == 'PLAYING':
                 # Check Game ID reset
                 game_id = game_state.get('gameId')
                 if game_id != self.current_game_id:
                      logger.info(f"New Game Detected: {game_id}. Resetting Memory.")
                      self.memory.reset()
                      self.current_game_id = game_id

                 # PROOF-BASED DETECTION (Memory Scan)
                 if crime := self.memory.scan_and_populate(game_state):
                      logger.info(f"[SHERLOCK] Crime Solved! {crime['crime_card']} is illegal. Reason: {crime['reason']}")
                      return {
                          "action": "QAYD_ACCUSATION",
                          "accusation": {
                              "crime_card": crime['crime_card'],
                              "proof_card": crime['proof_card'],
                              "violation_type": crime['violation_type']
                          }
                      }

             # 2. THE BRAIN: Check for Learned Moves (Redis)
             if ctx.phase in ['PLAYING', 'BIDDING']:
                  try:
                       # Generate Hash
                       import hashlib, json
                       state_str = json.dumps({
                           'hand': [str(c) for c in ctx.hand],
                           'table': [str(tc['card']) for tc in ctx.table_cards],
                           'phase': ctx.phase,
                           'bid': ctx.raw_state.get('bid'),
                           'dealer': ctx.dealer_index
                       }, sort_keys=True)
                       context_hash = hashlib.md5(state_str.encode()).hexdigest()
                       
                       # Lookup
                       brain_move = self.brain.lookup_move(context_hash)
                       
                       if brain_move:
                            logger.info(f"🧠 THE BRAIN found a move for {context_hash}!")
                            
                            if ctx.phase == 'PLAYING':
                                 target_rank = brain_move.get('rank')
                                 target_suit = brain_move.get('suit')
                                 for i, c in enumerate(ctx.hand):
                                      if c.rank == target_rank and c.suit == target_suit:
                                           return {
                                               "action": "PLAY", 
                                               "cardIndex": i, 
                                               "reasoning": "Brain Override: " + brain_move.get('reason', '')
                                           }
                                 logger.warning(f"Brain suggested {target_rank}{target_suit} but not in hand")
                            else:
                                 return brain_move
                                 
                       # Queue for Analysis (The Scout)
                       self._queue_analysis(ctx, context_hash)
 
                  except Exception as e:
                       logger.error(f"[BRAIN] Integration Error: {e}")
 
             # 3. STRATEGY CONFIGURATION
             # Allow per-player config in game_state['players'][idx].get('strategy')
             # 'neural' -> Direct Neural Inference (Speed/Imitation)
             # 'mcts' / 'hybrid' -> Neural-Guided MCTS (Strength/Search)
             # 'heuristic' -> Rule-based (Baseline)
             
             player_data = game_state['players'][player_index]
             strategy_cfg = player_data.get('strategy', 'heuristic') # Default to heuristic if unspecified? Or balanced?
             
             # Defaults
             use_neural_direct = False
             ctx.use_mcts = True # Default to using Brain
            
             if strategy_cfg == 'heuristic':
                 use_neural_direct = False
                 ctx.use_mcts = False # Force Pure Rules
                 
             elif strategy_cfg == 'neural':
                 use_neural_direct = True and self.neural_strategy.enabled
                 ctx.use_mcts = False # Disable MCTS to test pure network
                 
             elif strategy_cfg in ['mcts', 'hybrid']:
                 use_neural_direct = False # Do not shortcut
                 ctx.use_mcts = True 
 
             # 4. NEURAL DIRECT EXECUTION
             if ctx.phase == 'PLAYING' and use_neural_direct:
                  neural_move = self.neural_strategy.get_decision(ctx)
                  if neural_move:
                       return neural_move
 
             # 4.5. DESPERATION CHEATING (The Liar)
             # If losing badly and Strict Mode is OFF, consider lying.
             strict_mode = game_state.get('strictMode', False)
             if ctx.phase == 'PLAYING' and not strict_mode:
                  # Check Score Differential
                  scores = game_state.get('matchScores', {'us': 0, 'them': 0})
                  my_score = scores.get(ctx.team, 0)
                  their_score = scores.get('them' if ctx.team == 'us' else 'us', 0)
                  
                  is_losing_badly = (their_score - my_score) > 20 # Low threshold for testing
                  
                  if is_losing_badly:
                       # Look for a Cheat
                       # Simple Heuristic: If I have a Master Card (Ace/Trump) that is ILLEGAL, play it.
                       legal_indices = ctx.get_legal_moves()
                       
                       for i, card in enumerate(ctx.hand):
                            if i not in legal_indices:
                                 # This is an illegal card. Is it good?
                                 # If it's an Ace or Trump, maybe it wins?
                                 # Only cheat if it's worth it (Master Card).
                                 is_master = ctx.is_master_card(card)
                                 if is_master:
                                      logger.info(f"😈 [DIRTY] Desperation! {ctx.position} is losing and chooses to LIE with {card}.")
                                      return {
                                          "action": "PLAY", 
                                          "cardIndex": i, 
                                          "reasoning": "Desperation Cheat (Lying with Master Card)"
                                      }

             # 5. STRATEGY DISPATCH (MCTS + Heuristics)
             if ctx.phase in ['BIDDING', 'DOUBLING']:
                 return self.bidding_strategy.get_decision(ctx)
                 
             elif ctx.phase == 'PLAYING':
                 return self.playing_strategy.get_decision(ctx)
            
             return {"action": "PASS"}
 
        except Exception as e:
            logger.error(f"Bot Agent Error: {e}")
            traceback.print_exc()
            return {"action": "PASS", "cardIndex": 0}

    def _queue_analysis(self, ctx: BotContext, context_hash: str):
        """Prepare payload and delegate to BrainClient"""
        try:
             import json
             # Prepare Payload
             payload = {
                 'context_hash': context_hash,
                 'timestamp': time.time(),
                 'game_id': ctx.raw_state.get('gameId', 'unknown'),
                 'player_index': ctx.player_index,
                 'game_context': {
                     'mode': ctx.mode,
                     'trump': ctx.trump,
                     'hand': [c.to_dict() for c in ctx.hand],
                     'table': [tc['card'].to_dict() for tc in ctx.table_cards],
                     # Simplified for brevity
                     'phase': ctx.phase
                 }
             }
             self.brain.queue_analysis(payload)
        except Exception:
             pass

    def capture_round_data(self, round_snapshot):
        """Delegate to BrainClient"""
        self.brain.capture_round_data(round_snapshot)

# Singleton Instance (Required by server and tests)
bot_agent = BotAgent()
