"""
Player Manager - Manages player seating and queries
===================================================

Extracts player management logic from the main Game class.
"""

from typing import List, Optional
from game_engine.models.player import Player

class PlayerManager:
    def __init__(self, game):
        self.game = game

    def add_player(self, id: str, name: str, avatar: Optional[str] = None) -> Optional[Player]:
        """
        Add a player to the game or update existing player.
        Returns the Player object or None if game is full.
        """
        # Check if player already exists
        for p in self.game.players:
            if p.id == id:
                p.name = name
                if avatar:
                    p.avatar = avatar
                return p

        # Check for max players
        if len(self.game.players) >= 4:
            return None

        # Create new player
        p = Player(id, name, len(self.game.players), self.game, avatar=avatar)
        self.game.players.append(p)
        return p

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Find player by ID."""
        for p in self.game.players:
            if p.id == player_id:
                return p
        return None

    def get_player_by_index(self, index: int) -> Optional[Player]:
        """Find player by seat index (0-3)."""
        if 0 <= index < len(self.game.players):
            return self.game.players[index]
        return None

    def get_player_by_position(self, position: str) -> Optional[Player]:
        """Find player by position (Bottom, Right, Top, Left)."""
        for p in self.game.players:
            if p.position == position:
                return p
        return None
