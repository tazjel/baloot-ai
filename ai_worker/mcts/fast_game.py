
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
        self.teams = {0: 'us', 1: 'them', 2: 'us', 3: 'them'}  # Standard Baloot team assignment
        
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
                  except (KeyError, TypeError):
                      pass  # Discard broken card dicts
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
        card_debugs = []
        for _, card in self.played_cards_in_trick:
             if self.mode == 'SUN':
                  points += POINT_VALUES_SUN.get(card.rank, 0)
             else:
                  val = POINT_VALUES_HOKUM.get(card.rank, 0)
                  if card.suit == self.trump:
                       if card.rank == 'J': val = 20
                       elif card.rank == '9': val = 14
                  points += val
             card_debugs.append(f"{card}({points})")
                  
        # print(f"Trick Resolved: Mode {self.mode}. Cards: {card_debugs}. Winner: P{winner_idx} ({winner_team}). Points: {points}")
        
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
        Simulates the game to completion using a smart heuristic policy.
        Used for PIMC rollouts to estimate hand strength without MCTS overhead.
        """
        while not self.is_finished:
            legal = self.get_legal_moves()
            if not legal: break
            
            current_hand = self.hands[self.current_turn]
            my_team = self.teams[self.current_turn]
            partner_idx = (self.current_turn + 2) % 4
            is_leading = (len(self.played_cards_in_trick) == 0)
            
            best_choice = legal[0]  # Default fallback
            
            if is_leading:
                best_choice = self._greedy_lead(legal, current_hand)
            else:
                best_choice = self._greedy_follow(legal, current_hand, my_team, partner_idx)

            self.apply_move(best_choice)

    def _greedy_lead(self, legal, hand):
        """Smart lead: play masters first, then high cards, avoid naked honors."""
        best_idx = legal[0]
        best_score = -100
        
        for idx in legal:
            card = hand[idx]
            score = 0
            
            is_trump = (self.mode == 'HOKUM' and card.suit == self.trump)
            
            # Master card detection (simplified for speed)
            if is_trump:
                if card.rank == 'J': score += 50
                elif card.rank == '9': score += 45
                elif card.rank == 'A': score += 40
            else:
                if card.rank == 'A': score += 40
                elif card.rank == '10': score += 30
                elif card.rank == 'K': score += 20
            
            # Prefer suits where we have length (safer leads)
            suit_count = sum(1 for c in hand if c.suit == card.suit)
            score += suit_count * 2
            
            # Penalize naked honors (K without A, Q without K/A)
            if card.rank == 'K' and not any(c.rank == 'A' and c.suit == card.suit for c in hand):
                score -= 15
            if card.rank == 'Q' and not any(c.rank in ['A', 'K'] and c.suit == card.suit for c in hand):
                score -= 10
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        return best_idx

    def _greedy_follow(self, legal, hand, my_team, partner_idx):
        """Smart follow: finesse, feed partner, trump wisely, duck cheap."""
        lead_suit = self.played_cards_in_trick[0][1].suit
        
        # Find who is currently winning the trick
        best_strength = -1
        winner_player_idx = self.played_cards_in_trick[0][0]
        for p_idx, card in self.played_cards_in_trick:
            strength = self._card_strength(card, lead_suit)
            if strength > best_strength:
                best_strength = strength
                winner_player_idx = p_idx
        
        is_partner_winning = (winner_player_idx == partner_idx)
        
        # Classify moves
        follows = [i for i in legal if hand[i].suit == lead_suit]
        trumps = [i for i in legal if self.mode == 'HOKUM' and hand[i].suit == self.trump and hand[i].suit != lead_suit]
        
        if follows:
            # Can follow suit
            winners = [i for i in follows if self._card_strength(hand[i], lead_suit) > best_strength]
            
            if is_partner_winning:
                # Partner winning → feed points (highest point card that doesn't overtake)
                safe_feeds = [i for i in follows if self._card_strength(hand[i], lead_suit) <= best_strength]
                if safe_feeds:
                    return self._highest_points(safe_feeds, hand)
                # All cards overtake partner — play lowest winner
                return self._lowest_strength(follows, hand, lead_suit)
            else:
                # Enemy winning → try to win with lowest winning card (finesse)
                if winners:
                    return self._lowest_strength(winners, hand, lead_suit)
                # Can't win → play lowest (duck)
                return self._lowest_strength(follows, hand, lead_suit)
        else:
            # Void in lead suit
            if is_partner_winning:
                # Partner winning → discard lowest value card
                return self._lowest_points(legal, hand)
            elif trumps:
                # Can trump → use lowest trump
                return self._lowest_strength(trumps, hand, lead_suit)
            else:
                # No trumps, not following → discard lowest
                return self._lowest_points(legal, hand)

    def _card_strength(self, card, lead_suit):
        """Returns comparable strength value for a card in trick context."""
        try:
            if self.mode == 'HOKUM':
                if card.suit == self.trump:
                    return 100 + ORDER_HOKUM.index(card.rank)
                elif card.suit == lead_suit:
                    return ORDER_SUN.index(card.rank)
            else:  # SUN
                if card.suit == lead_suit:
                    return ORDER_SUN.index(card.rank)
        except (ValueError, AttributeError):
            pass
        return -1

    def _get_trick_winner_idx(self):
        """Returns the player index currently winning the trick."""
        if not self.played_cards_in_trick:
            return self.current_turn
        lead_suit = self.played_cards_in_trick[0][1].suit
        best_idx = 0
        best_strength = -1
        for i, (p_idx, card) in enumerate(self.played_cards_in_trick):
            s = self._card_strength(card, lead_suit)
            if s > best_strength:
                best_strength = s
                best_idx = i
        return self.played_cards_in_trick[best_idx][0]

    def _highest_points(self, indices, hand):
        """Select card with highest point value (for feeding partner)."""
        point_map = POINT_VALUES_HOKUM if self.mode == 'HOKUM' else POINT_VALUES_SUN
        best = indices[0]
        best_pts = -1
        for i in indices:
            pts = point_map.get(hand[i].rank, 0)
            if pts > best_pts:
                best_pts = pts
                best = i
        return best

    def _lowest_points(self, indices, hand):
        """Select card with lowest point value (for discarding)."""
        point_map = POINT_VALUES_HOKUM if self.mode == 'HOKUM' else POINT_VALUES_SUN
        best = indices[0]
        best_pts = 999
        for i in indices:
            pts = point_map.get(hand[i].rank, 0)
            # Protect trumps when discarding
            if self.mode == 'HOKUM' and hand[i].suit == self.trump:
                pts += 50
            if pts < best_pts:
                best_pts = pts
                best = i
        return best

    def _lowest_strength(self, indices, hand, lead_suit):
        """Select card with lowest strength (finessing / economy)."""
        best = indices[0]
        best_s = 999
        for i in indices:
            s = self._card_strength(hand[i], lead_suit)
            if s < best_s:
                best_s = s
                best = i
        return best
