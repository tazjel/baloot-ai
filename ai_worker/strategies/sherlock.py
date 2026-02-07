import logging
import time
from typing import Dict, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)

class SherlockStrategy:
    """
    The Detective Module.
    Responsible for:
    1. Scanning the table for illegal moves (Live Detection).
    2. Scanning history for past crimes (Cold Case).
    3. Filing Accusations (Qayd).
    """
    def __init__(self, agent):
        self.agent = agent # Back reference for memory/state if needed
        self.reported_crimes: Set[Tuple] = set()
        self.pending_qayd_trigger = False

    def scan_for_crimes(self, ctx, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Main entry point. Returns an Action dict if a crime is found and should be acted upon.
        """
        # 1. Check Global Locks
        qayd_state = game_state.get('qaydState', {})
        if qayd_state and qayd_state.get('active'):
            return self._handle_active_qayd(ctx, game_state, qayd_state)
            
        if self.pending_qayd_trigger:
             # We already locked it, waiting for next tick to confirm? 
             # Or we are just stuck. Verify lock ownership?
             # For now, if we think we are triggering, return None (wait).
             return None

        # 2. Check Triggers (The "Second Card" Rule)
        # Only check if valid phase and not blocked
        if ctx.phase == 'PLAYING':
            return self._scan_table_and_history(ctx, game_state)
            
        return None

    def _scan_table_and_history(self, ctx, game_state) -> Optional[Dict[str, Any]]:
        """
        Scans current table and recent history for contradictions.
        """
        from game_engine.models.card import Card
        
        # A. Check Current Table (Live)
        table_cards = game_state.get('tableCards', [])
        round_num = len(game_state.get('roundHistory', []))
        current_trick_idx = len(game_state.get('currentRoundTricks', [])) or 0
        
        for card_idx, tc in enumerate(table_cards):
            # Check Server Flag FIRST (Alignment with QaydEngine)
            meta = tc.get('metadata') or {}
            if meta.get('is_illegal'):
                 crime_id = (round_num, current_trick_idx, card_idx, tc['card'].get('suit'), tc['card'].get('rank'))
                 if crime_id in self.reported_crimes:
                     continue
                 
                 self.reported_crimes.add(crime_id)
                 self.pending_qayd_trigger = True
                 return {"action": "QAYD_TRIGGER"}

            # Optional: Keep Logic Check for logging/debugging but DO NOT Trigger if server didn't flag it
            # action = self._check_crime_logic(ctx, tc['card'], tc['playedBy'], "Current Trick")

        # B. Check History (Deep Scan)
        current_tricks = game_state.get('currentRoundTricks', []) # This might need to be passed in differently if not in standard state
        # In agent.py it was accessed via game_state.get('currentRoundTricks') which might be a computed view or separate key
        
        if current_tricks:
             for rev_idx, trick in enumerate(reversed(current_tricks)):
                  abs_trick_idx = len(current_tricks) - 1 - rev_idx
                  involved_players = trick.get('playedBy', [])
                  cards_list = trick.get('cards', [])
                  metas = trick.get('metadata') or []
                  
                  for i, c_data in enumerate(cards_list):
                        # Robust Parsing
                        c_inner = c_data if 'rank' in c_data else c_data.get('card', {})
                        p_pos = c_data.get('playedBy')
                        
                        # Fallback for old history format
                        if not p_pos and i < len(involved_players):
                            p_pos = involved_players[i]
                        
                        # Check Server Flag
                        is_illegal = False
                        if i < len(metas) and metas[i]:
                             if metas[i].get('is_illegal'):
                                  is_illegal = True

                        if is_illegal:
                             crime_id = (round_num, abs_trick_idx, i)
                             if crime_id in self.reported_crimes:
                                  continue
                             
                             self.reported_crimes.add(crime_id)
                             self.pending_qayd_trigger = True
                             logger.info(f"[SHERLOCK] Found flagged crime in history: {crime_id}")
                             return {"action": "QAYD_TRIGGER"}
        return None

    def _check_crime_logic(self, ctx, card_dict, played_by_pos, source="Table"):
        """
        Core logic: Does this card contradict known info?
        """
        from game_engine.models.card import Card
        
        # 1. Omerta (Ignore Team)
        offender_team = ctx.players_team_map.get(played_by_pos)
        if offender_team == ctx.team:
             return None
             
        # 2. Check Memory
        c_obj = Card(card_dict['suit'], card_dict['rank'])
        contradiction = ctx.memory.check_contradiction(played_by_pos, c_obj)
        
        if contradiction:
             logger.info(f"[SHERLOCK] 🕵️‍♂️ {ctx.position} Caught {played_by_pos}! {contradiction} (Source: {source})")
             return "QAYD_TRIGGER"
             
        return None

    def _handle_active_qayd(self, ctx, game_state, qayd_state) -> Dict[str, Any]:
        """
        Handle ongoing Qayd (Investigation/Accusation).
        """
        self.pending_qayd_trigger = False # Reset lock
        
        reporter_pos = qayd_state.get('reporter')
        
        # Am I the reporter?
        is_me = False
        if reporter_pos == ctx.position: is_me = True
        elif str(reporter_pos) == str(ctx.player_index): is_me = True
        
        if is_me:
             # Investigate and Accuse
             logger.info(f"[SHERLOCK] I am the reporter ({reporter_pos}). Investigating...")
             
             # Re-run scan to get the exact crime detail for the specific accusation packet
             # (Simplified reuse of logic possible, or just duplicate the deep scan here)
             # For Phase 1 refactor, we can just trigger a general accusation or repeat the scan.
             # Ideally we cached the crime that triggered it, but state is stateless between ticks.
             
             # Repeat Scan to find the Card
             # Logic same as _scan_table_and_history but returning Acusation Object
             
             # ... (Investigation Logic Omitted for brevity, will copy from agent.py during replace)
             # Returning placeholder for file creation
             # Repeat Scan to find the Card
             # Logic is to find the distinct crime card again to attach to accusation
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
                            if table_cards:
                                 proof_card = table_cards[0]['card']
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
                                          crime_card = c_inner 
                                          # Proof is usually the lead of that trick
                                          if cards_list:
                                               proof_card = cards_list[0] if 'rank' in cards_list[0] else cards_list[0].get('card', {})
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
                return {"action": "QAYD_CANCEL"}
             
        else:
             return {"action": "WAIT", "reason": "Qayd Investigation"}

