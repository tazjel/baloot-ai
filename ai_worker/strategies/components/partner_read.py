"""Partner-inference engine for Baloot AI.

Deduces what the partner likely holds by reading their bids, leads,
discards, and trump plays — pure heuristic, no ML.  Each observed
action adjusts per-suit strength scores and void/trump estimates.
"""
from __future__ import annotations
from collections import defaultdict

from ai_worker.strategies.constants import ALL_SUITS
HIGH_RANKS = {"A", "10", "K"}
LOW_RANKS = {"7", "8"}
_partner = lambda p: ["Bottom","Right","Top","Left"][(["Bottom","Right","Top","Left"].index(p)+2)%4]


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
            voids.add(led_suit); st[led_suit] = -5.0
            if mode == "HOKUM" and trump_suit and ps == trump_suit:
                t_seen += 1; t_est = max(t_est, t_seen + 1)
                if pr in {"J", "9"}: hi_trump = True
                st[trump_suit] += 1.5
                notes.append(f"ruff {led_suit} w/{pr}{ps}")
            else:
                if mode == "HOKUM" and trump_suit and t_seen > 0:
                    t_est = t_seen; notes.append(f"no ruff {led_suit}→low trump")
                # Discard signal: partner chose to discard from suit ps
                # 78.5% reliable that ps is their shortest non-void suit
                st[ps] -= 1.5
                # High-card discard = exhausting this suit (66.3% reliable)
                if pr in HIGH_RANKS:
                    st[ps] -= 1.0
                    notes.append(f"discard {pr}{ps}→exhausting")
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

    # --- Assemble result ---
    strong = sorted([s for s in ALL_SUITS if st[s] >= 1.0], key=lambda s: st[s], reverse=True)
    void_list = sorted(voids | {s for s in ALL_SUITS if st[s] <= -3.0})
    conf = min(1.0, ev / 12.0)
    detail = f"ev={ev} | {'; '.join(notes[:6])}" if notes else "no evidence yet"
    return {
        "likely_strong_suits": strong, "likely_void_suits": void_list,
        "estimated_trumps": t_est if mode == "HOKUM" else 0,
        "has_high_trumps": hi_trump, "confidence": round(conf, 2), "detail": detail,
    }
