"""Trump management engine for Baloot AI (HOKUM mode).

Decides the optimal trump strategy each turn: DRAW enemy trumps when
dominant, PRESERVE ours when outnumbered, set up CROSS_RUFF plays
through partner voids, or play NEUTRAL when trump is exhausted.
"""

ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]
ALL_SUITS = ["♠", "♥", "♦", "♣"]


def manage_trumps(
    hand: list,
    trump_suit: str,
    my_trumps: int,
    enemy_trumps_estimate: int,
    partner_trumps_estimate: int,
    tricks_played: int,
    we_are_buyers: bool,
    partner_void_suits: list[str],
    enemy_void_suits: list[str],
) -> dict:
    """Determine trump strategy for the current trick.

    Evaluates trump holdings, void patterns, and game phase to choose
    between drawing enemy trumps, preserving ours for ruffs, setting
    up cross-ruff sequences, or cashing side-suit winners freely.
    """
    trump_ranks = {c.rank for c in hand if c.suit == trump_suit}
    has_j = "J" in trump_ranks
    has_9 = "9" in trump_ranks
    has_j9 = has_j and has_9
    enemy_voids = set(enemy_void_suits or [])
    partner_voids = set(partner_void_suits or [])

    side_suits = [s for s in ALL_SUITS if s != trump_suit]
    safe_sides = [s for s in side_suits if s not in enemy_voids]
    my_void_sides = [s for s in side_suits
                     if not any(c.suit == s for c in hand)]
    ruff_targets = my_void_sides if my_trumps > 0 else []

    notes: list[str] = []
    action = "NEUTRAL"
    lead_trump = False

    # --- All enemy trumps gone → free play ---
    if enemy_trumps_estimate <= 0:
        action = "NEUTRAL"
        notes.append("enemy trumps exhausted→cash winners")
        return _result(action, False, safe_sides, ruff_targets, notes)

    # --- Late game: preserve last trump ---
    if tricks_played >= 5 and my_trumps == 1:
        action = "PRESERVE"
        notes.append("late game, 1 trump left→save for critical ruff")
        return _result(action, False, safe_sides, ruff_targets, notes)

    # --- Defenders with ≤2 trumps: never waste ---
    if not we_are_buyers and my_trumps <= 2:
        action = "PRESERVE"
        notes.append(f"defending with {my_trumps} trumps→preserve")
        return _result(action, False, safe_sides, ruff_targets, notes)

    # --- J+9 dominant: draw enemy trumps ---
    if has_j9 and enemy_trumps_estimate > 0:
        action = "DRAW"
        lead_trump = True
        notes.append(f"J+9 vs {enemy_trumps_estimate} enemy→draw trumps")
        return _result(action, lead_trump, safe_sides, ruff_targets, notes)

    # --- Buyers with J or 9 + 3+ trumps: offensive draw ---
    if we_are_buyers and (has_j or has_9) and my_trumps >= 3:
        action = "DRAW"
        lead_trump = True
        notes.append(f"buyer {my_trumps}t with {'J' if has_j else '9'}→draw")
        return _result(action, lead_trump, safe_sides, ruff_targets, notes)

    # --- Cross-ruff opportunity ---
    if partner_voids and my_trumps > 0 and ruff_targets:
        action = "CROSS_RUFF"
        notes.append(f"partner void {list(partner_voids)}, we void {ruff_targets}")
        return _result(action, False, safe_sides, ruff_targets, notes)
    if partner_voids and my_trumps > 0:
        action = "CROSS_RUFF"
        notes.append(f"partner void {list(partner_voids)}→lead for ruff")
        return _result(action, False, safe_sides, ruff_targets, notes)

    # --- Outnumbered in trump: preserve ---
    if my_trumps <= 2 and enemy_trumps_estimate > my_trumps:
        action = "PRESERVE"
        notes.append(f"{my_trumps}t vs {enemy_trumps_estimate} enemy→preserve")
        return _result(action, False, safe_sides, ruff_targets, notes)

    # --- Default: neutral, no strong signal ---
    notes.append(f"{my_trumps}t vs {enemy_trumps_estimate}e→neutral")
    return _result(action, False, safe_sides, ruff_targets, notes)


def _result(action, lead_trump, safe, ruffs, notes):
    return {
        "action": action,
        "lead_trump": lead_trump,
        "safe_side_suits": safe,
        "ruff_target_suits": ruffs,
        "reasoning": "; ".join(notes),
    }
