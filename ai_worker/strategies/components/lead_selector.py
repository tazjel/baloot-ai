"""Unified lead-card selection engine for Baloot AI.

Consults partner reads, defensive plans, and trump management to pick
the optimal opening card for a trick.  Pure functions — accepts module
outputs as parameters, does NOT import other strategy modules.
"""
from __future__ import annotations

ORDER_SUN: list[str] = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM: list[str] = ["7", "8", "Q", "K", "10", "A", "9", "J"]
ALL_SUITS: list[str] = ["♠", "♥", "♦", "♣"]

# Point values by mode
_PTS_SUN = {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2}
_PTS_HOKUM = {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3}


def _card_value(card, mode: str) -> int:
    """Raw point value of a card in the given mode."""
    pts = _PTS_HOKUM if mode == "HOKUM" else _PTS_SUN
    return pts.get(card.rank, 0)


def _rank_index(rank: str, mode: str) -> int:
    """Positional strength of a rank (higher = stronger)."""
    order = ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN
    return order.index(rank) if rank in order else -1


def _suits_in_hand(hand: list) -> dict[str, list[int]]:
    """Group hand indices by suit → {suit: [idx, ...]}."""
    groups: dict[str, list[int]] = {}
    for i, c in enumerate(hand):
        groups.setdefault(c.suit, []).append(i)
    return groups


def select_lead(
    hand: list,
    mode: str,
    trump_suit: str | None,
    we_are_buyers: bool,
    tricks_played: int,
    tricks_won_by_us: int,
    master_indices: list[int],
    partner_info: dict | None,
    defense_info: dict | None,
    trump_info: dict | None,
    opponent_voids: dict[str, set],
) -> dict:
    """Select the best card to lead with.

    Returns:
        dict with card_index, strategy, confidence, reasoning.
    """
    if not hand:
        return {"card_index": 0, "strategy": "SAFE_LEAD",
                "confidence": 0.0, "reasoning": "Empty hand — nothing to lead"}

    suits = _suits_in_hand(hand)
    voided = set()
    for s, positions in (opponent_voids or {}).items():
        if positions:
            voided.add(s)

    # Helper: pick best index from a list of candidates
    def _best_idx(indices: list[int]) -> int:
        return max(indices, key=lambda i: _rank_index(hand[i].rank, mode))

    def _lowest_idx(indices: list[int]) -> int:
        return min(indices, key=lambda i: _rank_index(hand[i].rank, mode))

    # ── 1. DESPERATION (late game, losing) ──
    tricks_remaining = 8 - tricks_played
    if tricks_remaining <= 2 and tricks_won_by_us < tricks_played - tricks_won_by_us:
        idx = _best_idx(list(range(len(hand))))
        c = hand[idx]
        return {"card_index": idx, "strategy": "DESPERATION",
                "confidence": 0.4,
                "reasoning": f"Late game losing ({tricks_won_by_us}/{tricks_played}) → lead {c.rank}{c.suit}"}

    # ── 2. MASTER_CASH ──
    safe_masters = [i for i in master_indices if hand[i].suit not in voided]
    if safe_masters:
        # Prefer master from shortest suit (void creation)
        idx = min(safe_masters, key=lambda i: (len(suits.get(hand[i].suit, [])), -_rank_index(hand[i].rank, mode)))
        c = hand[idx]
        return {"card_index": idx, "strategy": "MASTER_CASH",
                "confidence": 0.9,
                "reasoning": f"{c.rank}{c.suit} is master, suit len {len(suits.get(c.suit, []))} — guaranteed win"}

    # ── 3. TRUMP_DRAW (HOKUM only) ──
    if mode == "HOKUM" and trump_suit and trump_info:
        ti_action = trump_info.get("action") or trump_info.get("strategy", "")
        lead_trump = trump_info.get("lead_trump", False)
        if ti_action == "DRAW" or lead_trump:
            trump_indices = suits.get(trump_suit, [])
            if trump_indices:
                idx = _best_idx(trump_indices)
                c = hand[idx]
                return {"card_index": idx, "strategy": "TRUMP_DRAW",
                        "confidence": 0.85,
                        "reasoning": f"Trump draw: lead {c.rank}{c.suit} to strip enemy trumps"}

    # ── 4. DEFENSE_PRIORITY ──
    if not we_are_buyers and defense_info:
        pri_suit = defense_info.get("priority_suit")
        avoid = defense_info.get("avoid_suit")
        if pri_suit and pri_suit in suits and pri_suit not in voided:
            indices = suits[pri_suit]
            idx = _best_idx(indices)
            c = hand[idx]
            return {"card_index": idx, "strategy": "DEFENSE_PRIORITY",
                    "confidence": 0.75,
                    "reasoning": f"Defense priority: lead {c.rank}{c.suit} ({defense_info.get('reasoning', '')})"}

    # ── 5. PARTNER_FEED ──
    if partner_info and (partner_info.get("confidence", 0) >= 0.4):
        for ps in partner_info.get("likely_strong_suits", []):
            if ps in suits and ps not in voided and ps != trump_suit:
                indices = suits[ps]
                idx = _lowest_idx(indices)  # Lead low to let partner win
                c = hand[idx]
                return {"card_index": idx, "strategy": "PARTNER_FEED",
                        "confidence": 0.7,
                        "reasoning": f"Feed partner's strong {ps} — lead {c.rank}{c.suit}"}

    # ── 6. LONG_RUN ──
    for s, indices in sorted(suits.items(), key=lambda kv: -len(kv[1])):
        if s == trump_suit or s in voided:
            continue
        if len(indices) >= 4:
            top_idx = _best_idx(indices)
            c = hand[top_idx]
            return {"card_index": top_idx, "strategy": "LONG_RUN",
                    "confidence": 0.65,
                    "reasoning": f"Long run: {len(indices)} in {s}, lead {c.rank}{c.suit}"}

    # ── 7. SAFE_LEAD ──
    # Longest non-trump suit not voided by opponents
    safe_suits = {s: idxs for s, idxs in suits.items()
                  if s != trump_suit and s not in voided}
    if safe_suits:
        best_s = max(safe_suits, key=lambda s: (len(safe_suits[s]), _rank_index(hand[_best_idx(safe_suits[s])].rank, mode)))
        idx = _best_idx(safe_suits[best_s])
        c = hand[idx]
        return {"card_index": idx, "strategy": "SAFE_LEAD",
                "confidence": 0.5,
                "reasoning": f"Safe lead: {c.rank}{c.suit} from {len(safe_suits[best_s])}-card {best_s}"}

    # Fallback: lead highest card regardless
    idx = _best_idx(list(range(len(hand))))
    c = hand[idx]
    return {"card_index": idx, "strategy": "SAFE_LEAD",
            "confidence": 0.3,
            "reasoning": f"Fallback: lead {c.rank}{c.suit} (all suits problematic)"}
