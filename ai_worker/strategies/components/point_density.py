"""Point density evaluator for Baloot AI.

Assesses how many points are at stake in the current trick and advises
whether committing high cards is worthwhile.  Prevents wasting Aces on
empty tricks and ensures the bot fights hard for critical 26+ point pots.
"""

POINT_VALUES_SUN = {"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2, "9": 0, "8": 0, "7": 0}
POINT_VALUES_HOKUM = {"J": 20, "9": 14, "A": 11, "10": 10, "K": 4, "Q": 3, "8": 0, "7": 0}

_THRESHOLDS = [(0, "EMPTY", False), (6, "LOW", False),
               (15, "MEDIUM", True), (25, "HIGH", True)]


def _pts(rank: str, mode: str) -> int:
    return (POINT_VALUES_HOKUM if mode == "HOKUM" else POINT_VALUES_SUN).get(rank, 0)


def _classify(pts: int) -> tuple[str, bool]:
    if pts >= 26:
        return "CRITICAL", True
    # Walk thresholds in reverse to find the highest matching bracket
    for ceiling, label, worth in reversed(_THRESHOLDS):
        if pts >= ceiling:
            return label, worth
    return "EMPTY", False


def evaluate_trick_value(table_cards: list[dict], mode: str) -> dict:
    """Score the current trick's point density and fighting value."""
    total = 0
    point_count = 0
    for entry in table_cards:
        r = entry.get("rank", entry.get("card", {}).get("rank", ""))
        p = _pts(r, mode)
        total += p
        if p > 0:
            point_count += 1
    density, worth = _classify(total)
    return {
        "current_points": total,
        "density": density,
        "worth_fighting": worth,
        "point_cards_on_table": point_count,
    }


def should_play_high(
    table_cards: list[dict], my_card_rank: str, mode: str,
    partner_is_winning: bool, cards_remaining: int,
) -> dict:
    """Decide whether to commit a high card to this trick.

    Weighs trick density, partner status, and endgame urgency to
    prevent wasteful plays and ensure fights for critical pots.
    """
    ev = evaluate_trick_value(table_cards, mode)
    density = ev["density"]
    notes: list[str] = []

    # Rule 1: partner winning + density < HIGH → don't override
    if partner_is_winning and density not in ("HIGH", "CRITICAL"):
        notes.append(f"partner winning, density={density}→hold")
        return {"play_high": False, "reasoning": "; ".join(notes)}

    # Rule 2: CRITICAL → always fight
    if density == "CRITICAL":
        notes.append(f"{ev['current_points']}pts CRITICAL→fight")
        return {"play_high": True, "reasoning": "; ".join(notes)}

    # Rule 3: endgame (≤2 cards) → every point matters
    if cards_remaining <= 2:
        notes.append(f"{cards_remaining} cards left→play high")
        return {"play_high": True, "reasoning": "; ".join(notes)}

    # Rule 4: EMPTY trick + premium card → don't waste
    if density == "EMPTY" and my_card_rank in ("A", "10"):
        notes.append(f"empty trick, save {my_card_rank}")
        return {"play_high": False, "reasoning": "; ".join(notes)}

    # Rule 5: HIGH density + strong card → commit
    if density == "HIGH" and my_card_rank in ("A", "10", "K", "J"):
        notes.append(f"{ev['current_points']}pts HIGH + {my_card_rank}→commit")
        return {"play_high": True, "reasoning": "; ".join(notes)}

    # Rule 6: default to density.worth_fighting
    play = ev["worth_fighting"] and not partner_is_winning
    notes.append(f"density={density} worth={ev['worth_fighting']} partner_win={partner_is_winning}")
    return {"play_high": play, "reasoning": "; ".join(notes)}
