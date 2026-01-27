from typing import List, Dict, Tuple, Any
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, POINT_VALUES_SUN, POINT_VALUES_HOKUM
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
             if self.game.bidding_engine and self.game.bidding_engine.contract:
                 contract_variant = self.game.bidding_engine.contract.variant
             
             return is_move_legal(
                 card=card,
                 hand=hand,
                 table_cards=self.game.table_cards,
                 game_mode=self.game.game_mode,
                 trump_suit=self.game.trump_suit,
                 my_team=my_team,
                 players_team_map=players_team_map,
                 contract_variant=contract_variant
             )
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
        self.game.last_trick = {'cards': [tc['card'].to_dict() for tc in self.game.table_cards], 'winner': winner_pos}
        
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
            "playedBy": [t['playedBy'] for t in self.game.table_cards]
        }
        self.game.trick_history.append(trick_data)
        self.game.round_history.append(trick_data)
        
        self.game.table_cards = []
        self.game.current_turn = winner_player.index
        self.game.reset_timer() 
        
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
    def handle_qayd(self, reporter_index):
        """
        Processes a 'Qayd' (Penalty) claim.
        1. Checks validity of the LAST played card on the table.
        2. If Illegal: Offender loses round (Khasara).
        3. If Legal: Reporter loses round (False Claim).
        """
        try:
             reporter = self.game.players[reporter_index]
             
             if not self.game.table_cards:
                  return {"error": "No card to dispute"}
                  
             # Inspect last played card
             last_play = self.game.table_cards[-1]
             offender_pos = last_play['playedBy']
             is_illegal = False
             
             if 'metadata' in last_play and last_play['metadata'] and last_play['metadata'].get('is_illegal'):
                  is_illegal = True
                  
             # Determine Loser
             loser_team = None
             reason = ""
             
             if is_illegal:
                  # Claim Valid -> Offender Loses
                  offender = next(p for p in self.game.players if p.position == offender_pos)
                  loser_team = offender.team
                  reason = f"Qayd Valid: {offender_pos} played illegal move."
                  logger.info(reason)
             else:
                  # Claim Invalid -> Reporter Loses
                  loser_team = reporter.team
                  reason = f"Qayd Failed: Move was legal. {reporter.position} penalized."
                  logger.info(reason)
                  
             # Execute Penalty (Khasara)
             self.apply_khasara(loser_team, reason)
             return {"success": True, "message": reason}
             
        except Exception as e:
             logger.error(f"Error in handle_qayd: {e}")
             return {"error": str(e)}

    def apply_khasara(self, loser_team, reason):
        """Ends round giving full points (16/26) to the winner team."""
        winner_team = 'us' if loser_team == 'them' else 'them'
        
        # Calculate max round points
        points = 26 if self.game.game_mode == 'SUN' else 16
        
        # Multiply if doubled
        if self.game.doubling_level >= 2:
             points *= self.game.doubling_level
             
        score_us = points if winner_team == 'us' else 0
        score_them = points if winner_team == 'them' else 0
        
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

    # --- SAWA (SAWA) LOGIC ---
    def handle_sawa(self, player_index):
        """Player claims they can win all remaining tricks (Sawa/Sawa)"""
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
