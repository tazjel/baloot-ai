from typing import List, Dict, Tuple, Any
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, POINT_VALUES_SUN, POINT_VALUES_HOKUM
from game_engine.logic.referee import Referee
from server.logging_utils import logger, log_event

class TrickManager:
    def __init__(self, game):
        self.game = game
        self.sawa_state = {"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False}
        # qayd_state and ignored_crimes moved to ChallengePhase

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
        
        for card in hand:
            if card.suit == self.game.trump_suit:
                card_strength = 100 + ORDER_HOKUM.index(card.rank)
                if card_strength > winning_strength:
                    beating_cards.append(card)
        
        return len(beating_cards) > 0, beating_cards

    def is_valid_move(self, player_or_card, card_or_hand, hand=None, table_cards=None, trump_suit=None, game_mode=None) -> bool:
        """Central Validation using Referee. Supports (player_index, card, ...) or (card, hand)."""
        try:
             # Determine signature
             if isinstance(player_or_card, int):
                 # Signature: (player_index, card, hand, table_cards, trump_suit, game_mode)
                 player_index = player_or_card
                 card = card_or_hand
                 # 'hand' argument is already populated if passed positionally
             else:
                 # Signature: (card, hand) calling convention from Game.is_valid_move
                 player_index = self.game.current_turn
                 card = player_or_card
                 hand = card_or_hand
                 
             # Fill defaults from Game state if not provided
             if hand is None and player_index is not None and 0 <= player_index < len(self.game.players):
                  hand = self.game.players[player_index].hand
                  
             if table_cards is None: table_cards = self.game.table_cards
             if trump_suit is None: trump_suit = self.game.trump_suit
             if game_mode is None: game_mode = self.game.game_mode

             # Convert dicts to Card objects if needed
             card_obj = Card.from_dict(card) if isinstance(card, dict) else card
             hand_objs = [Card.from_dict(c) if isinstance(c, dict) else c for c in hand]
             table_objs = [
                 {'card': Card.from_dict(t['card']) if isinstance(t['card'], dict) else t['card'], 'playedBy': t['playedBy']}
                 for t in table_cards
             ]
             
             result, reason = Referee.validate_move(
                 card_obj, 
                 hand_objs, 
                 table_objs, 
                 trump_suit, 
                 game_mode,
                 self.game.players[player_index].team,
                 self.game.players[player_index].position
             )
             
             # Tag metadata automatically
             if isinstance(card, dict): # Only tag if it's a dict we can mutate
                 if not result:
                      card['metadata'] = {'is_illegal': True, 'illegal_reason': reason}
                 else:
                      card['metadata'] = {'is_illegal': False}
             
             if not result:
                  logger.warning(f"⚠️ [Referee] Flagged ILLEGAL move: {card} Reason: {reason}")
                  
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
             if hasattr(self.game, 'project_manager'):
                 self.game.project_manager.resolve_declarations()
             elif hasattr(self.game, 'resolve_declarations'):
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

    def apply_khasara(self, loser_team, reason, points_override=None):
        """
        Applies KHASARA (loss of round) to a team.
        Called by ChallengePhase (Qayd) or ScoringEngine.
        """
        winner_team = 'us' if loser_team == 'them' else 'them'
        
        points = points_override if points_override else (26 if self.game.game_mode == 'SUN' else 16)
        if self.game.doubling_level >= 2:
             points *= self.game.doubling_level
             
        project_points = 0
        if hasattr(self.game, 'declarations') and self.game.declarations:
             for pos, projs in self.game.declarations.items():
                  for proj in projs:
                       project_points += proj.get('score', 0)
                       
        total_points = points + project_points
             
        score_us = total_points if winner_team == 'us' else 0
        score_them = total_points if winner_team == 'them' else 0
        
        log_event("ROUND_END_PENALTY", self.game.room_id, details={
             "reason": reason,
             "loser": loser_team,
             "scores": {'us': score_us, 'them': score_them}
        })
        
        self.game.match_scores['us'] += score_us
        self.game.match_scores['them'] += score_them
        
        self.game.past_round_results.append({
             'roundNumber': len(self.game.past_round_results) + 1,
             'bid': self.game.bid,
             'us': {'result': score_us},
             'them': {'result': score_them},
             'winner': winner_team,
             'reason': reason
        })
        
        self.game.dealer_index = (self.game.dealer_index + 1) % 4
        if self.game.match_scores['us'] >= 152 or self.game.match_scores['them'] >= 152:
             self.game.phase = "GAMEOVER"
        else:
             self.game.phase = "FINISHED"
             
        self.game.reset_timer()

    def handle_sawa(self, player_index):
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
        claimer_pos = self.sawa_state["claimer"]
        
        all_cards = []
        for p in self.game.players:
            all_cards.extend(p.hand)
            p.hand = [] 
            
        dummy_trick = {
            'cards': [{'card': c.to_dict(), 'playedBy': claimer_pos} for c in all_cards], 
            'winner': claimer_pos,
            'points': 0 
        }
        
        total_trick_points = 0
        for c in all_cards:
             total_trick_points += self.get_card_points(c) 
             
        dummy_trick['points'] = total_trick_points
        
        self.game.round_history.append(dummy_trick)
        self.game.end_round()

    def reset_state(self):
        self.sawa_state = {"active": False, "claimer": None, "responses": {}, "status": "NONE", "challenge_active": False}
        # qayd_state is now managed by ChallengePhase
        # ignored_crimes is now managed by ChallengePhase
