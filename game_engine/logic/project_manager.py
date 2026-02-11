from typing import Dict, List, Optional, Any
from game_engine.logic.rules.projects import check_project_eligibility, compare_projects
from game_engine.logic.rules.sawa import check_sawa_eligibility
from game_engine.core.state import AkkaState
from server.logging_utils import logger

class ProjectManager:
    def __init__(self, game):
        self.game = game

    @property
    def akka_state(self):
        """Single source of truth for Akka state — the Pydantic model on GameState."""
        return self.game.state.akkaState

    # ─── Serialization Helpers ────────────────────────────────────────

    @staticmethod
    def _sanitize_project(proj: dict) -> dict:
        """Ensure all Card objects in a project dict are converted to plain dicts
        so they survive Pydantic model_dump(mode='json') without errors."""
        out = dict(proj)
        if 'cards' in out:
            out['cards'] = [c.to_dict() if hasattr(c, 'to_dict') else c for c in out['cards']]
        return out

    def handle_declare_project(self, player_index, type):
         try:
             player = self.game.players[player_index]
             # Validation: Must be first trick
             if len(self.game.round_history) > 0: 
                  pass # Actually rule says only during trick 1.
             else:
                  if player_index != self.game.current_turn:
                       return {"error": "Wait for your turn"}

             # Validate using new scan
             hand_projs = check_project_eligibility(player.hand, self.game.game_mode)
             
             # Check if requested type matches ANY found project
             matches = [p for p in hand_projs if p['type'] == type]
             
             if matches:
                  if player.position not in self.game.trick_1_declarations:
                       self.game.trick_1_declarations[player.position] = []
                  
                  # Check if we already have this specific project declared
                  current_decls = self.game.trick_1_declarations[player.position]
                  
                  # Create signature helper
                  def get_proj_sig(p):
                      # Create unique signature: TYPE-RANK-SUIT(if any)-CARDS
                      # Sorting cards ensures order independence
                      cards_sig = "-".join(sorted([f"{c.rank}{c.suit}" for c in p.get('cards', [])]))
                      return f"{p['type']}|{p['rank']}|{p.get('suit', 'ANY')}|{cards_sig}"

                  # Filter unique matches only
                  for match in matches:
                      match_sig = get_proj_sig(match)
                      
                      is_duplicate = any(
                          get_proj_sig(d) == match_sig
                          for d in current_decls
                      )
                      
                      if not is_duplicate:
                          safe = self._sanitize_project(match)
                          self.game.trick_1_declarations[player.position].append(safe)
                          
                          # updates self.declarations too for UI
                          if player.position not in self.game.declarations:
                               self.game.declarations[player.position] = []
                          self.game.declarations[player.position].append(safe)
                  
                  return {"success": True}
                  
             return {"error": "Invalid Project"}
         except Exception as e:
             logger.error(f"Error in handle_declare_project: {e}")
             return {"error": f"Internal Error: {str(e)}"}

    def resolve_declarations(self):
        """
        Called at end of Trick 1 / Start of Trick 2.
        Compares team projects using hierarchy and winner-takes-all.
        """
        # 1. Flatten into list with metadata
        all_projs = []
        for pos, projs in self.game.trick_1_declarations.items():
            p = next(p for p in self.game.players if p.position == pos)
            for proj in projs:
                 all_projs.append({'proj': proj, 'p_idx': p.index, 'team': p.team, 'pos': pos})
                 
        if not all_projs:
             self.game.declarations = {}
             return
             
        # 2. Find Best Project for US and THEM
        us_cands = [x for x in all_projs if x['team'] == 'us']
        them_cands = [x for x in all_projs if x['team'] == 'them']
        
        def sort_wrapper(items):
            from functools import cmp_to_key
            def cmp_func(a, b):
                return compare_projects(a['proj'], b['proj'], self.game.game_mode, self.game.dealer_index, a['p_idx'], b['p_idx'])
            return sorted(items, key=cmp_to_key(cmp_func), reverse=True)
            
        best_us = sort_wrapper(us_cands)[0] if us_cands else None
        best_them = sort_wrapper(them_cands)[0] if them_cands else None
        
        # 3. Compare Teams
        winner_team = 'NONE'
        if best_us and best_them:
             res = compare_projects(best_us['proj'], best_them['proj'], self.game.game_mode, self.game.dealer_index, best_us['p_idx'], best_them['p_idx'])
             if res > 0: winner_team = 'us'
             elif res < 0: winner_team = 'them'
             else: winner_team = 'BOTH' # Shouldn't happen given Tie Breaker logic (Position)
        elif best_us:
             winner_team = 'us'
        elif best_them:
             winner_team = 'them'
             
        # 4. Filter Declarations (Winner Takes All)
        # Move valid ones to self.game.declarations
        self.game.declarations = {}
        
        for item in all_projs:
             is_valid = False
             # Team Win logic: If my team won the comparison, ALL my team's projects are valid.
             if winner_team == 'BOTH': is_valid = True
             elif item['team'] == winner_team: is_valid = True
             
             if is_valid:
                  pos = item['pos']
                  if pos not in self.game.declarations: self.game.declarations[pos] = []
                  self.game.declarations[pos].append(self._sanitize_project(item['proj']))
        
        # Trigger Reveal Animation
        if self.game.declarations:
             self.game.is_project_revealing = True 

    def init_akka(self):
         self.game.state.akkaState = AkkaState()

    # ═══════════════════════════════════════════════════════════════════════
    #  AKKA LOGIC — "Boss Card" Declaration
    #  Akka = Declaring you hold the highest remaining non-trump card
    #         in a given suit during HOKUM mode.
    #
    #  Rules (Standard Baloot):
    #    1. Mode: HOKUM only (no concept of Akka in SUN).
    #    2. Suit: Must be non-trump.
    #    3. Rank: Must NOT be Ace (Ace is self-evident/obvious boss).
    #    4. Condition: Card must be the HIGHEST REMAINING card of that suit
    #       (all higher-ranked cards have been played in previous tricks).
    #    5. Phase: Must be PLAYING phase.
    #    6. Turn: Must be the player's turn.
    #
    #  NOTE: Some dialects call this "Sira" for sequences. Here "Akka"
    #  strictly means single-card boss declaration, not a sequence project.
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _card_key(card) -> str:
        """
        Generates a consistent card signature string from any card format.
        Handles: Card objects, dicts, nested {card: ...} wrappers.
        Returns: e.g. "A♠", "10♥"
        """
        if isinstance(card, dict):
            # Nested wrapper: {card: Card|dict, playedBy: ...}
            if 'card' in card:
                return ProjectManager._card_key(card['card'])
            return f"{card.get('rank', '')}{card.get('suit', '')}"
        # Card object
        if hasattr(card, 'rank') and hasattr(card, 'suit'):
            return f"{card.rank}{card.suit}"
        return str(card)

    def _build_played_cards_set(self) -> set:
        """
        Builds a set of all cards played this round (completed tricks + current table).
        Uses _card_key for consistent format regardless of card representation.
        """
        played = set()

        # 1. Completed tricks from round_history
        for trick in self.game.round_history:
            for card_entry in trick.get('cards', []):
                key = self._card_key(card_entry)
                if key:
                    played.add(key)

        # 2. Cards currently on the table
        for tc in self.game.table_cards:
            key = self._card_key(tc.get('card', tc))
            if key:
                played.add(key)

        return played

    def check_akka_eligibility(self, player_index):
        """
        Returns a list of suits where the player holds the Boss card.
        Delegates to pure logic in rules/akka.py.
        """
        from game_engine.logic.rules.akka import check_akka_eligibility
        
        player = self.game.players[player_index]
        if not player.hand:
            return []
            
        return check_akka_eligibility(
            hand=player.hand,
            played_cards=self._build_played_cards_set(),
            trump_suit=self.game.trump_suit,
            game_mode=self.game.game_mode,
            phase=self.game.phase
        )

    def handle_akka(self, player_index):
        """
        Process an Akka declaration from a player.
        Validates eligibility, updates state, and returns result.
        """
        from game_engine.models.constants import GamePhase
        import time

        try:
            player = self.game.players[player_index]

            # --- Pre-validation guards (race condition defense) ---

            # Must be PLAYING phase
            if self.game.phase != GamePhase.PLAYING.value:
                return {
                    "success": False,
                    "error": f"Cannot declare Akka outside PLAYING phase (current: {self.game.phase})"
                }

            # Must be this player's turn
            if player_index != self.game.current_turn:
                return {
                    "success": False,
                    "error": "Not your turn to declare Akka"
                }

            # Must be HOKUM
            if self.game.game_mode != 'HOKUM':
                return {
                    "success": False,
                    "error": "Akka is only available in HOKUM mode"
                }

            # Validation: Already active
            if self.akka_state.active:
                 # Log this to catch spam
                 logger.warning(f"AKKA REJECTED: Already active (Claimer: {self.akka_state.claimer}). Request by: {player.position}")
                 return {'success': False, 'error': 'Already Active'}

            eligible = self.check_akka_eligibility(player_index)

            if not eligible:
                # INVALID AKKA — Referee Intervention
                logger.warning(f"INVALID AKKA CLAIM by {player.position}")
                self.game.increment_blunder(player_index)

                return {
                    "success": False,
                    "error": "REFEREE_FLAG",
                    "message": "Invalid Akka! (Higher cards exist)",
                    "intervention": {
                        "type": "INVALID_AKKA",
                        "playerIndex": player_index,
                        "message": "Cannot declare Akka! Higher cards are still in play."
                    }
                }

            # Valid Akka! — Write directly to the Pydantic model (single source of truth)
            self.game.state.akkaState = AkkaState(
                active=True,
                claimer=player.position,
                claimerIndex=player_index,
                suits=eligible,
                timestamp=time.time(),
            )

            logger.info(f"AKKA DECLARED by {player.position} for suits: {eligible}")
            return {"success": True, "akka_state": self.akka_state.model_dump()}

        except Exception as e:
            logger.error(f"Error in handle_akka: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": f"Internal error: {str(e)}"}

    def calculate_project_points(self) -> Dict[str, int]:
        """
        Calculates total points for active declarations for each team.
        """
        points = {'us': 0, 'them': 0}
        
        for pos, projects in self.game.declarations.items():
            # Find team
            p = next((p for p in self.game.players if p.position == pos), None)
            if not p: continue
            
            team = p.team # 'us' or 'them'
            
            for proj in projects:
                points[team] += proj.get('score', 0)
                
                
        return points 

    # ═══════════════════════════════════════════════════════════════════════
    #  SAWA LOGIC — "Grand Slam" Declaration
    #  Sawa = Declaring you guarantee winning ALL remaining tricks.
    # ═══════════════════════════════════════════════════════════════════════

    def check_sawa_eligibility(self, player_index):
        """
        Wrapper checking Sawa eligibility for a player.
        """
        player = self.game.players[player_index]
        if not player.hand: return False
        
        return check_sawa_eligibility(
            hand=player.hand,
            played_cards=self._build_played_cards_set(),
            trump_suit=self.game.trump_suit,
            game_mode=self.game.game_mode,
            phase=self.game.phase
        )

    def handle_sawa(self, player_index):
        """
        Process a Sawa declaration.
        """
        from game_engine.models.constants import GamePhase
        
        try:
             player = self.game.players[player_index]
             
             # Validation: Must be PLAYING phase & Player's Turn
             if self.game.phase != GamePhase.PLAYING.value or player_index != self.game.current_turn:
                  return {"success": False, "error": "Invalid Timing"}
                  
             eligible = self.check_sawa_eligibility(player_index)
             
             if not eligible:
                  # PENALTY / REFEREE
                  logger.warning(f"INVALID SAWA CLAIM by {player.position}")
                  self.game.increment_blunder(player_index)
                  return {
                      "success": False, 
                      "error": "REFEREE_FLAG",
                      "intervention": {
                          "type": "INVALID_SAWA",
                          "playerIndex": player_index,
                          "message": "Sawa Rejected! You do not guarantee all tricks."
                      }
                  }
             
             # Valid Sawa
             logger.info(f"SAWA DECLARED VALID by {player.position}")
             
             self.game.sawa_declaration = {
                 'player_index': player_index,
                 'active': True
             }
             
             return {"success": True, "sawa_active": True}
             
        except Exception as e:
             logger.error(f"Error in handle_sawa: {e}")
             return {"success": False, "error": str(e)}
