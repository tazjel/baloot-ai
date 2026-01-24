import logging

logger = logging.getLogger(__name__)

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class CardMemory:
    def __init__(self):
        self.reset()

    def reset(self):
        self.played_cards = set()
        self.voids = {0: set(), 1: set(), 2: set(), 3: set()} # Player Index -> Set of Suits
        self.partners_aces = set() # Suits where partner showed an Ace
        self.turn_history = [] # List of (player_idx, card_str)

    def mark_played(self, card_str):
        self.played_cards.add(card_str)

    def mark_void(self, player_idx, suit):
        if suit in SUITS:
            self.voids[player_idx].add(suit)
            # logger.info(f"Memory: Player {player_idx} is VOID in {suit}")

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

    def is_master(self, rank, suit, mode, trump):
        """
        Check if a card is the highest remaining in its suit.
        """
        remaining = self.get_remaining_in_suit(suit)
        if not remaining: return True # Should not happen if I hold the card
        
        # Filter out the card itself if it's in remaining (it usually isn't if I hold it, 
        # but let's be safe: we are checking if *my* card is master against *others*)
        
        # Determine strict order for this suit
        # HOKUM Trump: J 9 A 10 K Q 8 7
        # HOKUM Non-Trump: A K Q J 10 9 8 7
        # SUN: A 10 K Q J 9 8 7
        
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
            return False # Invalid rank?
            
        # Check if any OTHER remaining card has a lower index (stronger)
        for c in remaining:
            if c['rank'] == rank: continue # Skip myself
            
            try:
                op_idx = order.index(c['rank'])
                if op_idx < my_idx:
                    return False # Found a stronger card
            except ValueError:
                continue

        return True
