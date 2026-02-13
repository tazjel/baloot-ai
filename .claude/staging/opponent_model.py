"""Opponent modelling for Baloot AI.

Analyses bid history and trick play to build threat profiles for both
opponents — tracking voids, trump holdings, suit strength, play style,
and composite danger level.  Mirrors ``partner_read.py`` but for enemies.
"""
from __future__ import annotations
from collections import defaultdict

POSITIONS = ["Bottom", "Right", "Top", "Left"]
ALL_SUITS = ["♠", "♥", "♦", "♣"]
_HIGH = {"A", "10", "K"}
_LOW = {"7", "8"}
_PTS = {"SUN": {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2},
        "HOKUM": {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3}}


def _partner_of(pos: str) -> str:
    return POSITIONS[(POSITIONS.index(pos) + 2) % 4]


def _opponents_of(pos: str) -> list[str]:
    partner = _partner_of(pos)
    return [p for p in POSITIONS if p != pos and p != partner]


def model_opponents(
    my_position: str,
    bid_history: list[dict],
    trick_history: list[dict],
    mode: str,
    trump_suit: str | None = None,
) -> dict:
    """Build threat profiles for both opponents.

    Returns per-opponent void/strength/style data plus safe/avoid suit
    lists and a combined danger score.
    """
    opps = _opponents_of(my_position)
    # Per-opponent accumulators
    strength: dict[str, dict[str, float]] = {p: {s: 0.0 for s in ALL_SUITS} for p in opps}
    voids: dict[str, set[str]] = {p: set() for p in opps}
    trump_count: dict[str, int] = {p: 0 for p in opps}
    high_trump: dict[str, bool] = {p: False for p in opps}
    agg_plays: dict[str, int] = {p: 0 for p in opps}
    total_plays: dict[str, int] = {p: 0 for p in opps}

    # --- Bid inference ---
    for entry in bid_history or []:
        player = entry.get("player", "")
        if player not in opps:
            continue
        action = entry.get("action", "PASS")
        if action == "HOKUM":
            s = entry.get("suit", "")
            if s:
                strength[player][s] += 3.0
        elif action == "SUN":
            for s in ALL_SUITS:
                strength[player][s] += 1.0
        elif action == "PASS":
            for s in ALL_SUITS:
                strength[player][s] -= 0.3

    # --- Trick analysis ---
    for trick in trick_history or []:
        cards = trick.get("cards", [])
        if not cards:
            continue
        led_suit = cards[0].get("card", {}).get("suit", "")
        for entry in cards:
            player = entry.get("playedBy", "")
            if player not in opps:
                continue
            total_plays[player] += 1
            cd = entry.get("card", {})
            rank, suit = cd.get("rank", ""), cd.get("suit", "")
            is_leader = (player == trick.get("leader", ""))

            # Void detection
            if suit != led_suit and led_suit:
                voids[player].add(led_suit)
                strength[player][led_suit] = -5.0
                # Trumped?
                if suit == trump_suit:
                    trump_count[player] += 1
                    if rank in ("J", "9"):
                        high_trump[player] = True
                    agg_plays[player] += 1

            # Suit strength from plays
            if is_leader:
                if rank in _HIGH:
                    strength[player][suit] += 2.0
                    agg_plays[player] += 1
                elif rank in _LOW:
                    strength[player][suit] -= 0.5
            else:
                if rank in _HIGH and suit == led_suit:
                    strength[player][suit] += 1.0

            # Trump counting (followed suit = trump led)
            if suit == trump_suit and suit == led_suit:
                trump_count[player] += 1
                if rank in ("J", "9"):
                    high_trump[player] = True

    # --- Build per-opponent profiles ---
    profiles: dict[str, dict] = {}
    for p in opps:
        strong_count = sum(1 for v in strength[p].values() if v > 1.0)
        tp = total_plays[p] or 1
        style_ratio = agg_plays[p] / tp
        style = "AGGRESSIVE" if style_ratio > 0.6 else ("PASSIVE" if style_ratio < 0.4 else "UNKNOWN")
        tc = trump_count[p] if mode == "HOKUM" else 0
        danger = min(1.0, tc * 0.15 + strong_count * 0.1 + style_ratio * 0.2)
        profiles[p] = {
            "void_suits": sorted(voids[p]),
            "estimated_trumps": tc,
            "has_high_trumps": high_trump[p],
            "strength_by_suit": dict(strength[p]),
            "play_style": style,
            "danger_level": round(danger, 2),
        }

    # --- Safe / avoid suits ---
    all_voids = set()
    for p in opps:
        all_voids |= voids[p]
    avoid = sorted(all_voids)
    safe = [s for s in ALL_SUITS if s != trump_suit
            and s not in all_voids
            and all(strength[p].get(s, 0) <= 1.0 for p in opps)]

    dangers = [profiles[p]["danger_level"] for p in opps]
    combined = round(sum(dangers) / max(len(dangers), 1), 2)

    notes = []
    for p in opps:
        pr = profiles[p]
        parts = []
        if pr["void_suits"]:
            parts.append(f"void {''.join(pr['void_suits'])}")
        if pr["has_high_trumps"]:
            parts.append("has high trump")
        parts.append(pr["play_style"].lower())
        notes.append(f"{p}: {', '.join(parts)}")

    return {
        "opponents": profiles,
        "safe_lead_suits": safe,
        "avoid_lead_suits": avoid,
        "combined_danger": combined,
        "reasoning": "; ".join(notes),
    }
