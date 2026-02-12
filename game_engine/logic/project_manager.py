"""
game_engine/logic/project_manager.py — Project Declaration Manager
====================================================================

Manages مشاريع (Mashari'i / Projects): Sira, 50, 100, 400 declarations.
Handles declaration, resolution, and scoring.

Akka and Sawa logic have been extracted to:
  - akka_manager.py  (Boss Card declarations)
  - sawa_manager.py  (Grand Slam declarations)
"""

from typing import Dict, List, Optional, Any
from game_engine.logic.rules.projects import check_project_eligibility, compare_projects
from server.logging_utils import logger


class ProjectManager:
    def __init__(self, game):
        self.game = game

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
         """Register a project declaration for a player during trick 1.

         Validates the project type against the player's hand, deduplicates,
         and stores the declaration for resolution at end of trick 1.
         """
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

    def auto_declare_bot_projects(self):
        """
        Auto-scan all bot players' hands and declare all eligible projects.
        Called at end of trick 1, right before resolve_declarations().
        Bots don't click the UI button — this simulates their announcement.
        """
        for player in self.game.players:
            if not getattr(player, 'is_bot', False):
                continue

            hand_projs = check_project_eligibility(player.hand, self.game.game_mode)
            if not hand_projs:
                continue

            # Initialize declarations for this position
            if player.position not in self.game.trick_1_declarations:
                self.game.trick_1_declarations[player.position] = []

            current_decls = self.game.trick_1_declarations[player.position]

            def get_proj_sig(p):
                cards_sig = "-".join(sorted([f"{c.rank}{c.suit}" for c in p.get('cards', [])]))
                return f"{p['type']}|{p['rank']}|{p.get('suit', 'ANY')}|{cards_sig}"

            for proj in hand_projs:
                proj_sig = get_proj_sig(proj)
                is_duplicate = any(get_proj_sig(d) == proj_sig for d in current_decls)

                if not is_duplicate:
                    safe = self._sanitize_project(proj)
                    self.game.trick_1_declarations[player.position].append(safe)

                    if player.position not in self.game.declarations:
                        self.game.declarations[player.position] = []
                    self.game.declarations[player.position].append(safe)

            if hand_projs:
                logger.info(f"Bot {player.name} auto-declared {len(hand_projs)} project(s): "
                           f"{[p['type'] for p in hand_projs]}")

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

