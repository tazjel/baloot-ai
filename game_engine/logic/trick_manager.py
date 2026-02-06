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
        self.ignored_crimes = set() # Track cancelled accusations (trick_idx, card_idx)

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
        
        # Update last trick for animation (include playedBy per card for DisputeModal)
        self.game.last_trick = {
            'cards': [{'card': tc['card'].to_dict(), 'playedBy': tc['playedBy']} for tc in self.game.table_cards], 
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
            "cards": [{'card': t['card'].to_dict(), 'playedBy': t['playedBy']} for t in self.game.table_cards],
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
    # NOTE: All Qayd logic has been moved to QaydEngine (qayd_engine.py).
    # The methods below are DEPRECATED stubs kept only to prevent import errors.
    # They redirect to QaydEngine via self.game.

    def propose_qayd(self, reporter_index, crime_card=None, proof_card=None, qayd_type='REVOKE', crime_trick_idx=None, proof_trick_idx=None):
        """DEPRECATED: Redirects to QaydEngine.trigger()."""
        logger.warning("[DEPRECATED] propose_qayd called — redirecting to QaydEngine")
        return self.game.handle_qayd_trigger(reporter_index)


    def cancel_qayd(self):
        """DEPRECATED: Redirects to QaydEngine.cancel()."""
        logger.warning("[DEPRECATED] cancel_qayd called — redirecting to QaydEngine")
        return self.game.handle_qayd_cancel()

    def confirm_qayd(self):
        """DEPRECATED: Redirects to QaydEngine.confirm()."""
        logger.warning("[DEPRECATED] confirm_qayd called — redirecting to QaydEngine")
        return self.game.handle_qayd_confirm()

    def handle_qayd(self, reporter_index):
        """DEPRECATED: Redirects to QaydEngine.trigger()."""
        logger.warning("[DEPRECATED] handle_qayd called — redirecting to QaydEngine")
        return self.game.handle_qayd_trigger(reporter_index)

    def apply_khasara(self, loser_team, reason, points_override=None):
        """DEPRECATED: Use game.apply_qayd_penalty() via QaydEngine instead."""
        logger.warning("[DEPRECATED] apply_khasara called — redirecting to game.apply_qayd_penalty")
        winner_team = 'us' if loser_team == 'them' else 'them'
        self.game.apply_qayd_penalty(loser_team, winner_team)

    # --- SAWA LOGIC ---
    def handle_sawa(self, player_index):
        """Player claims they can win all remaining tricks (Sawa)"""
        if player_index != self.game.current_turn:
             return {"error": "Not your turn"}
        
        if not self.game.players[player_index].hand:
             return {"error": "Hand empty"}

        if len(self.game.table_cards) > 0:
             return {"error": "Cannot called Sawa after playing a card"}
             
        self.sawa_state.clear()
        self.sawa_state.update({
            "active": True,
            "claimer": self.game.players[player_index].position, 
            "responses": {}, 
            "status": "PENDING",
            "challenge_active": False 
        })
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
        self.sawa_state.clear()
        self.sawa_state.update({"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False})
        
        # NOTE: qayd_state is managed exclusively by QaydEngine.
        # Do NOT touch it here. QaydEngine.reset() handles cleanup.
        
        self.ignored_crimes = set()
