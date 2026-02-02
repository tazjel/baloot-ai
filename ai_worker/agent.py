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
             p_name = p_data.get('name', 'Bot')
             profile = self.personality
             
             # Director Override
             explicit_profile = p_data.get('profile')
             if explicit_profile:
                  if explicit_profile in PROFILES:
                       profile = PROFILES[explicit_profile]
                  elif explicit_profile == 'Balanced':
                       profile = PROFILES['Balanced']
             else:
                 # Fallback to Name Parsing
                 if "Aggressive" in p_name: profile = PROFILES['Aggressive']
                 elif "Conservative" in p_name: profile = PROFILES['Conservative']
                 elif "Balanced" in p_name: profile = PROFILES['Balanced']
            
             # Use Typed Context
             ctx = BotContext(game_state, player_index, personality=profile)
 
             # 1. REFEREE: Check Mandatory Rules (Sawa/Qayd)
             # 1.1 Sawa Response
             if sawa_resp := self.referee.check_sawa(ctx, game_state):
                  return sawa_resp
             
             # Pub Sub: Theory of Mind (if active)
             # Only run occasionally or every move? Every move is fine for now on GPU/fast CPU.
             if ctx.phase == 'PLAYING':
                  try:
                      guesses = ctx.guess_hands()
                      if guesses:
                          gid = game_state.get('gameId', 'unknown')
                          self.brain.publish_mind_map(gid, player_index, guesses)
                  except Exception as me:
                      pass # Don't block game for metrics

             # 1.15 SHERLOCK TRIGGER (The Watchdog)
             # If valid game phase and NO Qayd active, check for illegal moves to catch them.
             if ctx.phase == 'PLAYING' and not (game_state.get('qaydState') or {}).get('active'):
                 # Check Table Cards
                 table_cards = game_state.get('tableCards', [])
                 for tc in table_cards:
                     if (tc.get('metadata') or {}).get('is_illegal'):
                         # Found one!
                         offender_pos = tc.get('playedBy')
                         logger.warning(f"[SHERLOCK] Detected illegal move by {offender_pos} in Current Trick. TRIGGERING QAYD!")
                         return {"action": "QAYD_TRIGGER"}
                 
                 # Check Last Trick (Crucial for 4th player cheats)
                 last_trick = game_state.get('lastTrick')
                 if last_trick and last_trick.get('metadata'):
                      for meta in last_trick['metadata']:
                           if meta and meta.get('is_illegal'):
                                logger.warning(f"[SHERLOCK] Detected illegal move in Last Trick. TRIGGERING QAYD!")
                                return {"action": "QAYD_TRIGGER"}

             # 1.2 Qayd Claim (Sherlock Logic)
             qayd_state = game_state.get('qaydState')
             if qayd_state and qayd_state.get('active'):
                 # Sherlock Bot Logic: If I am the reporter, investigate and accuse.
                 reporter_pos = qayd_state.get('reporter')
                 print(f"[SHERLOCK] Qayd Active. Reporter: {reporter_pos}, Me: {ctx.position}")
                 
                 # Check if I am the reporter (by position name OR index)
                 # ctx.position is 'Bottom', 'Right', etc.
                 # ctx.player_index is 0-3
                 
                 is_me = False
                 if reporter_pos == ctx.position:
                      is_me = True
                 elif str(reporter_pos) == str(ctx.player_index):
                      is_me = True
                 elif isinstance(reporter_pos, int) and reporter_pos == ctx.player_index:
                      is_me = True
                      
                 if is_me:
                      logger.info(f"[SHERLOCK] I am the reporter ({reporter_pos}). Investigation starting...")
                      # 1. Brief Pause (simulating reaction time)
                      time.sleep(1) # Reduced for responsiveness 
                      
                      # 2. Find the Crime
                      # We look for the last card played that has 'is_illegal' metadata
                      table_cards = game_state.get('tableCards', [])
                      full_history = game_state.get('fullMatchHistory', []) # Or we iterate recent tricks if needed
                      
                      # Simple approach: Check active table cards first
                      crime_card = None
                      proof_card = None
                      violation_type = 'REVOKE'
                      
                      # Look at current table
                      if table_cards:
                          for tc in reversed(table_cards):
                              if (tc.get('metadata') or {}).get('is_illegal'):
                                  crime_card = tc['card']
                                  # Proof is usually the first card of the trick (the lead)
                                  if table_cards:
                                      proof_card = table_cards[0]['card']
                                  break
                     
                      if not crime_card:
                          # Check Last Trick (if table cleared)
                          last_trick = game_state.get('lastTrick')
                          if last_trick and last_trick.get('metadata'):
                               for i, meta in enumerate(reversed(last_trick['metadata'])):
                                    if meta and meta.get('is_illegal'):
                                         # Need to get card from cards array
                                         # last_trick['cards'] is list of play objects
                                         idx = len(last_trick['cards']) - 1 - i
                                         play = last_trick['cards'][idx]
                                         crime_card = play['card']
                                         proof_card = last_trick['cards'][0]['card'] # Proof is lead
                                         break


                      if crime_card:
                         logger.info(f"[SHERLOCK] Crime Solved! {crime_card} is illegal. Accusing...")
                         return {
                             "action": "QAYD_ACCUSATION",
                             "accusation": {
                                 "crime_card": crime_card,
                                 "proof_card": proof_card or crime_card,
                                 "violation_type": "REVOKE" # Default for now
                             }
                         }
                      else:
                         logger.error("[SHERLOCK] False Alarm? Cancelling.")
                         return {"action": "QAYD_CANCEL"} # Should ideally cancel
                 
                 else:
                      # Not the reporter -> Wait
                      return {"action": "WAIT", "reason": "Qayd Investigation"}

             # Legacy/Backup Check
             if qayd_claim := self.referee.check_qayd(ctx, game_state):
                 return qayd_claim

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
