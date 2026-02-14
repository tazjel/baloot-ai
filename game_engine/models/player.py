from typing import TYPE_CHECKING, List
from game_engine.models.card import Card

if TYPE_CHECKING:
    from game_engine.logic.game import Game

class Player:
    def __init__(self, id, name, index, game: 'Game', avatar=None):
        self.id = id
        self.name = name
        self.index = index
        self.game = game  # Reference to game for dealer check
        self.hand: List[Card] = []
        self.captured_cards = []
        self.score = 0
        self.team = 'us' if index % 2 == 0 else 'them'
        self.action_text = ''
        self.last_reasoning = ''
        self.is_bot = False
        self.avatar = avatar if avatar else f"https://picsum.photos/id/{64 + (index % 4)}/100/100"
        
        # Director Configs (Bot Instructions)
        self.strategy = 'heuristic' # default
        self.profile = None # Explicit personality override
        self.difficulty = None # Difficulty level (EASY/MEDIUM/HARD/KHALID)

    @property
    def position(self):
        positions = ['Bottom', 'Right', 'Top', 'Left']
        return positions[self.index]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar,
            "index": self.index,
            "hand": [c.to_dict() for c in self.hand],
            "score": self.score,
            "team": self.team,
            "position": self.position,
            "isDealer": (self.index == self.game.dealer_index),
            "actionText": self.action_text,
            "lastReasoning": self.last_reasoning,
            "isBot": self.is_bot, 
            "isActive": (self.index == self.game.current_turn),
            # Expose Configs
            "strategy": getattr(self, 'strategy', 'heuristic'),
            "profile": getattr(self, 'profile', None),
            "difficulty": getattr(self, 'difficulty', None)
        }
