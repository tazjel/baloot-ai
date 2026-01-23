from enum import Enum

# Constants
SUITS = ['♠', '♥', '♦', '♣']  # Spades, Hearts, Diamonds, Clubs
RANKS = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']

# Scores & Orders
POINT_VALUES_SUN = {'7': 0, '8': 0, '9': 0, 'J': 2, 'Q': 3, 'K': 4, '10': 10, 'A': 11}
POINT_VALUES_HOKUM = {'7': 0, '8': 0, 'Q': 3, 'K': 4, '10': 10, 'A': 11, '9': 14, 'J': 20}
ORDER_SUN = ['7', '8', '9', 'J', 'Q', 'K', '10', 'A']
ORDER_HOKUM = ['7', '8', 'Q', 'K', '10', 'A', '9', 'J']
ORDER_PROJECTS = ['A', 'K', 'Q', 'J', '10', '9', '8', '7']

class GamePhase(Enum):
    WAITING = 'WAITING'
    BIDDING = 'BIDDING'
    PLAYING = 'PLAYING'
    FINISHED = 'FINISHED'
    GAMEOVER = 'GAMEOVER'
    DOUBLING = 'DOUBLING'
    VARIANT_SELECTION = 'VARIANT_SELECTION'

class BiddingPhase(Enum):
    ROUND_1 = "ROUND_1"
    GABLAK_WINDOW = "GABLAK_WINDOW" # Interruption window
    ROUND_2 = "ROUND_2"
    DOUBLING = "DOUBLING"
    VARIANT_SELECTION = "VARIANT_SELECTION" # Buyer chooses Open/Closed
    FINISHED = "FINISHED"

class BidType(Enum):
    PASS = "PASS"
    HOKUM = "HOKUM"
    SUN = "SUN"
    ASHKAL = "ASHKAL" # Special Sun initiated by partner
    # Doubling Types
    DOUBLE = "DOUBLE"   # Dobl
    TRIPLE = "TRIPLE"   # Khamsin
    FOUR = "FOUR"       # Raba'a
    GAHWA = "GAHWA"     # Match Win
    KAWESH = "KAWESH"   # Redeal request
