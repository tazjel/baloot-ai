import logging

logger = logging.getLogger(__name__)

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class CardMemory:
    def __init__(self):
        self.reset()

    def is_card_played(self, rank, suit):
        return f"{rank}{suit}" in self.played_cards

    def get_remaining_cards(self):
        remaining = []
        for s in SUITS:
            for r in RANKS:
                c_str = f"{r}{s}"
                if c_str not in self.played_cards:
                    remaining.append({'rank': r, 'suit': s})
        return remaining

    def get_remaining_in_suit(self, suit):
        return [c for c in self.get_remaining_cards() if c['suit'] == suit]

    def reset(self):
        self.played_cards = set()
        self.voids = {} # Player Ref -> Set of Suits
        self.discards = {} # Player Ref -> List of Discard Events
        self.partners_aces = set() 
        self.turn_history = [] 

    def mark_played(self, card_str):
        self.played_cards.add(card_str)

    def populate_from_state(self, game_state):
        """
        Rebuilds memory from the full game history provided in the state.
        Critically, this infers VOIDS based on player actions.
        """
        self.scan_and_populate(game_state)

    def scan_and_populate(self, game_state):
        """
        Rebuilds memory from the full game history provided in the state.
        Returns a contradiction dictionary if one is found, else None.
        """
        self.reset()
        
        history = game_state.get('currentRoundTricks', [])
        trump = game_state.get('trumpSuit')
        mode = game_state.get('gameMode')
        
        # 1. Process History (Tricks)
        for trick in history:
            led_suit = None
            proof_card = None
            if trick.get('cards'):
                 led_suit = trick['cards'][0]['suit']
                 proof_card = trick['cards'][0]

            for c_data in trick.get('cards', []):
                 player_pos = c_data.get('playedBy')
                 
                 # Check Contradiction
                 if contradiction := self.check_contradiction(player_pos, c_data['suit']):
                      return {
                          "violation_type": "REVOKE",
                          "reason": contradiction,
                          "crime_card": c_data,
                          "proof_card": proof_card
                      }
                 
                 self._process_card_update(c_data, player_pos, led_suit, trump, mode, history.index(trick))

        # 2. Process Table (Current Trick)
        table_cards = game_state.get('tableCards', [])
        led_suit = None
        proof_card = None
        if table_cards:
             led_suit = table_cards[0]['card']['suit']
             proof_card = table_cards[0]['card']

        for tc in table_cards:
             c_data = tc['card']
             player_pos = tc.get('playedBy')

             # Check Contradiction
             if contradiction := self.check_contradiction(player_pos, c_data['suit']):
                  return {
                      "violation_type": "REVOKE",
                      "reason": contradiction,
                      "crime_card": c_data,
                      "proof_card": proof_card
                  }

             self._process_card_update(c_data, player_pos, led_suit, trump, mode, -1)

        return None

    def _process_card_update(self, c_data, player_pos, led_suit, trump, mode, trick_idx):
         rank = c_data['rank']
         suit = c_data['suit']

         # Mark Played
         self.mark_played(f"{rank}{suit}")

         # Infer Voids
         if led_suit and suit != led_suit:
              self.mark_void(player_pos, led_suit)

              if player_pos not in self.discards: self.discards[player_pos] = []
              self.discards[player_pos].append({
                  'rank': rank,
                  'suit': suit,
                  'trick_idx': trick_idx
              })

              if mode == 'HOKUM' and led_suit != trump and suit != trump:
                   self.mark_void(player_pos, trump)

    def mark_void(self, player_ref, suit):
        # player_ref can be int index or string position
        if suit in SUITS:
            self.voids.setdefault(player_ref, set()).add(suit)

    def is_void(self, player_ref, suit):
        return suit in self.voids.get(player_ref, set())

    def get_remaining_trumps(self, trump_suit):
        return [c for c in self.get_remaining_in_suit(trump_suit)]

    def check_contradiction(self, player_ref, card_or_suit):
        """
        Sherlock's Magnifying Glass:
        Checks if playing 'card_obj' contradicts previously known voids.
        Returns a Reason string if contradictory, else None.
        """
        suit = card_or_suit.suit if hasattr(card_or_suit, 'suit') else card_or_suit

        # If it's a dict like {'rank': 'A', 'suit': 'S'}
        if isinstance(suit, dict):
            suit = suit.get('suit')

        if self.is_void(player_ref, suit):
             return f"Player {player_ref} played {suit} but previously showed VOID in {suit}."
        return None

    def is_master(self, rank, suit, mode, trump):
        """
        Check if a card is the highest remaining in its suit.
        """
        remaining = self.get_remaining_in_suit(suit)
        if not remaining: return True 
        
        order = []
        if mode == 'HOKUM':
            if suit == trump:
                order = ['J', '9', 'A', '10', 'K', 'Q', '8', '7']
            else:
                order = ['A', 'K', 'Q', 'J', '10', '9', '8', '7']
        else: # SUN
             order = ['A', '10', 'K', 'Q', 'J', '9', '8', '7']
             
        my_idx = -1
        try:
            my_idx = order.index(rank)
        except ValueError:
            return False 
            
        for c in remaining:
            if c['rank'] == rank: continue 
            try:
                op_idx = order.index(c['rank'])
                if op_idx < my_idx:
                    return False # Found a stronger card
            except ValueError:
                continue

        return True
