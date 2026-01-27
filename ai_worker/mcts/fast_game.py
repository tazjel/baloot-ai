
import copy
from typing import List, Dict, Tuple
from game_engine.models.card import Card
from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM, POINT_VALUES_SUN, POINT_VALUES_HOKUM
from game_engine.logic.validation import is_move_legal

class FastGame:
    """
    A lightweight, pure-logic game state for MCTS simulations.
    Optimized for speed: No logs, no metadata, no events.
    """
    def __init__(self, 
                 players_hands: List[List[Card]], 
                 trump: str, 
                 mode: str, 
                 current_turn: int, 
                 dealer_index: int,
                 us_score: int = 0,
                 them_score: int = 0,
                 tricks_history: List = None,
                 table_cards: List = None):
        
        # State
        self.hands = players_hands # List of Lists of Cards
        self.trump = trump
        self.mode = mode
        self.current_turn = current_turn
        self.dealer_index = dealer_index
        
        self.scores = {'us': us_score, 'them': them_score}
        self.tricks_collected = {'us': 0, 'them': 0} # Number of tricks
        
        self.table = table_cards if table_cards else [] # List of {'card': Card, 'playedBy': 'Bottom/Right...'} (Wait, simulation uses int indices usually)
        # Using int indices 0-3 for performance instead of strings
        self.played_cards_in_trick = [] # List of (player_idx, Card)
        
        if table_cards:
             # Convert existing table to internal format (player_idx, Card)
             # Map 'playedBy' (Bottom/Right/Top/Left) to index (0/1/2/3)
             pos_to_idx = {'Bottom': 0, 'Right': 1, 'Top': 2, 'Left': 3}
             
             for tc in table_cards:
                 # Check if 'card' is already a Card object or dict
                 c_obj = tc['card']
                 if isinstance(c_obj, dict):
                     c_obj = Card(c_obj['suit'], c_obj['rank'])
                     
                 # Check playedBy format
                 p_by = tc.get('playedBy', '')
                 p_idx = pos_to_idx.get(p_by, 0) # Default to 0 if unknown (risk, but mostly valid)
                 
                 self.played_cards_in_trick.append((p_idx, c_obj))
                 
             # Correctly set turn if cards are on table
             # If table has K cards, the next turn is (leader + K) % 4
             if self.played_cards_in_trick:
                 leader_idx = self.played_cards_in_trick[0][0]
                 cards_played_count = len(self.played_cards_in_trick)
                 self.current_turn = (leader_idx + cards_played_count) % 4 

        self.tricks_history = tricks_history if tricks_history else []
        self.is_finished = False
        
        # Cache for teams (0=Bottom=Us, 1=Right=Them, 2=Top=Us, 3=Left=Them)
        self.teams = [
             'us', 'them', 'us', 'them'
        ]

    def clone(self):
        """Deep copy for MCTS branching."""
        # Manual copy is faster than deepcopy usually for specific structures
        new_hands = [h[:] for h in self.hands] # Slice copy lists
        new_game = FastGame(
            players_hands=new_hands,
            trump=self.trump,
            mode=self.mode,
            current_turn=self.current_turn,
            dealer_index=self.dealer_index,
            us_score=self.scores['us'],
            them_score=self.scores['them']
        )
        new_game.played_cards_in_trick = self.played_cards_in_trick[:]
        return new_game

    def get_legal_moves(self) -> List[int]:
        """Returns list of INDICES of cards in current player's hand."""
        hand = self.hands[self.current_turn]
        if not hand: return []
        
        # Reuse validation logic
        # We need to construct 'table_cards' format expected by validator
        # Validator expects: [{'card': CardObj, 'playedBy': 'Bottom'}]
        # We have (player_idx, Card). We need map idx->pos.
        
        pos_map = {0: 'Bottom', 1: 'Right', 2: 'Top', 3: 'Left'}
        
        validator_table = []
        for p_idx, c in self.played_cards_in_trick:
             validator_table.append({'card': c, 'playedBy': pos_map[p_idx]})
             
        # My Team
        my_team = self.teams[self.current_turn]
        
        # Players Map (for validator)
        players_team_map = {'Bottom': 'us', 'Right': 'them', 'Top': 'us', 'Left': 'them'}
        
        legal_indices = []
        for i, card in enumerate(hand):
             if is_move_legal(
                 card=card,
                 hand=hand,
                 table_cards=validator_table,
                 game_mode=self.mode,
                 trump_suit=self.trump,
                 my_team=my_team,
                 players_team_map=players_team_map
             ):
                 legal_indices.append(i)
                 
        return legal_indices

    def apply_move(self, card_idx: int):
        """Executes move, updates state, resolves trick if full."""
        player_idx = self.current_turn
        card = self.hands[player_idx].pop(card_idx)
        
        self.played_cards_in_trick.append((player_idx, card))
        
        if len(self.played_cards_in_trick) == 4:
             self._resolve_trick()
        else:
             self.current_turn = (self.current_turn + 1) % 4
             
    def _resolve_trick(self):
        # Determine winner
        lead_play = self.played_cards_in_trick[0]
        lead_card = lead_play[1]
        lead_suit = lead_card.suit
        
        best_play = lead_play
        best_strength = -1
        
        # Strength Calc
        for play in self.played_cards_in_trick:
             p_idx, card = play
             strength = -1
             
             if self.mode == 'SUN':
                  if card.suit == lead_suit:
                       strength = ORDER_SUN.index(card.rank)
             else: # HOKUM
                  if card.suit == self.trump:
                       strength = 100 + ORDER_HOKUM.index(card.rank)
                  elif card.suit == lead_suit:
                       strength = ORDER_SUN.index(card.rank)
                       
             if strength > best_strength:
                  best_strength = strength
                  best_play = play
                  
        winner_idx = best_play[0]
        winner_team = self.teams[winner_idx]
        
        # Calculate Points
        points = 0
        for _, card in self.played_cards_in_trick:
             if self.mode == 'SUN':
                  points += POINT_VALUES_SUN.get(card.rank, 0)
             else:
                  val = POINT_VALUES_HOKUM.get(card.rank, 0)
                  # J/9 special case is built into constant map?
                  # Usually map is generic. Need to check if Trump.
                  if card.suit == self.trump:
                       if card.rank == 'J': val = 20
                       elif card.rank == '9': val = 14
                  points += val
                  
        # Rounding logic skipped for fast sim (raw points allowed)
        # Or integer math.
        
        self.scores[winner_team] += points
        self.tricks_collected[winner_team] += 1
        
        # Clear trick
        self.played_cards_in_trick = []
        self.current_turn = winner_idx
        
        # Consumed all cards?
        if len(self.hands[0]) == 0 and len(self.hands[1]) == 0:
             self.is_finished = True
             # Last trick bonus (10 points)
             self.scores[winner_team] += 10

    def is_terminal(self):
        return self.is_finished
