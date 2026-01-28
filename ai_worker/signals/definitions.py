from enum import Enum

class SignalType(Enum):
    ENCOURAGE = "ENCOURAGE"    # "Play this suit!" (Call)
    DISCOURAGE = "DISCOURAGE"  # "Don't play this suit" (Trash)
    PREFER_OPPOSITE_COLOR = "PREFER_OPPOSITE_COLOR" # "Play opposite color" (Suit Preference)
    NEGATIVE_DISCARD = "NEGATIVE_DISCARD" # "I definitely don't want this suit" (Tahreeb)
    URGENT_CALL = "URGENT_CALL" # "Play this suit NOW!" (Barqiya)
    PREFER_SAME_COLOR = "PREFER_SAME_COLOR" # "Play the *other* suit of the same color"
    CONFIRMED_POSITIVE = "CONFIRMED_POSITIVE" # "Low to High" sequence (Strong Encourage)
    CONFIRMED_NEGATIVE = "CONFIRMED_NEGATIVE" # "High to Low" sequence (Absolute Rejection)
    NONE = "NONE"              # No signal intended

class SignalStrength(Enum):
    HIGH = 3   # Explicit signal (e.g., discarding a 10)
    MEDIUM = 2 # Likely signal (e.g., discarding a King)
    LOW = 1    # Weak signal (e.g., discarding a 9)
