import random
from game_engine.models.card import Card
from game_engine.models.constants import SUITS, RANKS

class Deck:
    def __init__(self):
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
        self.shuffle()
    
    def shuffle(self):
        random.shuffle(self.cards)
    
    def deal(self, num):
        if num > len(self.cards):
            return self.cards  # Return what's left
        dealt = self.cards[:num]
        self.cards = self.cards[num:]
        return dealt
