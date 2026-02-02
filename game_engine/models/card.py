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

    @classmethod
    def from_dict(cls, data):
        if not data: return None
        return cls(data.get('suit'), data.get('rank'), id=data.get('id'))

    def __repr__(self):
        return f"{self.rank}{self.suit}"
