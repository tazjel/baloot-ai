"""Card tracking engine for Baloot AI.

Maintains a real-time picture of the 32-card deck by reconciling the player's
hand, completed tricks, and the current table against the full deck.  Exposes
queries for remaining cards, suit voids, high-card threats, and card mastery
that feed directly into bid/play decision logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

ORDER_SUN: list[str] = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM: list[str] = ["7", "8", "Q", "K", "10", "A", "9", "J"]

SUITS: list[str] = ["♠", "♥", "♦", "♣"]
RANKS: list[str] = ["7", "8", "9", "10", "J", "Q", "K", "A"]


@dataclass(frozen=True)
class SimpleCard:
    """Lightweight hashable card representation used internally."""
    rank: str
    suit: str


class CardTracker:
    """Tracks played cards and infers hidden information for a single round."""

    def __init__(
        self,
        my_hand: list,
        round_history: list[list[dict]],
        table_cards: list[dict],
        my_position: str,
    ) -> None:
        self._my_position = my_position
        self._full_deck: set[SimpleCard] = {
            SimpleCard(r, s) for s in SUITS for r in RANKS
        }
        self._hand: set[SimpleCard] = {
            SimpleCard(c.rank, c.suit) for c in my_hand
        }
        self._played: set[SimpleCard] = set()
        self._void: dict[str, set[str]] = {s: set() for s in SUITS}

        for trick in round_history:
            self._process_trick(trick)
        if table_cards:
            self._process_trick(table_cards, complete=False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _process_trick(self, trick: list[dict], *, complete: bool = True) -> None:
        """Ingest a trick, recording played cards and detecting voids."""
        if not trick:
            return
        led_suit = trick[0]["card"]["suit"]
        for entry in trick:
            card = SimpleCard(entry["card"]["rank"], entry["card"]["suit"])
            self._played.add(card)
            if (
                entry["playedBy"] != self._my_position
                and card.suit != led_suit
            ):
                self._void[led_suit].add(entry["playedBy"])

    @property
    def _unseen(self) -> set[SimpleCard]:
        """Cards not in hand and not yet played."""
        return self._full_deck - self._hand - self._played

    @staticmethod
    def _order(mode: str) -> list[str]:
        return ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_remaining_cards(self, suit: Optional[str] = None) -> list[SimpleCard]:
        """Return unplayed cards not in hand, optionally filtered by *suit*."""
        cards = self._unseen
        if suit is not None:
            cards = {c for c in cards if c.suit == suit}
        return sorted(cards, key=lambda c: (c.suit, RANKS.index(c.rank)))

    def get_void_players(self, suit: str) -> list[str]:
        """Return positions known to be void in *suit*."""
        return list(self._void.get(suit, set()))

    def get_remaining_high_cards(
        self, suit: str, mode: str = "SUN"
    ) -> list[SimpleCard]:
        """Return unseen cards in *suit* that outrank every card I hold in that suit."""
        order = self._order(mode)
        my_best_idx = -1
        for c in self._hand:
            if c.suit == suit:
                my_best_idx = max(my_best_idx, order.index(c.rank))

        return [
            c
            for c in self._unseen
            if c.suit == suit and order.index(c.rank) > my_best_idx
        ]

    def is_my_card_master(self, card, mode: str = "SUN") -> bool:
        """True when no unseen card in the same suit can beat *card*."""
        order = self._order(mode)
        card_idx = order.index(card.rank if isinstance(card, SimpleCard) else card.rank)
        return all(
            order.index(c.rank) <= card_idx
            for c in self._unseen
            if c.suit == (card.suit if isinstance(card, SimpleCard) else card.suit)
        )

    def count_remaining_trump(self, trump_suit: str) -> int:
        """Count unseen trump cards (held by opponents, not in my hand)."""
        return sum(1 for c in self._unseen if c.suit == trump_suit)
