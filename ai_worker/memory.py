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
        
        TODO: Upgrade to "Mind's Eye" Probabilistic Memory.
        Current implementation uses binary voids (Has Suit / Void).
        Future: self.hand_distributions = {player: {suit: prob}}
        """
        self.reset()
        
        # 1. Mark Table Cards as Played
        for tc in game_state.get('tableCards', []):
             c = tc['card']
             self.mark_played(f"{c['rank']}{c['suit']}")
             
        # 2. Process Round History (Tricks)
        # Assuming round_history / currentRoundTricks structure:
        # [{'winner': 'Bottom', 'cards': [{'suit': 'S', 'rank': 'A', 'playedBy': 'Bottom'}, ...]}, ...]
        
        history = game_state.get('currentRoundTricks', [])
        # Also check 'pastRoundResults' for previous rounds if we wanted long-term memory?
        # No, Baloot memory is per-round (cards are reshuffled).
        
        trump = game_state.get('trumpSuit')
        mode = game_state.get('gameMode')
        
        for trick in history:
            led_suit = None
            if trick.get('cards'):
                 led_suit = trick['cards'][0]['suit']
                 
            for c_data in trick.get('cards', []):
                 rank = c_data['rank']
                 suit = c_data['suit']
                 player_pos = c_data.get('playedBy') # Position 'Bottom', etc.
                 
                 # Mark Played
                 self.mark_played(f"{rank}{suit}")
                 
                 # Infer Voids
                 if led_suit and suit != led_suit:
                      # Player failed to follow suit -> VOID in led_suit
                      self.mark_void(player_pos, led_suit)
                      
                      # Track Discard for Signaling History
                      # structure: { player_pos: [ { card: {rank, suit}, trick_idx: i } ] }
                      if player_pos not in self.discards: self.discards[player_pos] = []
                      self.discards[player_pos].append({
                          'rank': rank,
                          'suit': suit,
                          'trick_idx': history.index(trick) # Naive index
                      })
                      
                      # Hokum Constraint: If failed to follow suit, AND failed to Trump (when enemy winning?)
                      # In Baloot, you MUST play trump if you can't follow lead.
                      # So if they played non-trump on a non-trump lead... they are void in Trump too?
                      # Only if: Mode is Hokum, Lead was Non-Trump, and they played Non-Trump.
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
