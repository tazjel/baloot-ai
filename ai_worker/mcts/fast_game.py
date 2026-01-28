
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
        raw_hand = self.hands[self.current_turn]
        if not raw_hand: return []
        
        # Paranoid Rebuild: Create a guaranteed clean list of Card Objects
        safe_hand = []
        for c in raw_hand:
             if isinstance(c, dict):
                  try:
                       safe_hand.append(Card(c['suit'], c['rank']))
                  except:
                       pass # Discard broken dicts
             elif hasattr(c, 'suit') and hasattr(c, 'rank'):
                  safe_hand.append(c)
             else:
                  # Discard None, strings, ints, etc.
                  pass
                  
        # Update self.hands check? No, just use safe_hand for this validation step.
        # But if we don't update self.hands, then apply_move might crash later?
        # Yes, we should update strict.
        self.hands[self.current_turn] = safe_hand
        hand = safe_hand
        
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
             try:
                 # Double check card object integrity
                 _ = card.suit 
                 
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
             except Exception as e:
                 # Silent fail for single card? Or print?
                 # If we rebuild hand safely, this shouldn't happen.
                 # Taking valid cards only.
                 pass
                 
        return legal_indices
                 
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

    def play_greedy(self):
        """
        Simulates the game to completion using a greedy policy.
        Used for PIMC rollouts to estimate hand strength without MCTS overhead.
        """
        while not self.is_finished:
            legal = self.get_legal_moves()
            if not legal: break
            
            # Policy:
            # 1. If we can win the trick (and it's currently ours or empty), throw big.
            # 2. If partner winning, throw points (10/K/Q or A if Sun).
            # 3. Else throw lowest garbage.
            
            # SIMPLIFICATION: Random for now, but strict valid.
            # Ideally: Pick highest strength card that wins?
            
            # Let's map card -> strength
            best_move = legal[0]
            # Simple heuristic: Just play random. 
            # Given we average over 20 worlds, random rollout (light MCTS) is "okay" for raw potential check
            # BUT Double Dummy suggests we use MINIMAX. That is too slow.
            
            # Improved Greedy Policy
            # 1. Sort legal moves by strength
            # We need to consider:
            # - Am I leading?
            # - Is partner winning?
            
            # Simple "High Card" logic:
            # If leading: Play highest card (in SUN: Ace/10).
            # If following:
            #   - Can I beat current winner? If yes, play highest winner? No, play lowest winner (finesse) or highest (secure)? 
            #   - Greedy = Secure. Play highest winner.
            #   - If can't beat, throw lowest.
            #   - If partner winning, throw points (A/10/K) or lowest garbage? 
            #     - Usually throw points if 100% partner win. 
            #     - For simplistic PIMC: Just throw high points to bank them.
            
            current_hand = self.hands[self.current_turn]
            
            # Helper to rate card strength
            def get_card_strength(c: Card, lead_suit=None):
                # Using constants indices
                try:
                    is_trump = (c.suit == self.trump)
                    if self.mode == 'HOKUM':
                        if is_trump:
                            return 100 + ORDER_HOKUM.index(c.rank)
                        if lead_suit and c.suit == lead_suit:
                            return ORDER_SUN.index(c.rank)
                    else: # SUN
                        if lead_suit and c.suit == lead_suit:
                            return ORDER_SUN.index(c.rank)
                except:
                    pass
                return -1

            # Determine context
            is_leading = (len(self.played_cards_in_trick) == 0)
            lead_suit = self.played_cards_in_trick[0][1].suit if not is_leading else None
            
            legal_indices_with_obj = [(idx, current_hand[idx]) for idx in legal]
            
            best_choice = legal[0] # Default
            
            if is_leading:
                # Play highest strength card generally (e.g. Ace)
                # Sort by strength descending
                # For SUN: A=7, 10=6...
                # For HOKUM: J=7, 9=6...
                
                # We need a generic sort. 
                # Just use ORDER constants order.
                ordered_moves = sorted(legal_indices_with_obj, key=lambda x: get_card_strength(x[1], x[1].suit), reverse=True)
                best_choice = ordered_moves[0][0]
            else:
                # Following
                # Check who is winning
                # ... resolving trick logic is duplicated here ...
                # To be fast, let's just use SIMPLE heuristic:
                # Try to win.
                
                # Filter winners
                # We don't know who is winning easily without re-calculating everything.
                # Just play Highest Legal Card.
                # This approximates "Trying to win".
                ordered_moves = sorted(legal_indices_with_obj, key=lambda x: get_card_strength(x[1], lead_suit), reverse=True)
                best_choice = ordered_moves[0][0]

            self.apply_move(best_choice)
