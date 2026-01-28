import time
import random

class Card:
    def __init__(self, suit, rank, id=None):
        self.suit = suit
        self.rank = rank
        # Optimization: Only generate ID if strictly needed
        self.id = id if id else f"{rank}{suit}"

    def to_dict(self):
        return {"suit": self.suit, "rank": self.rank, "id": self.id, "value": 0}

    def __repr__(self):
        return f"{self.rank}{self.suit}"
