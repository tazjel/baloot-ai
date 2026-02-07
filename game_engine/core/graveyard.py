"""
game_engine/core/graveyard.py — Played Card Tracker
====================================================

Maintains O(1) lookup sets of all cards played this round.
Replaces the O(N) round_history scanning in check_akka_eligibility,
forensic checks, and validation logic.

Updated automatically by Game.resolve_trick() and Game.play_card().
Reset at the start of each round via Game.reset_round_state().

Usage:
    game.graveyard.add(card)               # when card hits table
    game.graveyard.commit_trick(cards)      # when trick resolves
    "A♠" in game.graveyard                 # O(1) lookup
    game.graveyard.unplayed_higher("K", "♠", ORDER_SUN)  # for Akka
"""

from __future__ import annotations
from typing import Set, List, Dict, Optional
from game_engine.core.models import card_key


class Graveyard:
    """
    Tracks all cards played during the current round.

    Internal state:
        seen        : Set[str]                — All played card keys ("A♠", "10♥", ...)
        by_suit     : Dict[str, Set[str]]     — Played ranks grouped by suit
        trick_count : int                      — Number of completed tricks
    """

    __slots__ = ('seen', 'by_suit', 'trick_count', '_on_table')

    def __init__(self):
        self.seen: Set[str] = set()
        self.by_suit: Dict[str, Set[str]] = {}
        self.trick_count: int = 0
        self._on_table: Set[str] = set()   # Cards currently on table (not yet committed)

    # ── Core API ──────────────────────────────────────────────────────

    def add(self, card) -> str:
        """
        Register a card as played (on the table, not yet committed to a trick).
        Accepts Card objects, dicts, or nested {card: ..., playedBy: ...}.
        Returns the card key.
        """
        key = card_key(card)
        if not key:
            return ""
        self._on_table.add(key)
        self.seen.add(key)

        rank, suit = self._split_key(key)
        if suit:
            self.by_suit.setdefault(suit, set()).add(rank)

        return key

    def commit_trick(self, cards=None):
        """
        Called when a trick is resolved.
        Moves _on_table cards into permanent history.
        Optionally accepts the trick's card list for safety re-add.
        """
        if cards:
            for c in cards:
                self.add(c)
        self._on_table.clear()
        self.trick_count += 1

    def reset(self):
        """Clear everything for a new round."""
        self.seen.clear()
        self.by_suit.clear()
        self._on_table.clear()
        self.trick_count = 0

    # ── Query API ─────────────────────────────────────────────────────

    def __contains__(self, item) -> bool:
        """
        O(1) check: has this card been played?
        Accepts a card key string ("A♠") or any card object/dict.
        """
        if isinstance(item, str):
            return item in self.seen
        return card_key(item) in self.seen

    def is_played(self, rank: str, suit: str) -> bool:
        """Check if a specific rank+suit has been played."""
        return f"{rank}{suit}" in self.seen

    def played_ranks_in_suit(self, suit: str) -> Set[str]:
        """Returns set of ranks played in a given suit."""
        return self.by_suit.get(suit, set())

    def unplayed_higher(self, my_rank: str, suit: str, rank_order: List[str]) -> List[str]:
        """
        Returns list of ranks STRONGER than `my_rank` in `suit` that are NOT yet played.
        rank_order is ascending strength (index 0 = weakest).

        Used by Akka eligibility: if this returns empty -> card is Boss.
        """
        try:
            my_idx = rank_order.index(my_rank)
        except ValueError:
            return []

        result = []
        played = self.by_suit.get(suit, set())
        for i in range(my_idx + 1, len(rank_order)):
            r = rank_order[i]
            if r not in played:
                result.append(r)
        return result

    @property
    def count(self) -> int:
        """Total number of unique cards seen (played + on table)."""
        return len(self.seen)

    # ── Internal ──────────────────────────────────────────────────────

    @staticmethod
    def _split_key(key: str):
        """
        Split a card key like "10♠" into (rank, suit).
        Suit is always the last character (Unicode symbols like ♠♥♦♣).
        """
        if not key or len(key) < 2:
            return key, ""
        return key[:-1], key[-1]

    def __repr__(self):
        return f"Graveyard(played={len(self.seen)}, tricks={self.trick_count})"
