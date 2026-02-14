"""Bidding inference engine for Baloot AI play phase.

Extracts card-holding predictions from the bidding history to inform
play decisions. Each bid action reveals information about a player's hand:

- HOKUM bid in suit X → likely holds J/9 of X, possibly A/10
- SUN bid → strong balanced hand, multiple Aces and Tens
- PASS → weak in floor suit (R1), weak overall (R2)
- ASHKAL → 4-of-a-kind project or dominant Sun hand
- Floor card pickup → bidder gets that specific card

Returns per-player predictions with confidence levels.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

POSITIONS = ["Bottom", "Right", "Top", "Left"]
from ai_worker.strategies.constants import ALL_SUITS


def _partner_of(pos: str) -> str:
    idx = POSITIONS.index(pos) if pos in POSITIONS else 0
    return POSITIONS[(idx + 2) % 4]


def infer_from_bids(
    my_position: str,
    bid_history: list[dict],
    floor_card: dict | None = None,
    bidding_round: int = 1,
) -> dict:
    """Analyze bid history to predict card holdings for all players.

    Returns a dict with:
    - players: {position: {likely_trumps: [rank,...], likely_aces: int,
                            weak_suits: [suit,...], strong_suits: [suit,...],
                            bid_action: str, confidence: float}}
    - declarer_position: str or None
    - declarer_trump: str or None
    - avoid_suits: [suit,...] — suits where declarer is strong
    - target_suits: [suit,...] — suits where declarer is weak
    """
    partner_pos = _partner_of(my_position)
    players: dict[str, dict] = {p: {
        'likely_trumps': [],
        'likely_aces': 0,
        'weak_suits': [],
        'strong_suits': [],
        'bid_action': 'UNKNOWN',
        'confidence': 0.0,
    } for p in POSITIONS if p != my_position}

    declarer_pos = None
    declarer_trump = None
    floor_suit = None
    floor_rank = None

    if floor_card:
        floor_suit = floor_card.get('suit') if isinstance(floor_card, dict) else getattr(floor_card, 'suit', None)
        floor_rank = floor_card.get('rank') if isinstance(floor_card, dict) else getattr(floor_card, 'rank', None)

    for entry in bid_history or []:
        player = entry.get('player', entry.get('bidder', ''))
        action = entry.get('action', entry.get('type', 'PASS'))
        suit = entry.get('suit')

        if player == my_position or player not in players:
            continue

        profile = players[player]
        profile['bid_action'] = action

        if action == 'HOKUM' and suit:
            # Player bid HOKUM in suit → they likely hold top trumps
            declarer_pos = player
            declarer_trump = suit
            profile['strong_suits'].append(suit)
            profile['confidence'] = 0.7

            # Infer trump holdings: bidder almost certainly has J or 9
            profile['likely_trumps'] = ['J', '9']  # Most likely holdings
            # If floor card is in their trump suit, they get it
            if floor_suit == suit and floor_rank:
                profile['likely_trumps'].append(floor_rank)

            # Weak in other suits (committed resources to trump)
            for s in ALL_SUITS:
                if s != suit:
                    profile['weak_suits'].append(s)

        elif action == 'SUN':
            declarer_pos = player
            declarer_trump = None
            profile['likely_aces'] = 2  # SUN bidder likely has 2+ Aces
            profile['confidence'] = 0.6
            # Strong in all suits (balanced)
            profile['strong_suits'] = list(ALL_SUITS)

        elif action == 'PASS':
            profile['confidence'] = 0.3
            # Pass in R1 → weak in floor suit
            if floor_suit:
                profile['weak_suits'].append(floor_suit)
            # Pass in R2 → weak overall
            if bidding_round >= 2:
                profile['likely_aces'] = 0

        elif action == 'ASHKAL':
            declarer_pos = player
            profile['likely_aces'] = 3  # Ashkal = strong project
            profile['confidence'] = 0.8
            profile['strong_suits'] = list(ALL_SUITS)

    # Build tactical recommendations
    avoid_suits = []  # Suits where declarer is strong (don't lead)
    target_suits = []  # Suits where declarer is weak (attack)

    if declarer_pos and declarer_pos != partner_pos:
        decl = players.get(declarer_pos, {})
        avoid_suits = list(set(decl.get('strong_suits', [])))
        target_suits = list(set(decl.get('weak_suits', [])))

    return {
        'players': players,
        'declarer_position': declarer_pos,
        'declarer_trump': declarer_trump,
        'avoid_suits': avoid_suits,
        'target_suits': target_suits,
    }
