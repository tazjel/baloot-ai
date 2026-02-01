from enum import Enum
from typing import List

class Suit(str, Enum):
    SPADES = '♠'
    HEARTS = '♥'
    DIAMONDS = '♦'
    CLUBS = '♣'

class Rank(str, Enum):
    SEVEN = '7'
    EIGHT = '8'
    NINE = '9'
    TEN = '10'
    JACK = 'J'
    QUEEN = 'Q'
    KING = 'K'
    ACE = 'A'

class GamePhase(str, Enum):
    WAITING = 'WAITING'
    BIDDING = 'BIDDING'
    PLAYING = 'PLAYING'
    FINISHED = 'FINISHED'
    GAMEOVER = 'GAMEOVER'
    DOUBLING = 'DOUBLING'
    VARIANT_SELECTION = 'VARIANT_SELECTION'
    CHALLENGE = 'CHALLENGE'

class BiddingPhase(str, Enum):
    ROUND_1 = "ROUND_1"
    GABLAK_WINDOW = "GABLAK_WINDOW"
    ROUND_2 = "ROUND_2"
    DOUBLING = "DOUBLING"
    VARIANT_SELECTION = "VARIANT_SELECTION"
    FINISHED = "FINISHED"

class BidType(str, Enum):
    PASS = "PASS"
    HOKUM = "HOKUM"
    SUN = "SUN"
    ASHKAL = "ASHKAL"
    DOUBLE = "DOUBLE"
    TRIPLE = "TRIPLE"
    FOUR = "FOUR"
    GAHWA = "GAHWA"
    KAWESH = "KAWESH"

class Team(str, Enum):
    US = 'us'
    THEM = 'them'
