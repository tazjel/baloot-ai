import logging
import enum
from typing import Dict, Any, Optional

from game_engine.models.constants import GamePhase
from game_engine.models.card import Card
from server.logging_utils import logger, log_event

class ChallengePhase:
    """
    Handles all logic related to the 'CHALLENGE' (Qayd/Forensic) phase.
    OWNER of the Qayd Investigation State.
    """
    
    def __init__(self, game_instance):
        self.game = game_instance
        self.state = {
            'active': False,
            'reporter': None,
            'reason': None,
            'status': 'NONE', # NONE, REVIEW, RESOLVED
            'target_play': None,
            'target_source': None,
            'verdict_message': None,
            'crime_card_index': -1,
            'proof_card_index': -1,
            'penalty_points': 0,
            'loser_team': None,
            'qayd_type': None,
            'crime_signature': None
        }
        self.ignored_crimes = set() # Track cancelled accusations (trick_idx, card_idx)
        self.previous_phase = None

    def reset(self):
        """Reset state for new round"""
        self.state = {
            'active': False,
            'reporter': None,
            'reason': None,
            'status': 'NONE',
            'target_play': None,
            'target_source': None,
            'verdict_message': None,
            'crime_card_index': -1,
            'proof_card_index': -1,
            'penalty_points': 0,
            'loser_team': None,
            'qayd_type': None,
            'crime_signature': None
        }
        self.ignored_crimes = set()
        self.previous_phase = None

    def trigger_investigation(self, player_index):
        """
        Transitions the game into Qayd investigation mode.
        """
        if self.game.is_locked:
            logger.warning(f"Qayd trigger rejected - game already locked")
            return {'success': False, 'error': 'Game Locked'}
        
        logger.info(f"[QAYD] Player {player_index} triggering Qayd investigation (via ChallengePhase)")
        
        # Call INTERNAL propose logic
        result = self.propose_qayd(player_index)
        
        if result.get('success'):
            # 1. Lock Game
            self.game.is_locked = True
            
            # Store previous phase explicitly
            if self.game.phase != GamePhase.CHALLENGE.value:
                self.previous_phase = self.game.phase
                
            # 2. Change Phase
            self.game.phase = GamePhase.CHALLENGE.value
            
            logger.info(f"[QAYD] Game LOCKED & Phase set to CHALLENGE")
            
            # 4. AUTO-CONFIRM FOR BOTS
            player = self.game.players[player_index]
            if player.is_bot:
                 logger.info(f"[QAYD] Bot {player.name} ({player_index}) triggered Qayd. Auto-confirming verdict.")
                 return self.resolve_verdict()
                 
            return result
        else:
            logger.error(f"[QAYD] propose_qayd FAILED: {result}")
            return result

    def propose_qayd(self, reporter_index, crime_card=None, proof_card=None, qayd_type='REVOKE', crime_trick_idx=None, proof_trick_idx=None):
        """
        Logic moved from TrickManager: detailed investigation of valid Qayd.
        """
        try:
             reporter = self.game.players[reporter_index]
             
             # Reset internal state for new proposal
             self.state = {
                 'active': True,
                 'reporter': reporter.position,
                 'status': 'REVIEW',
                 'verdict_message': None,
                 'crime_card_index': -1,
                 'proof_card_index': -1,
                 'penalty_points': 0,
                 'loser_team': None,
                 'reason': None,
                 'target_play': None, 
                 'target_source': 'table_cards',
                 'qayd_type': qayd_type,
                 'crime_card': crime_card,
                 'proof_card': proof_card,
                 'crime_trick_idx': crime_trick_idx,
                 'proof_trick_idx': proof_trick_idx,
                 'crime_signature': None
             }
             
             crime_card_found = False
             
             # === EXPLICIT ACCUSATION MODE (Kammelna-style) ===
             if crime_card and proof_card:
                 logger.info(f"[QAYD] Explicit accusation: crime={crime_card}, proof={proof_card}, type={qayd_type}")
                 
                 crime_validated = False
                 for trick_idx, trick in enumerate(self.game.round_history):
                     for card_idx, card_dict in enumerate(trick['cards']):
                         if card_dict['suit'] == crime_card['suit'] and card_dict['rank'] == crime_card['rank']:
                             player_pos = trick['playedBy'][card_idx]
                             led_card = trick['cards'][0]
                             led_suit = led_card['suit']
                             
                             if card_dict['suit'] != led_suit:
                                 crime_validated = True
                                 self.state['crime_card_index'] = card_idx
                                 self.state['crime_trick_idx'] = trick_idx
                                 self.state['target_play'] = {
                                     'card': card_dict,
                                     'playedBy': player_pos,
                                     'metadata': trick.get('metadata', [{}])[card_idx] if trick.get('metadata') else {}
                                 }
                                 self.state['target_source'] = 'round_history'
                                 
                                 proof_validated = False
                                 for proof_t_idx, proof_trick in enumerate(self.game.round_history[trick_idx+1:], start=trick_idx+1):
                                     for proof_c_idx, proof_c_dict in enumerate(proof_trick['cards']):
                                         proof_player_pos = proof_trick['playedBy'][proof_c_idx]
                                         if proof_player_pos == player_pos and proof_c_dict['suit'] == led_suit:
                                             proof_validated = True
                                             self.state['proof_card_index'] = proof_c_idx
                                             self.state['proof_trick_idx'] = proof_t_idx
                                             break
                                     if proof_validated: break
                                 
                                 if proof_validated:
                                     crime_card_found = True
                                     logger.info(f"[QAYD] Explicit accusation VALIDATED: {player_pos} revoked on {led_suit}")
                                 else:
                                     logger.warning(f"[QAYD] Proof card not found in history for {player_pos}")
                             break
                     if crime_validated: break
                 
                 if not crime_card_found:
                     logger.warning(f"[QAYD] Could not validate explicit accusation")
                 else:
                     logger.info(f"[QAYD] Explicit accusation VALIDATED in HISTORY")
                     
             # === EXPLICIT MODE CHECK ON ACTIVE TABLE (If not found in history) ===
             if crime_card and proof_card and not crime_card_found:
                 # Check active table for the crime card
                 for i, play in enumerate(self.game.table_cards):
                      card_dict = play['card'].to_dict() if hasattr(play['card'], 'to_dict') else play['card']
                      if card_dict['suit'] == crime_card['suit'] and card_dict['rank'] == crime_card['rank']:
                           player_pos = play['playedBy']
                           if not self.game.table_cards: break
                           led_card = self.game.table_cards[0]['card']
                           led_card_dict = led_card.to_dict() if hasattr(led_card, 'to_dict') else led_card
                           led_suit = led_card_dict['suit']
                           
                           if card_dict['suit'] != led_suit:
                                crime_card_found = True
                                self.state['crime_card_index'] = i
                                self.state['target_play'] = {
                                   'card': card_dict,
                                   'playedBy': player_pos,
                                   'metadata': play.get('metadata', {})
                                }
                                self.state['target_source'] = 'table_cards'
                                logger.info(f"[QAYD] Explicit accusation VALIDATED on TABLE")
                                
                                # We assume Sherlock logic holds for proof
                           break
             
             # === AUTO-DETECT MODE (Legacy/Bot: metadata search) ===
             if not crime_card_found:
                 crime_card_idx_in_trick = -1
                 # Check Table Cards
                 for i, play in enumerate(reversed(self.game.table_cards)):
                      if (play.get('metadata') or {}).get('is_illegal'):
                           crime_card_found = True
                           crime_card_idx_in_trick = len(self.game.table_cards) - 1 - i
                           self.state['crime_card_index'] = crime_card_idx_in_trick
                           
                           # Convert play to serializable dict
                           card_data = play['card'].to_dict() if hasattr(play['card'], 'to_dict') else play['card']
                           
                           self.state['target_play'] = {
                               'card': card_data,
                               'playedBy': play.get('playedBy'),
                               'metadata': play.get('metadata')
                           }
                           self.state['target_source'] = 'table_cards'
                           break
             
             # Check Last Trick (Priority 2)
             if not crime_card_found and self.game.last_trick and self.game.last_trick.get('metadata'):
                   for i, meta in enumerate(self.game.last_trick['metadata']):
                        if meta and meta.get('is_illegal'):
                             crime_card_found = True
                             self.state['crime_card_index'] = i 
                             self.state['target_source'] = 'last_trick'
                             
                             if self.game.round_history:
                                  last_trick_hist = self.game.round_history[-1]
                                  # Fix serialization if needed
                                  card_obj = last_trick_hist['cards'][i]
                                  # Ensure it's a dict
                                  if hasattr(card_obj, 'to_dict'): card_obj = card_obj.to_dict()
                                  
                                  self.state['target_play'] = {
                                      'card': card_obj,
                                      'playedBy': last_trick_hist['playedBy'][i],
                                      'metadata': last_trick_hist['metadata'][i]
                                  }
                             break
                             
             # CHECK IGNORED CRIMES
             current_trick_idx = len(self.game.round_history)
             if self.state.get('target_source') == 'last_trick':
                  current_trick_idx -= 1
                   
             crime_sig = (current_trick_idx, self.state.get('crime_card_index'))
              
             if crime_sig in self.ignored_crimes:
                  logger.info(f"[QAYD] Ignoring previously cancelled crime: {crime_sig}")
                  return {"success": False, "error": "Crime ignored (Double Jeopardy)"}
                   
             self.state['crime_signature'] = crime_sig

             # --- VERDICT CALCULATION ---
             violation = None
             if crime_card_found:
                  if 'target_play' in self.state and self.state['target_play']:
                       violation = self.state['target_play']['metadata'].get('illegal_reason', 'Rule Violation')
             
             game_mode = self.game.game_mode
             
             if crime_card_found:
                  offender_pos = self.state['target_play']['playedBy']
                  offender = next(p for p in self.game.players if p.position == offender_pos)
                  self.state['loser_team'] = offender.team
                  self.state['reason'] = f"Qayd Valid: {violation}"
                  self.state['verdict_message'] = f"QATA: {offender.position} played illegal move ({violation})"
             else:
                  self.state['loser_team'] = reporter.team
                  self.state['reason'] = f"Qayd Failed: Move was legal."
                  self.state['verdict_message'] = f"False Accusation by {reporter.position}"
                  
             # Points Calculation
             raw_mode = str(game_mode).upper()
             is_sun = 'SUN' in raw_mode
             if not is_sun and self.game.bid and str(self.game.bid.get('type')).upper() == 'SUN':
                 is_sun = True
             
             base_points = 26 if is_sun else 16
             if self.game.doubling_level >= 2: base_points *= self.game.doubling_level
             
             project_points = 0
             if hasattr(self.game, 'declarations') and self.game.declarations:
                  for pos, projs in self.game.declarations.items():
                       for proj in projs:
                            project_points += proj.get('score', 0)
             
             self.state['penalty_points'] = base_points + project_points
             
             # CLEAR 'is_illegal' FLAG (Prevent Re-trigger)
             self._clear_illegal_flag()
             
             self.game.timer_paused = True
             return {"success": True, "qayd_state": self.state}
             
        except Exception as e:
             logger.error(f"Error in propose_qayd: {e}")
             import traceback
             logger.error(traceback.format_exc())
             return {"success": False, "error": str(e)}

    def _clear_illegal_flag(self):
         """Helper to wipe illegal flag from source"""
         source = self.state.get('target_source')
         crime_idx = self.state.get('crime_card_index', -1)
         
         if source == 'table_cards' and crime_idx >= 0 and crime_idx < len(self.game.table_cards):
              if self.game.table_cards[crime_idx].get('metadata'):
                   self.game.table_cards[crime_idx]['metadata']['is_illegal'] = False
                   logger.info(f"[QAYD] Cleared is_illegal flag from table_cards[{crime_idx}]")
         elif source == 'last_trick' and self.game.round_history and crime_idx >= 0:
              last_trick = self.game.round_history[-1]
              if last_trick.get('metadata') and crime_idx < len(last_trick['metadata']):
                   if last_trick['metadata'][crime_idx]:
                        last_trick['metadata'][crime_idx]['is_illegal'] = False
                        logger.info(f"[QAYD] Cleared is_illegal flag from last_trick[{crime_idx}]")

    def resolve_verdict(self):
        """
        Handles the confirmation/resolution of a Qayd.
        Applies penalty and unlocks game.
        """
        if not self.state.get('active'):
            return {'success': False, 'error': "No active Qayd"}
            
        loser_team = self.state['loser_team']
        points = self.state['penalty_points']
        points = self.state['penalty_points']
        reason = self.state['reason']
        
        # Prevent Double Jeopardy: Ignore this crime signature in future
        if self.state.get('crime_signature'):
             self.ignored_crimes.add(self.state['crime_signature'])

        
        # Mark as resolved
        self.state['status'] = 'RESOLVED'
        self.state['active'] = False
        
        # Apply Khasara via TrickManager (Scoring Logic)
        self.game.trick_manager.apply_khasara(loser_team, reason, points_override=points)
        
        # Unlock
        self.game.is_locked = False
        logger.info(f"[QAYD] Game UNLOCKED after resolution.")
        
        result = {'success': True}

        # Trigger auto-restart if game phase is FINISHED
        if self.game.phase == GamePhase.FINISHED.value:
            logger.info(f"[QAYD] Phase is FINISHED after confirmation. Signaling Auto-Restart.")
            result['trigger_next_round'] = True
            
        return result

    def cancel_investigation(self):
        """
        Handles the cancellation of a Qayd investigation (e.g. by User or Timer).
        Ensures the game is UNLOCKED and resumes.
        """
        logger.info(f"[QAYD] cancel_investigation via ChallengePhase...")
        
        # 1. Update State
        if self.state.get('crime_signature'):
             self.ignored_crimes.add(self.state['crime_signature'])
             
        self.state['active'] = False
        self.state['status'] = 'CANCELLED'
             
        # 2. Unlock Game
        self.game.is_locked = False
        logger.info(f"[QAYD] Game UNLOCKED after Cancel.")

        # 3. Resume Phase
        if self.game.phase == GamePhase.CHALLENGE.value:
            if self.previous_phase:
                self.game.phase = self.previous_phase
                logger.info(f"[QAYD] Phase reverted to stored prior phase: {self.previous_phase}")
            else:
                self.game.phase = GamePhase.PLAYING.value
                logger.info("[QAYD] Phase reverted to PLAYING (Default).")
            
        # 4. Resume Timer
        self.game.timer_paused = False
        
        result = {'success': True}

        # 5. Check for Auto-Restart
        if self.game.phase == GamePhase.FINISHED.value:
             logger.info(f"[QAYD] Phase is FINISHED. Signaling Auto-Restart.")
             result['trigger_next_round'] = True
             
        return result
