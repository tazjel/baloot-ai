from typing import Dict, List, Optional, Any
from game_engine.logic.utils import scan_hand_for_projects, compare_projects
from server.logging_utils import logger

class ProjectManager:
    def __init__(self, game):
        self.game = game
        self.akka_state = None

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
             hand_projs = scan_hand_for_projects(player.hand, self.game.game_mode)
             
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
                          self.game.trick_1_declarations[player.position].append(match)
                          
                          # updates self.declarations too for UI
                          if player.position not in self.game.declarations:
                               self.game.declarations[player.position] = []
                          self.game.declarations[player.position].append(match)
                  
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
                  self.game.declarations[pos].append(item['proj'])
        
        # Trigger Reveal Animation
        if self.game.declarations:
             self.game.is_project_revealing = True 

    def init_akka(self):
         self.akka_state = None

    # --- AKKA LOGIC ---
    def check_akka_eligibility(self, player_index):
        """
        Check if player holds the highest remaining card for any suit they have.
        STRICT RULES:
        1. Game Mode must be HOKUM.
        2. Suit must NOT be Trump.
        3. Card itself must NOT be Ace (Ace is self-evident).
        4. Card must be the highest remaining card of that suit.
        """
        from game_engine.models.constants import ORDER_SUN 
        import time 
        
        # 1. Game Mode Restriction: ONLY HOKUM
        if self.game.game_mode != 'HOKUM':
            return []

        p = self.game.players[player_index]
        if not p.hand: return []
        
        # Gather all played cards in this round
        played_cards = set()
        
        # 1. Completed tricks
        for t in self.game.round_history:
             for c_dict in t['cards']:
                 played_cards.add(f"{c_dict['rank']}{c_dict['suit']}")
                 
        # 2. Current table
        for tc in self.game.table_cards:
             c = tc['card']
             played_cards.add(f"{c.rank}{c.suit}")
             
        eligible_suits = []
        
        # Group hand by suit
        hand_by_suit = {}
        for c in p.hand:
             if c.suit not in hand_by_suit: hand_by_suit[c.suit] = []
             hand_by_suit[c.suit].append(c)
             
        for suit, cards in hand_by_suit.items():
             # 2. Suit Restriction: NO TRUMP
             if suit == self.game.trump_suit:
                 continue
                 
             # Rank Order for Non-Trump in Hokum follows SUN order (A > 10 > K...)
             rank_order = ORDER_SUN
             
             # Find my best card in this suit
             my_best = max(cards, key=lambda c: rank_order.index(c.rank))
             
             # 3. Card Restriction: NO ACES
             if my_best.rank == 'A':
                 continue
                 
             my_strength = rank_order.index(my_best.rank)
             
             # Check if any card in UNPLAYED (Deck + Others) is stronger
             can_declare = True
             
             for r in rank_order:
                  strength = rank_order.index(r)
                  if strength > my_strength:
                       # This rank is stronger. Is it available?
                       # It is available if NOT played.
                       card_sig = f"{r}{suit}"
                       if card_sig not in played_cards:
                            # It is out there!
                            can_declare = False
                            break
                            
             if can_declare:
                  eligible_suits.append(suit)
                  
        return eligible_suits

    def handle_akka(self, player_index):
        try:
             import time
             eligible = self.check_akka_eligibility(player_index)
             p = self.game.players[player_index]

             if not eligible:
                  # INVALID AKKA! REFEREE INTERVENTION
                  # We record the attempt but flag it as a violation
                  logger.warning(f"INVALID AKKA CLAIM by {p.position}")
                  
                  # Trigger Qayd/Blunder
                  self.game.increment_blunder(player_index)
                  
                  # We return success=False but with specific error code to let UI show Referee
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
             
             # Valid!
             
             # Update State
             self.akka_state = {
                 'claimer': p.position,
                 'suits': eligible, # Sending list of suits where he is Boss
                 'timestamp': time.time()
             }
             
             return {"success": True, "akka_state": self.akka_state}
             
        except Exception as e:
             logger.error(f"Error in handle_akka: {e}")
             return {"error": str(e)} 
