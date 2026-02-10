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
        from ai_worker.strategies.sherlock import SherlockStrategy
        self.bidding_strategy = BiddingStrategy()
        self.playing_strategy = PlayingStrategy(neural_strategy=self.neural_strategy)
        self.sherlock = SherlockStrategy(self) # New Detective Module

        # Core Components
        self.brain = BrainClient()

        
    def get_decision(self, game_state, player_index):
        try:
             # RESET: If no Qayd active, ensure flag is cleared (prevents permanent blocking)
             qayd_state = game_state.get('qaydState', {})
             
             # Prevent Zombie Locks (Phase 2 - Ghost Buster)
             if not qayd_state.get('active'):
                 self.sherlock.pending_qayd_trigger = False
             
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

             # 1. Sawa check handled by PlayingStrategy.project_logic
             
             # 1.2 Detect Human Lies (Project Blunders)
             # If server flagged an invalid project in the previous turn/event log (hypothetically)
             # or we scan the table metadata for "intervention" flags.
             
             # Current implementation of handle_akka/sawa returns error dicts to the caller (API).
             # It doesn't put "intervention" in game_state directly unless we added it.
             # However, if we want the Bot to CATCH it, the Bot needs to see the invalid claim.
             
             # New Logic: Inspect 'intervention' field in Table or specific GameState flag
             # The ProjectManager puts it in... wait, it returns it to the API response.
             # So the CLIENT sees it. The BOT (via socket) might not see the immediate API response of the human.
             # BUT: The server likely broadcasts an event or updates state.
             
             # Assumption: The server updates `game_state['latest_event']` or similar.
             # For now, let's assume the helper `self.sherlock.scan_for_blunders` handles this
             # if we point it to the right data.
             
             # Let's delegate to Sherlock entirely for this.
             if hasattr(self.sherlock, 'detect_invalid_projects'):
                  qayd = self.sherlock.detect_invalid_projects(game_state)
                  if qayd: return qayd
             
             # Pub Sub: Theory of Mind (if active)
             if ctx.phase == 'PLAYING':
                  try:
                      guesses = ctx.guess_hands()
                      if guesses:
                          gid = game_state.get('gameId', 'unknown')
                          self.brain.publish_mind_map(gid, player_index, guesses)
                  except Exception as me:
                      pass 

             # 1.15 SHERLOCK (The Detective) - Delegated
             sherlock_action = self.sherlock.scan_for_crimes(ctx, game_state)
             if sherlock_action:
                  return sherlock_action


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
 
             # 4.5. DESPERATION CHEATING (The Liar) - REMOVED
             # We want to ensure bots NEVER make illegal moves.


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
