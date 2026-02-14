"""Galoss (Khasara) awareness engine for Baloot AI.

Monitors score trajectory during a round to detect when the buying team
is at risk of losing their bid (Khasara/Galoss).  When detected, triggers
emergency defensive mode that shifts strategy from point-maximization
to point-denial.

Khasara rules:
- If the bidding team's Game Points <= opponents' Game Points, they lose ALL
  points to the opposing team (Khasara penalty).
- SUN total = 26 GP; HOKUM total = 16 GP
- Buyer must score MORE than half to avoid Khasara.

This module provides:
- galoss_check(): Assess Galoss risk for both teams
- get_emergency_action(): Recommend emergency plays when Galoss is near
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

from ai_worker.strategies.constants import ORDER_SUN, ORDER_HOKUM, PTS_SUN, PTS_HOKUM


def _estimate_remaining_points(
    tricks_played: int,
    our_points: int,
    their_points: int,
    mode: str,
) -> tuple[int, int]:
    """Estimate total remaining points still to be won.

    Total deck points (8 tricks):
    - SUN: A(11)+10(10)+K(4)+Q(3)+J(2) = 30 per suit * 4 = 120, + last trick 10 = 130
    - HOKUM: J(20)+9(14)+A(11)+10(10)+K(4)+Q(3) = 62 for trump + 30*3 for sides = 152, + last 10 = 162
    But in practice total varies. Use observed points + estimate.
    """
    scored = our_points + their_points
    tricks_remaining = 8 - tricks_played
    if tricks_played > 0:
        avg_per_trick = scored / tricks_played
    else:
        avg_per_trick = 16 if mode == "SUN" else 20  # rough average
    estimated_remaining = int(avg_per_trick * tricks_remaining)
    # Add last trick bonus if remaining
    if tricks_remaining > 0:
        estimated_remaining += 10  # last trick bonus
    return estimated_remaining, tricks_remaining


def galoss_check(
    mode: str,
    we_are_buyers: bool,
    tricks_played: int,
    our_points: int,
    their_points: int,
    our_tricks: int,
    their_tricks: int,
) -> dict:
    """Assess Galoss risk for the current round.

    Returns:
        dict with:
        - risk_level: "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
        - we_risk_galoss: bool (are WE at risk?)
        - they_risk_galoss: bool (are THEY at risk?)
        - emergency_mode: bool (should we shift to emergency strategy?)
        - buyer_deficit: int (how many points buyer trails by)
        - reasoning: str
    """
    tricks_remaining = 8 - tricks_played

    # Determine buyer and defender points
    if we_are_buyers:
        buyer_pts, defender_pts = our_points, their_points
        buyer_tricks, defender_tricks = our_tricks, their_tricks
    else:
        buyer_pts, defender_pts = their_points, our_points
        buyer_tricks, defender_tricks = their_tricks, our_tricks

    # GP thresholds for Khasara
    # SUN: 26 total GP → buyer needs >13 → needs more raw points
    # HOKUM: 16 total GP → buyer needs >8
    total_scored = buyer_pts + defender_pts
    buyer_deficit = defender_pts - buyer_pts  # positive = buyer trails

    # Estimate what's left
    est_remaining, _ = _estimate_remaining_points(
        tricks_played, our_points, their_points, mode,
    )

    # Buyer can still catch up?
    buyer_max_possible = buyer_pts + est_remaining  # If buyer wins ALL remaining
    buyer_can_recover = buyer_max_possible > defender_pts

    # Risk classification
    risk_level = "NONE"
    emergency = False
    notes = []

    if tricks_played < 2:
        # Too early to assess
        risk_level = "NONE"
        notes.append("early game — no risk assessment")
    elif buyer_deficit > 0:
        # Buyer is trailing
        if not buyer_can_recover:
            risk_level = "CRITICAL"
            emergency = True
            notes.append(f"buyer down {buyer_deficit}pts, cannot recover")
        elif buyer_deficit > est_remaining * 0.7:
            risk_level = "HIGH"
            emergency = True
            notes.append(f"buyer down {buyer_deficit}pts, needs {buyer_deficit}/{est_remaining} remaining")
        elif buyer_deficit > est_remaining * 0.4:
            risk_level = "MEDIUM"
            notes.append(f"buyer trailing by {buyer_deficit}pts, {est_remaining} left")
        else:
            risk_level = "LOW"
            notes.append(f"buyer slightly behind ({buyer_deficit}pts)")
    elif buyer_tricks == 0 and tricks_played >= 3:
        # Kaboot risk — buyer hasn't won ANY tricks
        risk_level = "CRITICAL"
        emergency = True
        notes.append(f"buyer 0 tricks in {tricks_played} — Kaboot imminent!")
    elif buyer_tricks == 0 and tricks_played >= 2:
        risk_level = "HIGH"
        emergency = True
        notes.append("buyer 0 tricks — Kaboot danger")

    we_risk = we_are_buyers and risk_level in ("MEDIUM", "HIGH", "CRITICAL")
    they_risk = not we_are_buyers and risk_level in ("MEDIUM", "HIGH", "CRITICAL")

    return {
        "risk_level": risk_level,
        "we_risk_galoss": we_risk,
        "they_risk_galoss": they_risk,
        "emergency_mode": emergency,
        "buyer_deficit": buyer_deficit,
        "tricks_remaining": tricks_remaining,
        "buyer_tricks": buyer_tricks,
        "defender_tricks": defender_tricks,
        "reasoning": "; ".join(notes) if notes else "no Galoss risk",
    }


def get_emergency_action(
    hand: list,
    legal_indices: list[int],
    mode: str,
    trump_suit: str | None,
    we_are_buyers: bool,
    galoss_info: dict,
    is_leading: bool,
    partner_winning: bool = False,
) -> dict | None:
    """Recommend emergency plays when Galoss is near.

    Returns dict with card_index, strategy, confidence, reasoning — or None.
    """
    if not galoss_info.get("emergency_mode"):
        return None
    if not legal_indices:
        return None

    order = ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN
    pts = PTS_HOKUM if mode == "HOKUM" else PTS_SUN

    def _rv(rank: str) -> int:
        return order.index(rank) if rank in order else -1

    if we_are_buyers:
        # ── BUYER IN GALOSS DANGER ──
        # Strategy: WIN AT ALL COSTS — play highest cards to take tricks
        if is_leading:
            # Lead our absolute strongest card
            best = max(legal_indices, key=lambda i: _rv(hand[i].rank))
            c = hand[best]
            return {"card_index": best, "strategy": "GALOSS_DESPERATION",
                    "confidence": 0.85,
                    "reasoning": f"GALOSS ALERT: Must win tricks — lead {c.rank}{c.suit}"}
        else:
            if partner_winning:
                # Feed maximum points to partner
                best = max(legal_indices, key=lambda i: pts.get(hand[i].rank, 0))
                c = hand[best]
                if pts.get(c.rank, 0) >= 3:
                    return {"card_index": best, "strategy": "GALOSS_FEED",
                            "confidence": 0.8,
                            "reasoning": f"GALOSS: Feed {c.rank}{c.suit} ({pts.get(c.rank, 0)}pts) to partner"}
            else:
                # Try to win the trick at any cost
                best = max(legal_indices, key=lambda i: _rv(hand[i].rank))
                c = hand[best]
                return {"card_index": best, "strategy": "GALOSS_FIGHT",
                        "confidence": 0.8,
                        "reasoning": f"GALOSS: Fight with {c.rank}{c.suit} — must win tricks"}
    else:
        # ── DEFENDER PRESSING GALOSS ON BUYER ──
        # Strategy: deny points to buyer, maximize our capture
        if is_leading:
            # Lead in suits where we're strong to extract points
            # Prefer Aces (guaranteed wins)
            aces = [i for i in legal_indices if hand[i].rank == "A"]
            if aces:
                pick = aces[0]
                c = hand[pick]
                return {"card_index": pick, "strategy": "GALOSS_PRESS",
                        "confidence": 0.8,
                        "reasoning": f"Press Galoss: cash {c.rank}{c.suit} to deny buyer"}
            # Otherwise lead our highest non-trump
            non_trump = [i for i in legal_indices
                         if not trump_suit or hand[i].suit != trump_suit]
            pool = non_trump if non_trump else legal_indices
            best = max(pool, key=lambda i: _rv(hand[i].rank))
            c = hand[best]
            return {"card_index": best, "strategy": "GALOSS_PRESS",
                    "confidence": 0.7,
                    "reasoning": f"Press Galoss: lead {c.rank}{c.suit} to deny buyer"}
        else:
            # Following: play to win if possible, deny points
            if not partner_winning:
                best = max(legal_indices, key=lambda i: _rv(hand[i].rank))
                c = hand[best]
                return {"card_index": best, "strategy": "GALOSS_DENY",
                        "confidence": 0.75,
                        "reasoning": f"Galoss deny: play {c.rank}{c.suit} to take trick from buyer"}

    return None
