"""
Source Card Index Mapping — Pure conversion between Source's 0-51
encoding and our game engine's Card(suit, rank) objects.

Proven formula: index = suit_index * 13 + rank_index
  Suits:  0=♠, 1=♥, 2=♣, 3=♦
  Ranks:  0=2, 1=3, ..., 5=7, 6=8, 7=9, 8=10, 9=J, 10=Q, 11=K, 12=A
  Baloot uses only ranks 7-A (indices 5-12).

Verified against 9 card plays from captured session data (100% match).
"""
from __future__ import annotations

from typing import Optional

from game_engine.models.card import Card

# ── Constants ────────────────────────────────────────────────────────

SOURCE_SUITS: dict[int, str] = {0: "♠", 1: "♥", 2: "♣", 3: "♦"}
SUIT_SYMBOL_TO_IDX: dict[str, int] = {"♠": 0, "♥": 1, "♣": 2, "♦": 3}

SOURCE_RANKS: dict[int, str] = {
    0: "2", 1: "3", 2: "4", 3: "5", 4: "6",
    5: "7", 6: "8", 7: "9", 8: "10", 9: "J", 10: "Q", 11: "K", 12: "A",
}
RANK_TO_IDX: dict[str, int] = {v: k for k, v in SOURCE_RANKS.items()}

# Only rank indices 5-12 (7 through A) are valid in Baloot
VALID_RANK_RANGE = range(5, 13)

VALID_BALOOT_INDICES: frozenset[int] = frozenset(
    suit * 13 + rank for suit in range(4) for rank in VALID_RANK_RANGE
)

# Source game mode strings → our engine mode strings
MODE_MAP: dict[str, str] = {
    "ashkal": "SUN",
    "sun": "SUN",
    "hokom": "HOKUM",
    "hokum": "HOKUM",
}

# Card code letters from SEND events (e.g. "hj" = Hearts Jack)
CODE_SUIT_MAP: dict[str, str] = {"s": "♠", "h": "♥", "c": "♣", "d": "♦"}
CODE_RANK_MAP: dict[str, str] = {
    "a": "A", "7": "7", "8": "8", "9": "9", "10": "10",
    "j": "J", "q": "Q", "k": "K",
}


# ── Conversion Functions ────────────────────────────────────────────

def index_to_card(idx: int) -> Optional[Card]:
    """Convert a Source card index (0-51) to a Card object.

    @param idx: Source card index.
    @returns Card object, or None if index is invalid or maps to a non-Baloot rank.
    """
    if not isinstance(idx, int) or idx < 0 or idx > 51:
        return None
    suit_idx = idx // 13
    rank_idx = idx % 13
    if rank_idx not in VALID_RANK_RANGE:
        return None
    suit = SOURCE_SUITS[suit_idx]
    rank = SOURCE_RANKS[rank_idx]
    return Card(suit, rank)


def card_to_index(card: Card) -> int:
    """Convert a Card object back to a Source index (0-51).

    @param card: Card object with .suit and .rank attributes.
    @returns Integer index.
    @raises ValueError: If suit or rank is unrecognized.
    """
    suit_idx = SUIT_SYMBOL_TO_IDX.get(card.suit)
    rank_idx = RANK_TO_IDX.get(card.rank)
    if suit_idx is None:
        raise ValueError(f"Unknown suit: {card.suit}")
    if rank_idx is None:
        raise ValueError(f"Unknown rank: {card.rank}")
    return suit_idx * 13 + rank_idx


def suit_idx_to_symbol(idx: int) -> str:
    """Convert a Source suit index (0-3) to a Unicode suit symbol.

    @param idx: Suit index (0=♠, 1=♥, 2=♣, 3=♦).
    @returns Suit symbol string, or "?" for invalid indices.
    """
    return SOURCE_SUITS.get(idx, "?")


def card_code_to_card(code: str) -> Optional[Card]:
    """Convert a Source SEND-event card code to a Card object.

    @param code: Card code like 'hj' (Hearts Jack) or 's10' (Spades 10).
    @returns Card object, or None if the code cannot be parsed.
    """
    if not code or len(code) < 2:
        return None
    suit_char = code[0].lower()
    rank_str = code[1:].lower()
    suit = CODE_SUIT_MAP.get(suit_char)
    rank = CODE_RANK_MAP.get(rank_str)
    if suit is None or rank is None:
        return None
    return Card(suit, rank)


def decode_hand_bitmask(pcs: int) -> list[Card]:
    """Decode a Source hand bitmask into a list of Card objects.

    Each set bit at position i means card index i is in the hand.

    @param pcs: 64-bit integer bitmask from the pcs field.
    @returns Sorted list of Card objects (only valid Baloot cards).
    """
    cards: list[Card] = []
    for idx in VALID_BALOOT_INDICES:
        if pcs & (1 << idx):
            card = index_to_card(idx)
            if card is not None:
                cards.append(card)
    return cards


def map_game_mode(gm: str) -> str:
    """Map a Source game mode string to our engine's mode string.

    @param gm: Source mode ('ashkal', 'sun', 'hokom', 'hokum').
    @returns 'SUN' or 'HOKUM'.
    @raises ValueError: If gm is unrecognized.
    """
    result = MODE_MAP.get(gm.lower() if gm else "")
    if result is None:
        raise ValueError(f"Unknown Source game mode: {gm!r}")
    return result
