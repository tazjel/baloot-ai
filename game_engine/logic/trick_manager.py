from typing import List, Dict, Tuple, Any
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, POINT_VALUES_SUN, POINT_VALUES_HOKUM
from server.logging_utils import logger, log_event

class TrickManager:
    def __init__(self, game):
        self.game = game

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
            # 0. Check Closed Doubling Constraint (Magfool)
            if not self.game.table_cards and self.game.bidding_engine and self.game.bidding_engine.contract:
                contract = self.game.bidding_engine.contract
                if self.game.game_mode == 'HOKUM' and contract.variant == 'CLOSED': # Magfool
                    if card.suit == self.game.trump_suit:
                        has_non_trump = any(c.suit != self.game.trump_suit for c in hand)
                        if has_non_trump:
                            return False

            if not self.game.table_cards:
                return True
            
            lead_play = self.game.table_cards[0]
            lead_card = lead_play['card']
            lead_suit = lead_card.suit
            
            # 1. Follow Suit (Mandatory in Sun & Hokum)
            has_suit = any(c.suit == lead_suit for c in hand)
            if has_suit:
                if card.suit != lead_suit:
                    return False
                if self.game.game_mode == 'HOKUM' and lead_suit == self.game.trump_suit:
                     pass 
                else:
                     return True

            if self.game.game_mode == 'SUN':
                return True # If can't follow suit, play anything.
            
            # --- HOKUM STRICT RULES ---
            
            # Determine Current Winner of the Trick
            winner_idx = self.get_trick_winner()
            curr_winner_play = self.game.table_cards[winner_idx]
            curr_winner_pos = curr_winner_play['playedBy']
            
            me = self.game.players[self.game.current_turn]
            my_team = me.team
            winner_p = next(p for p in self.game.players if p.position == curr_winner_pos)
            is_partner_winning = (winner_p.team == my_team)
            
            # 2. Partner Winning? -> Play Anything (unless forced to follow suit, handled above)
            if is_partner_winning:
                return True

            # 3. Enemy Winning
            # Must Trump if possible OR Must Over-Trump
            
            has_trump = any(c.suit == self.game.trump_suit for c in hand)
            
            # Case A: Void in Lead Suit
            if not has_suit:
                if has_trump:
                    # Must play Trump
                    if card.suit != self.game.trump_suit:
                        return False
                    
                    # Must Over-Trump?
                    if curr_winner_play['card'].suit == self.game.trump_suit:
                        can_beat, beating_cards = self.can_beat_trump(curr_winner_play['card'], hand)
                        if can_beat:
                             if card not in beating_cards: 
                                  played_strength = 100 + ORDER_HOKUM.index(card.rank)
                                  winning_strength = 100 + ORDER_HOKUM.index(curr_winner_play['card'].rank)
                                  if played_strength <= winning_strength:
                                       return False
                return True

            # Case B: Followed Suit (Lead was Trump) -> has_suit True
            if lead_suit == self.game.trump_suit:
                 can_beat, beating_cards = self.can_beat_trump(curr_winner_play['card'], hand)
                 if can_beat:
                      played_strength = 100 + ORDER_HOKUM.index(card.rank)
                      winning_strength = 100 + ORDER_HOKUM.index(curr_winner_play['card'].rank)
                      if played_strength <= winning_strength:
                           return False

            return True

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
        if self.game.sawa_state.get('challenge_active', False):
             claimer_pos = self.game.sawa_state['claimer']
             claimer_team = 'us' if (claimer_pos in ['Bottom', 'Top']) else 'them'
             winner_team = 'us' if (winner_pos in ['Bottom', 'Top']) else 'them'
             
             if winner_team != claimer_team:
                  self.game.sawa_failed_khasara = True 
                  self.game.end_round()
                  return

        if not winner_player.hand:
            self.game.end_round()
