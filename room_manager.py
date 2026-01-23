
from game_logic import Game
import uuid

class RoomManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoomManager, cls).__new__(cls)
            cls._instance.games = {}
        return cls._instance

    def create_room(self):
        room_id = str(uuid.uuid4())[:8]  # Short ID for ease
        self.games[room_id] = Game(room_id)
        return room_id

    def get_game(self, room_id):
        return self.games.get(room_id)

    def remove_room(self, room_id):
        if room_id in self.games:
            del self.games[room_id]
            return True
        return False

# Global instance
room_manager = RoomManager()
