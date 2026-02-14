from enum import Enum

# ═══════════════════════════════════════════════════════════════════════
#  CANONICAL CONSTANTS — Single source of truth for the game engine.
#
#  Note: Strategy modules in ai_worker/strategies/components/ duplicate
#  these values locally to maintain module independence (no cross-imports
#  between strategy components). If you change values here, update them
#  in the strategy modules too.
#
#  Total card points per round:
#    SUN:  120 card points + 10 last trick = 130 Abnat → ÷5 = 26 GP
#    HOKUM: 152 card points + 10 last trick = 162 Abnat → ÷10 = 16 GP
#
#  Kaboot (all 8 tricks): SUN = 44 GP, HOKUM = 25 GP
#  Baloot (K+Q of trump): Always 2 GP (immune to doubling)
# ═══════════════════════════════════════════════════════════════════════

# Card universe
SUITS = ['♠', '♥', '♦', '♣']  # Spades, Hearts, Diamonds, Clubs
RANKS = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']

# Point values per rank (Abnat)
POINT_VALUES_SUN = {'7': 0, '8': 0, '9': 0, 'J': 2, 'Q': 3, 'K': 4, '10': 10, 'A': 11}
# Trump suit total: 62 Abnat (J=20, 9=14, A=11, 10=10, K=4, Q=3)
# Side suit total: 30 Abnat each (A=11, 10=10, K=4, Q=3, J=2)
POINT_VALUES_HOKUM = {'7': 0, '8': 0, 'Q': 3, 'K': 4, '10': 10, 'A': 11, '9': 14, 'J': 20}

# Rank ordering (low → high, for trick comparison)
ORDER_SUN = ['7', '8', '9', 'J', 'Q', 'K', '10', 'A']
ORDER_HOKUM = ['7', '8', 'Q', 'K', '10', 'A', '9', 'J']
ORDER_PROJECTS = ['A', 'K', 'Q', 'J', '10', '9', '8', '7']

# Scoring constants
TOTAL_ABNAT_SUN = 130     # 120 card points + 10 last trick bonus
TOTAL_ABNAT_HOKUM = 162   # 152 card points + 10 last trick bonus
TOTAL_GP_SUN = 26         # Game points from tricks in SUN
TOTAL_GP_HOKUM = 16       # Game points from tricks in HOKUM
KABOOT_GP_SUN = 44        # All 8 tricks in SUN
KABOOT_GP_HOKUM = 25      # All 8 tricks in HOKUM
BALOOT_GP = 2             # K+Q of trump (immune to doubling)
BALOOT_ABNAT = 20         # Raw Baloot value
LAST_TRICK_BONUS = 10     # Abnat bonus for winning trick 8
MATCH_TARGET = 152        # Points to win the match

class GamePhase(Enum):
    WAITING = 'WAITING'
    BIDDING = 'BIDDING'
    PLAYING = 'PLAYING'
    FINISHED = 'FINISHED'
    GAMEOVER = 'GAMEOVER'
    DOUBLING = 'DOUBLING'
    VARIANT_SELECTION = 'VARIANT_SELECTION'
    CHALLENGE = 'CHALLENGE'

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
