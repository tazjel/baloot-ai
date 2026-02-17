"""Partner-inference engine for Baloot AI.

Deduces what the partner likely holds by reading their bids, leads,
discards, and trump plays — pure heuristic, no ML.  Each observed
action adjusts per-suit strength scores and void/trump estimates.
"""
from __future__ import annotations
from collections import defaultdict

from ai_worker.strategies.constants import ALL_SUITS
from ai_worker.strategies.components.pro_data import (
    DISCARD_SHORTEST_SUIT_RELIABILITY,
    DISCARD_HIGHEST_IN_SUIT_RELIABILITY,
    DISCARD_HIGH_PARTNER_WINNING
)

HIGH_RANKS = {"A", "10", "K"}
LOW_RANKS = {"7", "8"}
_partner = lambda p: ["Bottom","Right","Top","Left"][(["Bottom","Right","Top","Left"].index(p)+2)%4]


def read_partner_discard(discard_history: list[dict]) -> dict:
    """Analyze partner's discards for signals.

    Returns:
        dict: {"short_suits": set, "feeding": bool, "confidence": float}
    """
    signals = {
        "short_suits": set(),
        "feeding": False,
        "confidence": 0.0
    }

    if not discard_history:
        return signals

    for discard in discard_history:
        suit = discard["suit"]
        rank = discard["rank"]
        partner_winning = discard.get("partner_winning", False)

        # Signal 1: Discard from suit -> Short in suit (78.5% reliable)
        signals["short_suits"].add(suit)

        # Signal 2: Discard high (A/10/K) + partner winning -> Feeding
        if partner_winning and rank in HIGH_RANKS:
            signals["feeding"] = True

    # Set confidence based on findings
    if signals["short_suits"]:
        signals["confidence"] = DISCARD_SHORTEST_SUIT_RELIABILITY

    return signals


def read_partner(
    partner_position: str, bid_history: list[dict], trick_history: list[dict],
    mode: str, trump_suit: str | None = None,
) -> dict:
    """Infer partner's likely hand from observed bids and plays.

    Returns suit strengths, void signals, trump estimates, and a
    confidence score scaled by the amount of evidence gathered.
    """
    st: dict[str, float] = defaultdict(float)
    voids: set[str] = set()
    shown: set[str] = set()
    t_seen = t_est = 0
    hi_trump = False
    ev = 0
    notes: list[str] = []

    # Track discards for signal analysis
    discard_history: list[dict] = []
    my_pos = _partner(partner_position)

    # --- Bid inference ---
    for bid in bid_history:
        if bid.get("player") != partner_position:
            continue
        act, bs = bid["action"], bid.get("suit")
        if act == "SUN":
            for s in ALL_SUITS: st[s] += 1.0
            notes.append("bid SUN→balanced"); ev += 3
        elif act == "HOKUM" and bs:
            st[bs] += 3.0; hi_trump = True; t_est = max(t_est, 3)
            notes.append(f"bid HOKUM {bs}"); ev += 3
        elif act == "PASS":
            for s in ALL_SUITS: st[s] -= 0.3
            notes.append("passed→weak"); ev += 1

    # --- Trick inference ---
    for trick in trick_history:
        cards = trick.get("cards", [])
        leader = trick.get("leader", "")
        if not cards:
            continue
        led_suit = cards[0]["suit"]
        pc = next((c for c in cards if c["position"] == partner_position), None)
        if not pc:
            continue
        ev += 1
        ps, pr = pc["suit"], pc["rank"]
        shown.add(ps)
        # --- Didn't follow suit ---
        if ps != led_suit:
            # Check for ruff vs discard
            is_ruff = (mode == "HOKUM" and trump_suit and ps == trump_suit)

            if is_ruff:
                voids.add(led_suit); st[led_suit] = -5.0
                t_seen += 1; t_est = max(t_est, t_seen + 1)
                if pr in {"J", "9"}: hi_trump = True
                st[trump_suit] += 1.5
                notes.append(f"ruff {led_suit} w/{pr}{ps}")
            else:
                # Discard logic
                voids.add(led_suit); st[led_suit] = -5.0
                if mode == "HOKUM" and trump_suit and t_seen > 0:
                    t_est = t_seen; notes.append(f"no ruff {led_suit}→low trump")
                st[ps] -= 1.0

                # Record discard for analysis
                is_winning = (trick.get("winner") == my_pos)
                discard_history.append({
                    "suit": ps,
                    "rank": pr,
                    "partner_winning": is_winning
                })
            continue
        # --- Followed suit ---
        if mode == "HOKUM" and ps == trump_suit:
            t_seen += 1; t_est = max(t_est, t_seen)
            if pr in {"J", "9"}: hi_trump = True
        is_lead = partner_position == leader
        if pr in HIGH_RANKS:
            st[ps] += 2.0 if is_lead else 1.0
            if is_lead: notes.append(f"led {pr}{ps}→strong")
        elif pr in LOW_RANKS:
            st[ps] -= 0.5 if is_lead else 0.3
            if is_lead: notes.append(f"led {pr}{ps}→weak")

    # --- Analyze Discards ---
    discard_signals = read_partner_discard(discard_history)

    # Merge signals
    likely_short = discard_signals["short_suits"]
    if likely_short:
        # These suits are likely short, so we can treat them similar to voids for some logic,
        # but technically they are just "short".
        # For now, we add them to a specific list or merge with voids?
        # The prompt says: "If partner discards from a suit, infer they're short in that suit"
        # We'll return them in likely_short_suits
        pass

    if discard_signals["feeding"]:
        notes.append("feeding signal")
        # Feeding implies partner WANTS us to have the lead, or is giving points.

    # --- Assemble result ---
    strong = sorted([s for s in ALL_SUITS if st[s] >= 1.0], key=lambda s: st[s], reverse=True)
    void_list = sorted(voids | {s for s in ALL_SUITS if st[s] <= -3.0})

    # Combine actual voids with inferred short suits
    # Note: Short suit inference means they have few cards, not necessarily zero.
    # But usually discard implies they have cards in that suit (unless they discarded their LAST card).
    # "Short" usually means singleton or doubleton.
    # We will expose it separately or merge?
    # The return dict structure is fixed in tests?
    # Test expects: self.assertIn("♠", result["likely_short_suits"])

    conf = min(1.0, ev / 12.0)
    if discard_signals["confidence"] > 0:
        conf = max(conf, discard_signals["confidence"])

    detail = f"ev={ev} | {'; '.join(notes[:6])}" if notes else "no evidence yet"

    return {
        "likely_strong_suits": strong,
        "likely_void_suits": void_list,
        "likely_short_suits": sorted(list(likely_short)), # New field
        "feeding": discard_signals["feeding"],           # New field
        "signals": ["feeding"] if discard_signals["feeding"] else [], # New field for tests
        "estimated_trumps": t_est if mode == "HOKUM" else 0,
        "has_high_trumps": hi_trump,
        "confidence": round(conf, 2),
        "detail": detail,
    }
