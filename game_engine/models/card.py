import time
import random

class Card:
    def __init__(self, suit, rank, id=None):
        self.suit = suit
        self.rank = rank
        self.id = id if id else f"{rank}{suit}-{int(time.time()*1000)}{random.randint(0,999)}"

    def to_dict(self):
        return {"suit": self.suit, "rank": self.rank, "id": self.id, "value": 0}

    def __repr__(self):
        return f"{self.rank}{self.suit}"
