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
        self.brain = BrainClient()
        self.referee = RefereeObserver()
        
        # Anti-Spam Memory
        self.reported_crimes = set() # Stores (round_num, trick_idx, card_idx)
        self.pending_qayd_trigger = False  # Global lock to prevent multiple bots triggering Qayd
        
    def _check_crime_logic(self, ctx, card_dict, played_by_pos, source="Table"):
        """
        Helper to check a card play for contractions (Sherlock Logic).
        """
        from game_engine.models.card import Card
        
        # 1. Team Loyalty Check (Omerta)
        offender_team = ctx.players_team_map.get(played_by_pos)
        my_team = ctx.team
        
        if offender_team == my_team:
             return None
             
        # 2. Rival Aggression (Check Memory)
        c_obj = Card(card_dict['suit'], card_dict['rank'])
        contradiction = ctx.memory.check_contradiction(played_by_pos, c_obj)
        
        if contradiction:
             logger.info(f"[SHERLOCK] 🕵️‍♂️ {ctx.position} Caught {played_by_pos}! {contradiction} (Source: {source})")
             # SILENCING SENSITIVE SHERLOCK temporarily to improve UX (prevent constant interruptions)
             return "QAYD_TRIGGER"
             # return None
        return None
        
    def get_decision(self, game_state, player_index):
        try:
             # RESET: If no Qayd active, ensure flag is cleared (prevents permanent blocking)
             qayd_state = game_state.get('qaydState', {})
             if not qayd_state.get('active'):
                 self.pending_qayd_trigger = False
             
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

             # 1.15 SHERLOCK TRIGGER (Organic, Team-Aware, & Memory-Based)
             # If valid game phase and NO Qayd active, check for visual contradictions (The "Second Card" Trigger).
             if ctx.phase == 'PLAYING' and not (game_state.get('qaydState') or {}).get('active') and not self.pending_qayd_trigger:
                 from game_engine.models.card import Card
                 


                 # A. Check Current Table (Live Detection)
                 table_cards = game_state.get('tableCards', [])
                 round_num = len(game_state.get('roundHistory', []))
                 current_trick_idx = len(game_state.get('currentRoundTricks', []))
                 for card_idx, tc in enumerate(table_cards):
                      # ANTI-SPAM: Create unique crime ID for this specific card play
                      crime_id = (round_num, current_trick_idx, card_idx, tc['card'].get('suit'), tc['card'].get('rank'))
                      if crime_id in self.reported_crimes:
                          continue  # Already reported this exact crime
                      action = self._check_crime_logic(ctx, tc['card'], tc['playedBy'], "Current Trick")
                      if action:
                          self.reported_crimes.add(crime_id)
                          self.pending_qayd_trigger = True  # Lock to prevent other bots
                          return {"action": action}
                 
                 # B. Check Last Trick (Post-Mortem Detection)
                 # Crucial for catching the 4th player who plays illegal, then trick clears immediately.
                 last_trick = game_state.get('lastTrick')
                 if last_trick and last_trick.get('cards'):
                      # last_trick cards are dicts or objects? game.py says serialized to dicts.
                      # structure: {'cards': [{'rank':.., 'suit':.., 'playedBy': ..}], ...}
                      # WAIT: game.py serialization: 'cards': [{**c, 'card': c['card'].to_dict()}...] or just list of cards?
                      # game.py line 155 in get_game_state uses {**c, 'card': ...} format for roundHistory/currentRoundTricks.
                      # BUT last_trick (line 145) is assigned self.last_trick.
                      # In resolve_trick (trick_manager.py line 100): 
                      # 'cards': [tc['card'].to_dict() for tc in self.game.table_cards]
                      # 'metadata': ...
                      # But wait, where is 'playedBy' in last_trick['cards']?
                      # trick_manager.py line 100 doesn't seem to zip playedBy into the cards list!
                      # It stores `winner` pos.
                      
                      # Ah, trick_manager.py line 113 `trick_data` stores `cards` and `playedBy` as parallel lists for history.
                      # But `self.game.last_trick` (line 100) might only store cards?
                      # Let's check `trick_manager.py` again.
                      
                      # Re-reading trick_manager.py from context:
                      # 100: self.game.last_trick = {
                      # 101:     'cards': [tc['card'].to_dict() for tc in self.game.table_cards], 
                      # 102:     'winner': winner_pos,
                      # 103:     'metadata': ...
                      # 104: }
                      # It does NOT store playedBy per card! This is a flaw for Sherlock checking last trick if he needs position.
                      # However, we can reconstruct order. Trick starts at `(winner_index_of_prev_trick)`.
                      # But easier: Use `game_state['roundHistory'][-1]` (the last completed trick) which HAS playedBy data.
                      pass

                 # C. Robust Last Trick Check using Round History
                 # C. Deep History Scan (Sherlock's Archives)
                 # We must scan ALL past tricks in the current round, because the crime might be old.
                 current_tricks = game_state.get('currentRoundTricks', [])
                 if current_tricks:
                       # Iterate backwards through all tricks
                       round_num = len(game_state.get('roundHistory', []))
                       
                       for rev_idx, trick in enumerate(reversed(current_tricks)):
                            # Calculate Absolute Trick Index for stability
                            abs_trick_idx = len(current_tricks) - 1 - rev_idx
                            
                            involved_players = trick.get('playedBy', [])
                            cards_list = trick.get('cards', [])
                            
                            for i, c_data in enumerate(cards_list):
                                 # Robust Parsing
                                 c_inner = c_data if 'rank' in c_data else c_data.get('card', {})
                                 
                                 # Determine Player Position
                                 p_pos = c_data.get('playedBy')
                                 if not p_pos and i < len(involved_players):
                                      p_pos = involved_players[i]
                                      
                                 if p_pos and c_inner:
                                      source_label = f"Trick {abs_trick_idx + 1}"
                                      action = self._check_crime_logic(ctx, c_inner, p_pos, source_label)
                                      if action: 
                                           # ANTI-SPAM CHECK
                                           crime_id = (round_num, abs_trick_idx, i)
                                           if crime_id in self.reported_crimes:
                                                # logger.info(f"[SHERLOCK] Skipping known crime: {crime_id}")
                                                continue
                                                
                                           logger.info(f"[SHERLOCK] Crime found in {source_label} by {p_pos} ({c_inner}). Reporting...")
                                           self.reported_crimes.add(crime_id)
                                           self.pending_qayd_trigger = True  # Lock to prevent other bots
                                           return {"action": action}
                                     
                 # D. Extra Debugging: Log if we are suspicious but memory says OK
                 # (This block only runs if no action returned yet)
                 # logger.debug(f"[SHERLOCK] Scan complete. No contradictions found in Table or Last Trick.")

             # 1.2 Qayd Claim (Sherlock Logic)
             qayd_state = game_state.get('qaydState')
             if qayd_state and qayd_state.get('active'):
                 # Reset the pending trigger - Qayd is now active, lock can be released
                 self.pending_qayd_trigger = False
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
                      # DON'T auto-confirm - always investigate first to ensure proper penalty assignment
                      # The investigate step sends QAYD_ACCUSATION with crime details
                      logger.info(f"[SHERLOCK] I am the reporter ({reporter_pos}). Investigation starting...")
                      # 1. Brief Pause (simulating reaction time)
                      # time.sleep(1) # REMOVED per user request (Too slow)
                      
                      # 2. Find the Crime (Using Deep Scan Logic, NOT Metadata)
                      # We must re-scan using the Sherlock Logic because 'is_illegal' metadata is hidden from clients.
                      
                      crime_card = None
                      proof_card = None
                      violation_type = 'REVOKE'
                      
                      # FIRST: Check Current Table (where trigger found it!)
                      table_cards = game_state.get('tableCards', [])
                      if table_cards:
                           for tc in table_cards:
                                action = self._check_crime_logic(ctx, tc['card'], tc['playedBy'], "Current Table")
                                if action:
                                     crime_card = tc['card']
                                     # Proof is the lead card of this trick
                                     if table_cards:
                                          proof_card = table_cards[0]['card']
                                     logger.info(f"[SHERLOCK] Investigation confirmed crime on table by {tc['playedBy']}")
                                     break
                      
                      # SECOND: Deep History Scan (Re-used from Trigger)
                      if not crime_card:
                          current_tricks = game_state.get('currentRoundTricks', [])
                          if current_tricks:
                               for rev_idx, trick in enumerate(reversed(current_tricks)):
                                abs_trick_idx = len(current_tricks) - 1 - rev_idx
                                involved_players = trick.get('playedBy', [])
                                cards_list = trick.get('cards', [])
                                
                                for i, c_data in enumerate(cards_list):
                                     c_inner = c_data if 'rank' in c_data else c_data.get('card', {})
                                     p_pos = c_data.get('playedBy')
                                     if not p_pos and i < len(involved_players): p_pos = involved_players[i]
                                     
                                     if p_pos and c_inner:
                                          # Re-check Logic
                                          action = self._check_crime_logic(ctx, c_inner, p_pos, f"Trick {abs_trick_idx}")
                                          if action:
                                               # Found it! Reconstruct details
                                               from game_engine.models.card import Card
                                               crime_card = c_inner # Dict representation
                                               
                                               # Proof is usually the lead of that trick
                                               if cards_list:
                                                    proof_card = cards_list[0] if 'rank' in cards_list[0] else cards_list[0].get('card', {})
                                               
                                               logger.info(f"[SHERLOCK] Investigation confirmed crime in Trick {abs_trick_idx} by {p_pos}")
                                               break
                                if crime_card: break


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

             # Legacy/Backup Check - Now uses proof-based detection via Memory
             # Use ctx.memory (populated from current game state) not self.memory
             # SILENCED FOR UX:
             # if qayd_claim := self.referee.check_qayd(ctx, game_state, memory=ctx.memory):
             #     return qayd_claim
             pass

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
                  
                  # is_losing_badly = (their_score - my_score) > 20 # Low threshold for testing
                  is_losing_badly = False # DISABLED per user request (Debugging confusion)
                  
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
