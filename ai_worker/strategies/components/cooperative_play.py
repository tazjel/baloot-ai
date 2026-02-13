"""Cooperative play engine for Baloot AI.

Bridges partner_read.py inferences with lead/follow decisions.
Produces cooperative adjustments: feeding partner's strong suits,
avoiding their voids, drawing trumps on their behalf, and making
smart discards that protect the partnership.
"""
from __future__ import annotations

ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]
ALL_SUITS = ["♠", "♥", "♦", "♣"]
_PTS_SUN = {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2}
_PTS_HOKUM = {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3}


def _rv(rank: str, mode: str) -> int:
    return (ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN).index(rank)


def get_cooperative_lead(
    hand: list,
    partner_info: dict,
    mode: str,
    trump_suit: str | None = None,
    tricks_remaining: int = 8,
    we_are_buyers: bool = True,
) -> dict | None:
    """Return a cooperative lead recommendation, or None if no override.

    Strategies: FEED_STRONG (lead partner's suit), DRAW_TRUMP (clear
    enemy trumps for partner), SETUP_RUN (establish long shared suit),
    AVOID_VOID (filter out partner's void suits).
    """
    if not hand or not partner_info or partner_info.get("confidence", 0) < 0.25:
        return None

    order = ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN
    pconf = partner_info.get("confidence", 0.3)
    strong = partner_info.get("likely_strong_suits", [])
    void_suits = set(partner_info.get("likely_void_suits", []))
    by_suit: dict[str, list[int]] = {}
    for i, c in enumerate(hand):
        by_suit.setdefault(c.suit, []).append(i)

    # DRAW_TRUMP: partner has weak trumps but decent count → clear enemies
    if (mode == "HOKUM" and trump_suit
            and not partner_info.get("has_high_trumps", False)
            and partner_info.get("estimated_trumps", 0) >= 2):
        my_t = by_suit.get(trump_suit, [])
        high_t = [i for i in my_t if hand[i].rank in ("J", "9", "A")]
        if high_t:
            pick = max(high_t, key=lambda i: _rv(hand[i].rank, mode))
            return {"card_index": pick, "strategy": "DRAW_TRUMP",
                    "confidence": round(min(1.0, pconf * 0.9), 2),
                    "reasoning": f"Draw trump with {hand[pick].rank}{hand[pick].suit} for partner"}

    # SETUP_RUN: shared long suit (we have 3+ in partner's strong suit)
    for s in strong:
        if s in by_suit and len(by_suit[s]) >= 3:
            pick = max(by_suit[s], key=lambda i: _rv(hand[i].rank, mode))
            return {"card_index": pick, "strategy": "SETUP_RUN",
                    "confidence": round(min(1.0, pconf * 0.8), 2),
                    "reasoning": f"Setup run: lead {hand[pick].rank}{s} (3+ cards, partner strong)"}

    # FEED_STRONG: lead low in partner's strong suit
    for s in strong:
        if s in void_suits or s == trump_suit:
            continue
        cands = by_suit.get(s, [])
        low = [i for i in cands if _rv(hand[i].rank, mode) <= 3]  # rank idx 0-3 = low
        if low:
            pick = min(low, key=lambda i: _rv(hand[i].rank, mode))
            return {"card_index": pick, "strategy": "FEED_STRONG",
                    "confidence": round(min(1.0, pconf * 0.8), 2),
                    "reasoning": f"Feed {hand[pick].rank}{s} to partner (strong suit)"}

    return None  # no cooperative override


def get_cooperative_follow(
    hand: list,
    legal_indices: list[int],
    partner_info: dict,
    led_suit: str,
    mode: str,
    trump_suit: str | None = None,
    partner_winning: bool = False,
    trick_points: int = 0,
) -> dict | None:
    """Return a cooperative follow recommendation, or None if default is fine.

    Tactics: TRUMP_SUPPORT (follow partner's trump lead low),
    SMART_DISCARD (discard from partner's void suits, protect strong),
    SACRIFICE (protect partner's winning trick with our high card).
    """
    if not hand or not legal_indices or not partner_info:
        return None
    if partner_info.get("confidence", 0) < 0.2:
        return None

    pv = _PTS_HOKUM if mode == "HOKUM" else _PTS_SUN
    strong = set(partner_info.get("likely_strong_suits", []))
    p_voids = set(partner_info.get("likely_void_suits", []))

    # TRUMP_SUPPORT: partner led trump and has high trumps → follow lowest
    if (mode == "HOKUM" and trump_suit and led_suit == trump_suit
            and partner_info.get("has_high_trumps", False)):
        trump_legal = [i for i in legal_indices if hand[i].suit == trump_suit]
        if trump_legal:
            pick = min(trump_legal, key=lambda i: _rv(hand[i].rank, mode))
            return {"card_index": pick, "tactic": "TRUMP_SUPPORT",
                    "confidence": 0.7,
                    "reasoning": f"Support partner trump draw: play low {hand[pick].rank}{trump_suit}"}

    # SMART_DISCARD: void in led suit → discard smartly
    following_suit = any(hand[i].suit == led_suit for i in legal_indices)
    if not following_suit and legal_indices:
        # Prefer discarding from partner's void suits (no loss to partnership)
        from_p_void = [i for i in legal_indices if hand[i].suit in p_voids]
        if from_p_void:
            pick = min(from_p_void, key=lambda i: pv.get(hand[i].rank, 0))
            return {"card_index": pick, "tactic": "SMART_DISCARD",
                    "confidence": 0.65,
                    "reasoning": f"Discard {hand[pick].rank}{hand[pick].suit} (partner also void)"}
        # Avoid discarding from partner's strong suits
        safe_disc = [i for i in legal_indices if hand[i].suit not in strong]
        if safe_disc:
            pick = min(safe_disc, key=lambda i: pv.get(hand[i].rank, 0))
            return {"card_index": pick, "tactic": "SMART_DISCARD",
                    "confidence": 0.55,
                    "reasoning": f"Discard {hand[pick].rank}{hand[pick].suit} (protect partner suits)"}

    # SACRIFICE: partner winning high-value trick, we have a beater to protect
    if partner_winning and trick_points >= 15:
        beaters = [i for i in legal_indices
                   if pv.get(hand[i].rank, 0) >= 4 and hand[i].suit not in strong]
        if beaters:
            pick = max(beaters, key=lambda i: _rv(hand[i].rank, mode))
            return {"card_index": pick, "tactic": "SACRIFICE",
                    "confidence": 0.6,
                    "reasoning": f"Sacrifice {hand[pick].rank}{hand[pick].suit} to protect {trick_points}pt trick"}

    return None
