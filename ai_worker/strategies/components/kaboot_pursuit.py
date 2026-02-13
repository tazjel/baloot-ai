"""Kaboot (sweep) pursuit engine for Baloot AI.

Kaboot — winning all 8 tricks — awards 44 bonus points in SUN and
doubles the round score.  This module manages the pursuit: cashing
masters early, clearing weak suits mid-game, detecting the lock-in
point, and knowing when to abort a failed sweep attempt.
"""
from __future__ import annotations
from collections import Counter

ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]


def _order(mode: str) -> list[str]:
    return ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN


def _rank_val(rank: str, mode: str) -> int:
    return _order(mode).index(rank)


def pursue_kaboot(
    hand: list,
    mode: str,
    trump_suit: str | None,
    tricks_won_by_us: int,
    tricks_played: int,
    master_cards: list[int],
    partner_is_leading: bool,
) -> dict:
    """Decide whether and how to pursue a Kaboot sweep.

    Evaluates game phase, master-card inventory, and abort conditions
    to return a status (PURSUING/LOCKED/ABORT), the best card index
    to lead, and a priority strategy label.
    """
    masters = set(master_cards)
    order = _order(mode)
    suit_counts = Counter(c.suit for c in hand)
    notes: list[str] = []

    # ── Abort checks ────────────────────────────────────────────
    if tricks_won_by_us < tricks_played:
        reason = f"lost {tricks_played - tricks_won_by_us} trick(s)"
        return _out("ABORT", None, None, reason, reason)

    if not masters and tricks_played < 5:
        reason = f"0 masters at trick {tricks_played}→unsustainable"
        return _out("ABORT", None, None, reason, reason)

    if mode == "HOKUM" and trump_suit:
        my_trumps = [i for i, c in enumerate(hand) if c.suit == trump_suit]
        if not my_trumps and tricks_played < 5:
            reason = "no trumps left in HOKUM→vulnerable"
            return _out("ABORT", None, None, reason, reason)

    # ── Partner leading → we defer ──────────────────────────────
    if partner_is_leading:
        status = "LOCKED" if tricks_played >= 6 else "PURSUING"
        notes.append(f"partner leads at trick {tricks_played}")
        return _out(status, None, None, None, "; ".join(notes))

    # ── Phase & status ──────────────────────────────────────────
    if tricks_played >= 6:
        status = "LOCKED"
        notes.append(f"trick {tricks_played}, sweep near-guaranteed")
    else:
        status = "PURSUING"

    # ── Priority selection ──────────────────────────────────────
    trump_masters = [i for i in masters if hand[i].suit == trump_suit] if trump_suit else []
    has_high_trump = any(hand[i].rank in ("J", "9") for i in trump_masters) if trump_masters else False
    longest_len = max(suit_counts.values()) if suit_counts else 0

    if mode == "HOKUM" and has_high_trump and tricks_played < 5:
        priority = "TRUMP_DRAW"
        notes.append("high trump available→draw enemy trumps")
    elif len(masters) >= 2:
        priority = "MASTER_FIRST"
        notes.append(f"{len(masters)} masters→cash guaranteed wins")
    elif masters and longest_len >= 3:
        priority = "LONG_SUIT"
        notes.append(f"1 master + {longest_len}-card suit→run length")
    elif masters:
        priority = "MASTER_FIRST"
        notes.append("few masters→cash while available")
    else:
        priority = None
        notes.append("no masters, riding momentum")

    # ── Card selection ──────────────────────────────────────────
    idx = _select_card(hand, masters, priority, mode, trump_suit, suit_counts, order)
    if idx is not None:
        c = hand[idx]
        notes.append(f"play {c.rank}{c.suit}")

    return _out(status, idx, priority, None, "; ".join(notes))


def _select_card(hand, masters, priority, mode, trump_suit, suit_counts, order):
    """Pick the best card index to lead based on priority strategy."""
    if not hand:
        return None

    if priority == "TRUMP_DRAW" and trump_suit:
        trumps = [(i, _rank_val(hand[i].rank, mode))
                  for i in range(len(hand)) if hand[i].suit == trump_suit]
        if trumps:
            return max(trumps, key=lambda t: t[1])[0]

    if priority == "MASTER_FIRST" and masters:
        # Pick master in shortest side suit → cash + move toward void
        return min(masters, key=lambda i: (suit_counts[hand[i].suit], -_rank_val(hand[i].rank, mode)))

    if priority == "LONG_SUIT":
        longest_suit = max(suit_counts, key=suit_counts.get)
        cards_in_long = [(i, _rank_val(hand[i].rank, mode))
                         for i in range(len(hand)) if hand[i].suit == longest_suit]
        if cards_in_long:
            return max(cards_in_long, key=lambda t: t[1])[0]

    # LOCKED or fallback: lead any master, else highest card
    if masters:
        return min(masters, key=lambda i: (suit_counts[hand[i].suit], -_rank_val(hand[i].rank, mode)))
    return max(range(len(hand)), key=lambda i: _rank_val(hand[i].rank, mode))


def _out(status, play_index, priority, abort_reason, reasoning):
    return {
        "status": status, "play_index": play_index,
        "priority": priority, "abort_reason": abort_reason,
        "reasoning": reasoning,
    }
