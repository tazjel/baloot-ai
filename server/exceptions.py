"""
server/exceptions.py — Domain-specific exception hierarchy.

All custom exceptions inherit from BalootError, enabling
granular error handling throughout the server layer.
"""


class BalootError(Exception):
    """Base exception for all Baloot server errors."""
    pass


class GameNotFoundError(BalootError):
    """Raised when a game/room cannot be found in Redis or local cache."""
    def __init__(self, room_id: str):
        self.room_id = room_id
        super().__init__(f"Game not found: {room_id}")


class InvalidActionError(BalootError):
    """Raised when a player attempts an invalid game action."""
    def __init__(self, action: str, reason: str = ""):
        self.action = action
        self.reason = reason
        super().__init__(f"Invalid action '{action}': {reason}")


class SerializationError(BalootError):
    """Raised when game state serialization/deserialization fails."""
    pass


class RedisPersistenceError(BalootError):
    """Raised when Redis read/write operations fail."""
    def __init__(self, operation: str, room_id: str, cause: Exception | None = None):
        self.operation = operation
        self.room_id = room_id
        self.cause = cause
        super().__init__(f"Redis {operation} failed for room {room_id}: {cause}")


class BroadcastError(BalootError):
    """Raised when game state broadcast to clients fails."""
    pass
