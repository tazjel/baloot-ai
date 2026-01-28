from enum import Enum

class SignalType(Enum):
    ENCOURAGE = "ENCOURAGE"    # "Play this suit!" (Call)
    DISCOURAGE = "DISCOURAGE"  # "Don't play this suit" (Trash)
    PREFER_OPPOSITE_COLOR = "PREFER_OPPOSITE_COLOR" # "Play opposite color" (Suit Preference)
    NONE = "NONE"              # No signal intended

class SignalStrength(Enum):
    HIGH = 3   # Explicit signal (e.g., discarding a 10)
    MEDIUM = 2 # Likely signal (e.g., discarding a King)
    LOW = 1    # Weak signal (e.g., discarding a 9)
