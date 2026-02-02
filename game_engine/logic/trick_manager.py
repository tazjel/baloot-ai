from typing import List, Dict, Tuple, Any
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, POINT_VALUES_SUN, POINT_VALUES_HOKUM
from game_engine.logic.referee import Referee
from server.logging_utils import logger, log_event

class TrickManager:
    def __init__(self, game):
        self.game = game
        self.qayd_state = {'active': False, 'reporter': None, 'reason': None, 'target_play': None}
        self.sawa_state = {"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False}

    def get_card_points(self, card: Card) -> int:
        if self.game.game_mode == "SUN":
             return POINT_VALUES_SUN[card.rank]
        else:
             if card.suit == self.game.trump_suit:
                  return POINT_VALUES_HOKUM[card.rank]
             else:
                  return POINT_VALUES_SUN[card.rank]

    def get_trick_winner(self) -> int:
        lead_card = self.game.table_cards[0]['card']
        best_idx = 0
        current_best = -1
        
        for i, play in enumerate(self.game.table_cards):
            card = play['card']
            strength = -1
            
            if self.game.game_mode == "SUN":
                if card.suit == lead_card.suit:
                    strength = ORDER_SUN.index(card.rank)
            else:
                if card.suit == self.game.trump_suit:
                    strength = 100 + ORDER_HOKUM.index(card.rank)
                elif card.suit == lead_card.suit:
                    strength = ORDER_SUN.index(card.rank)
            
            if strength > current_best:
                current_best = strength
                best_idx = i
        return best_idx

    def can_beat_trump(self, winning_card: Card, hand: List[Card]) -> Tuple[bool, List[Card]]:
        winning_strength = 100 + ORDER_HOKUM.index(winning_card.rank)
        beating_cards = []
        for c in hand:
            if c.suit == self.game.trump_suit:
                 s = 100 + ORDER_HOKUM.index(c.rank)
                 if s > winning_strength:
                      beating_cards.append(c)
        return (len(beating_cards) > 0), beating_cards

    def is_valid_move(self, card: Card, hand: List[Card]) -> bool:
        try:
             from game_engine.logic.validation import is_move_legal
             
             # Prepare context
             # Map players to teams
             players_team_map = {p.position: p.team for p in self.game.players}
             my_idx = self.game.current_turn
             my_team = self.game.players[my_idx].team
             
             contract_variant = None
             bidding_engine = getattr(self.game, 'bidding_engine', None)
             if bidding_engine and hasattr(bidding_engine, 'contract') and bidding_engine.contract:
                 contract_variant = bidding_engine.contract.variant
             
             result = is_move_legal(
                 card=card,
                 hand=hand,
                 table_cards=self.game.table_cards,
                 game_mode=self.game.game_mode,
                 trump_suit=self.game.trump_suit,
                 my_team=my_team,
                 players_team_map=players_team_map,
                 contract_variant=contract_variant
             )
             if not result:
                  logger.error(f"❌ [TrickManager] ILLEGAL MOVE DETECTED: {card}")
             return result
        except Exception as e:
            logger.error(f"Error in is_valid_move: {e}")
            return True # Fallback

    def resolve_trick(self):
        winner_idx = self.get_trick_winner()
        winner_play = self.game.table_cards[winner_idx]
        winner_pos = winner_play['playedBy']
        
        winner_player = next(p for p in self.game.players if p.position == winner_pos)
        
        points = 0
        for play in self.game.table_cards:
             points += self.get_card_points(play['card'])
        
        # Update last trick for animation
        # Update last trick for animation
        self.game.last_trick = {
            'cards': [tc['card'].to_dict() for tc in self.game.table_cards], 
            'winner': winner_pos,
            'metadata': [tc.get('metadata') for tc in self.game.table_cards]
        }
        
        log_event("TRICK_WIN", self.game.room_id, details={
            "winner": winner_pos,
            "points": points,
            "trick_num": len(self.game.round_history) + 1
        })
        
        # Clear table
        trick_data = {
            "winner": winner_pos,
            "points": points,
            "cards": [t['card'].to_dict() for t in self.game.table_cards],
            "playedBy": [t['playedBy'] for t in self.game.table_cards],
            # Preserve metadata (including is_illegal) for Qayd checks
            "metadata": [t.get('metadata') for t in self.game.table_cards]
        }
        self.game.trick_history.append(trick_data)
        self.game.round_history.append(trick_data)
        
        self.game.table_cards = []
        self.game.current_turn = winner_player.index
        self.game.reset_timer() 
        
        # --- ANALYTICS: Track Win Probability ---
        prob = self.game.calculate_win_probability()
        self.game.win_probability_history.append({
            "trick": len(self.game.round_history),
            "us": prob
        }) 
        
        # --- PROJECT RESOLUTION (End of Trick 1) ---
        if len(self.game.round_history) == 1:
             # This will be handled by ProjectManager via Game delegation
             if hasattr(self.game, 'project_manager'):
                 self.game.project_manager.resolve_declarations()
             else:
                 # Fallback if refactor partial
                 if hasattr(self.game, 'resolve_declarations'):
                     self.game.resolve_declarations()

        # --- SAWA CHALLENGE CHECK ---
        if self.sawa_state.get('challenge_active', False):
             claimer_pos = self.sawa_state['claimer']
             claimer_team = 'us' if (claimer_pos in ['Bottom', 'Top']) else 'them'
             winner_team = 'us' if (winner_pos in ['Bottom', 'Top']) else 'them'
             
             if winner_team != claimer_team:
                  self.game.sawa_failed_khasara = True 
                  self.game.end_round()
                  return

        if not winner_player.hand:
            self.game.end_round()

    # --- QAYD (PENALTY) LOGIC ---
    def propose_qayd(self, reporter_index):
        """
        Phase 1: Propose a Qayd accusation.
        Validates the claim and prepares the verdict, but does NOT apply it yet.
        Returns the Qayd State for review.
        """
        try:
             reporter = self.game.players[reporter_index]
             
             # Reset Qayd State for new proposal
             self.qayd_state = {
                 'active': True,
                 'reporter': reporter.position, # Store Position String (e.g. 'Top')
                 'status': 'REVIEW',
                 'verdict_message': None,
                 'crime_card_index': -1,
                 'proof_card_index': -1,
                 'penalty_points': 0,
                 'loser_team': None,
                 'reason': None,
                 'target_play': None, # Snapshot of the play object
                 'target_source': 'table_cards' # 'table_cards' or 'last_trick'
             }
             
             # Locate the Crime (Illegal Move)
             # Priority 1: Check Active Table
             crime_card_found = False
             crime_card_idx_in_trick = -1 # Relative to current trick
             
             # Search backwards in current table
             for i, play in enumerate(reversed(self.game.table_cards)):
                  if (play.get('metadata') or {}).get('is_illegal'):
                       # Found it
                       crime_card_found = True
                       # Save absolute index or relative? 
                       # For UI, maybe relative to tableCards is best, or unique ID.
                       # Let's verify how UI renders. Likely tableCards map.
                       # But if it's buried, we need to know which one.
                       crime_card_idx_in_trick = len(self.game.table_cards) - 1 - i
                       self.qayd_state['crime_card_index'] = crime_card_idx_in_trick
                       # Serialize play to ensure Card is a dict
                       serialized_play = {
                           'card': play['card'].to_dict() if hasattr(play['card'], 'to_dict') else play['card'],
                           'playedBy': play.get('playedBy'),
                           'metadata': play.get('metadata')
                       }
                       self.qayd_state['target_play'] = serialized_play
                       self.qayd_state['target_source'] = 'table_cards'
                       break
             
             # Priority 2: Check Last Trick (if table cleared or not found in active)
             if not crime_card_found and self.game.last_trick and self.game.last_trick.get('metadata'):
                   for i, meta in enumerate(self.game.last_trick['metadata']):
                        if meta and meta.get('is_illegal'):
                             crime_card_found = True
                             self.qayd_state['crime_card_index'] = i # Index in last_trick
                             self.qayd_state['target_source'] = 'last_trick' # Flag to UI to look at last trick
                             # Need to reconstruct target_play for last_trick
                             # We stored 'cards' and 'playedBy' in trick_history
                             if self.game.round_history:
                                  last_trick_hist = self.game.round_history[-1]
                                  card_obj = Card.from_dict(last_trick_hist['cards'][i])
                                  self.qayd_state['target_play'] = {
                                      'card': card_obj.to_dict(),  # Serialize to dict for JSON
                                      'playedBy': last_trick_hist['playedBy'][i],
                                      'metadata': last_trick_hist['metadata'][i]
                                  }
                             break
                             
             if not crime_card_found:
                  pass



    # --- VERDICT LOGIC (Reused/Refactored) ---
             # (Simplified for Proposal: We know if it's illegal by the flag)
             
             violation = None
             if crime_card_found:
                  # If we found the flag, we trust the Engine's validation
                  # We can extract the specific violation string from metadata if avail
                  if 'target_play' in self.qayd_state and self.qayd_state['target_play']:
                       violation = self.qayd_state['target_play']['metadata'].get('illegal_reason', 'Rule Violation')
             
             # Calculate Kaboot / Penalty
             game_mode = self.game.game_mode
             points_override = None
             
             # Note: We are trusting the 'is_illegal' flag 100% here for simplicity.
             # The Referee.check_* methods act as a double-check or for reasoning.
             # If flag is missing but move was actually illegal (complex case), we fail to catch it.
             # But we fixed flag propagation, so this should suffice.
             
             if crime_card_found:
                  # Valid Claim
                  # Determine Offender
                  offender_pos = self.qayd_state['target_play']['playedBy']
                  offender = next(p for p in self.game.players if p.position == offender_pos)
                  self.qayd_state['loser_team'] = offender.team
                  self.qayd_state['reason'] = f"Qayd Valid: {violation}"
                  self.qayd_state['verdict'] = f"QATA: {offender.position} played illegal move ({violation})"
             else:
                  # Invalid Claim
                  self.qayd_state['loser_team'] = reporter.team
                  self.qayd_state['reason'] = f"Qayd Failed: Move was legal."
                  self.qayd_state['verdict'] = f"False Accusation by {reporter.position}"
                  
             # Calculate Points
             # Apply Kaboot logic if needed (TODO: port estimate_kaboot here or keep it simple)
             # For now, standard penalty.
             base_points = 26 if game_mode == 'SUN' else 16
             if self.game.doubling_level >= 2: base_points *= self.game.doubling_level
             
             # Add projects
             project_points = 0
             if hasattr(self.game, 'declarations') and self.game.declarations:
                  for pos, projs in self.game.declarations.items():
                       for proj in projs:
                            project_points += proj.get('score', 0)
             
             self.qayd_state['penalty_points'] = base_points + project_points
             
             # Pause Game
             self.game.timer_paused = True
             
             return {"success": True, "qayd_state": self.qayd_state}
             
        except Exception as e:
             logger.error(f"Error in propose_qayd: {e}")
             return {"error": str(e)}

    def cancel_qayd(self):
        """
        Cancels the current Qayd investigation and resets state.
        """
        self.qayd_state = {'active': False, 'reporter': None, 'reason': None, 'target_play': None}
        return {'success': True}

    def confirm_qayd(self):
        """
        Phase 2: Confirm and Execute.
        Applies the penalty calculated in Phase 1.
        """
        if not self.qayd_state['active'] or self.qayd_state['status'] != 'REVIEW':
             return {"error": "No Qayd details to confirm"}
             
        # Apply Logic
        loser_team = self.qayd_state['loser_team']
        reason = self.qayd_state['reason']
        points = self.qayd_state['penalty_points']
        
        # Log resolution
        logger.info(f"QAYD CONFIRMED: {reason}. {loser_team} loses {points} pts.")
        
        self.apply_khasara(loser_team, reason, points_override=points)
        
        # Reset State (handled in reset_round_state usually, but good to clear status)
        self.qayd_state['status'] = 'RESOLVED'
        
        return {"success": True}

    # Helper alias for backward compatibility or simple call
    def handle_qayd(self, reporter_index):
        # Auto-confirm for now if called directly (or redirect to proposal)
        # return self.propose_qayd(reporter_index) 
        # Actually, let's make handle_qayd just call propose then confirm for "Legacy/Bot" instant behavior
        # UNLESS we want the bot to propose and wait?
        # User said "Wait for me to click confirm".
        
        # So Bot calls propose_qayd.
        # Frontend sees REVIEW state.
        # User clicks Confirm.
        return self.propose_qayd(reporter_index)

    def apply_khasara(self, loser_team, reason, points_override=None):
        """Ends round giving full points (16/26) to the winner team."""
        winner_team = 'us' if loser_team == 'them' else 'them'
        
        # Calculate max round points
        points = points_override if points_override else (26 if self.game.game_mode == 'SUN' else 16)
        
        # Multiply if doubled
        if self.game.doubling_level >= 2:
             points *= self.game.doubling_level
             
        # Calculate Project Points (All Declared Projects)
        project_points = 0
        if hasattr(self.game, 'declarations') and self.game.declarations:
             for pos, projs in self.game.declarations.items():
                  for proj in projs:
                       project_points += proj.get('score', 0)
                       
        total_points = points + project_points
             
        score_us = total_points if winner_team == 'us' else 0
        score_them = total_points if winner_team == 'them' else 0
        
        # Log and End
        log_event("ROUND_END_PENALTY", self.game.room_id, details={
             "reason": reason,
             "loser": loser_team,
             "scores": {'us': score_us, 'them': score_them}
        })
        
        # Update Match Scores
        self.game.match_scores['us'] += score_us
        self.game.match_scores['them'] += score_them
        
        # History Snapshot
        self.game.past_round_results.append({
             'roundNumber': len(self.game.past_round_results) + 1,
             'bid': self.game.bid,
             'us': {'result': score_us},
             'them': {'result': score_them},
             'winner': winner_team,
             'reason': reason
        })
        
        # Proceed to next round
        self.game.dealer_index = (self.game.dealer_index + 1) % 4
        if self.game.match_scores['us'] >= 152 or self.game.match_scores['them'] >= 152:
             self.game.phase = "GAMEOVER" # GamePhase.GAMEOVER.value (avoid circular import if enum not avail)
        else:
             self.game.phase = "FINISHED" # GamePhase.FINISHED.value
             
        self.game.reset_timer()

    # --- SAWA LOGIC ---
    def handle_sawa(self, player_index):
        """Player claims they can win all remaining tricks (Sawa)"""
        if player_index != self.game.current_turn:
             return {"error": "Not your turn"}
        
        if not self.game.players[player_index].hand:
             return {"error": "Hand empty"}

        if len(self.game.table_cards) > 0:
             return {"error": "Cannot called Sawa after playing a card"}
             
        self.sawa_state = {
            "active": True,
            "claimer": self.game.players[player_index].position, 
            "responses": {}, 
            "status": "PENDING",
            "challenge_active": False 
        }
        return {"success": True, "sawa_state": self.sawa_state}

    def handle_sawa_response(self, player_index, response):
        if not hasattr(self, 'sawa_state') or not self.sawa_state.get('active') or self.sawa_state.get('status') != 'PENDING':
             return {"error": "No active Sawa claim"}
             
        responder_pos = self.game.players[player_index].position
        claimer_pos = self.sawa_state['claimer']
        
        claimer_team = 'us' if claimer_pos in ['Bottom', 'Top'] else 'them'
        responder_team = 'us' if responder_pos in ['Bottom', 'Top'] else 'them'
        
        if claimer_team == responder_team:
             return {"error": "Teammate cannot respond"}
             
        self.sawa_state['responses'][responder_pos] = response
        
        opponents = [p for p in self.game.players if p.team != claimer_team]
        op_responses = [self.sawa_state['responses'].get(p.position) for p in opponents]
        
        if 'REFUSE' in op_responses:
             self.sawa_state['status'] = 'REFUSED'
             self.sawa_state['active'] = False
             self.sawa_state['challenge_active'] = True  # Enable challenge mode
             return {"success": True, "sawa_status": "REFUSED", "challenge": True}
             
        if all(r == 'ACCEPT' for r in op_responses):
             self.sawa_state['status'] = 'ACCEPTED'
             self._resolve_sawa_win() 
             return {"success": True, "sawa_status": "ACCEPTED"}
             
        return {"success": True, "message": "Waiting for partner"}

    def _resolve_sawa_win(self):
        """End round immediately, giving all remaining potential points to claimer's team"""
        claimer_pos = self.sawa_state["claimer"]
        
        # Collect all cards from hands
        all_cards = []
        for p in self.game.players:
            all_cards.extend(p.hand)
            p.hand = [] # Empty hands
            
        # Create a dummy trick with all cards won by claimer
        dummy_trick = {
            'cards': [{'card': c.to_dict(), 'playedBy': claimer_pos} for c in all_cards], 
            'winner': claimer_pos,
            'points': 0 
        }
        
        total_trick_points = 0
        for c in all_cards:
             total_trick_points += self.get_card_points(c) # Use self.get_card_points
             
        dummy_trick['points'] = total_trick_points
        
        self.game.round_history.append(dummy_trick)
        self.game.end_round()

    def reset_state(self):
        self.sawa_state = {"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False}
        self.qayd_state = {'active': False, 'reporter': None, 'reason': None, 'target_play': None}
