"""Trump management engine for Baloot AI (HOKUM mode).

Decides the optimal trump strategy each turn using a phased approach:

Phase 1 — PARTIAL_DRAW: Lead 1-2 rounds of trump to extract enemy trumps
           when we hold J/9/A. Don't exhaust all our trumps yet.
Phase 2 — CASH_SIDES: Once partial draw is done, cash side-suit Aces/Kings
           before opponents can ruff them. Only safe when enemy trump
           count is reduced.
Phase 3 — FINISH: Lead remaining trumps to strip the last enemy trumps,
           then run side-suit winners freely.

Also handles: CROSS_RUFF (exploit matching voids), PRESERVE (weak trump,
save for critical ruff), and NEUTRAL (enemy trumps exhausted).
"""
from __future__ import annotations

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

    Uses a phased timing engine to maximize trick yield:
    1. Partial draw with top trumps to reduce enemy count
    2. Cash side-suit winners while enemies have fewer trumps
    3. Finish by leading last trumps to clear and run winners
    """
    trump_ranks = {c.rank for c in hand if c.suit == trump_suit}
    trump_cards = [c for c in hand if c.suit == trump_suit]
    has_j = "J" in trump_ranks
    has_9 = "9" in trump_ranks
    has_a = "A" in trump_ranks
    has_j9 = has_j and has_9
    enemy_voids = set(enemy_void_suits or [])
    partner_voids = set(partner_void_suits or [])

    side_suits = [s for s in ALL_SUITS if s != trump_suit]
    safe_sides = [s for s in side_suits if s not in enemy_voids]
    my_void_sides = [s for s in side_suits
                     if not any(c.suit == s for c in hand)]
    ruff_targets = my_void_sides if my_trumps > 0 else []

    # Count side-suit winners (Aces, A+K combos)
    side_winners = 0
    side_winner_suits = []
    for s in side_suits:
        s_cards = [c for c in hand if c.suit == s]
        s_ranks = {c.rank for c in s_cards}
        if 'A' in s_ranks:
            side_winners += 1
            side_winner_suits.append(s)
            if 'K' in s_ranks:
                side_winners += 1

    notes: list[str] = []
    action = "NEUTRAL"
    lead_trump = False
    phase = "NEUTRAL"

    # ═══════════════════════════════════════════════════════════
    # PHASE 0: Enemy trumps exhausted → free play
    # ═══════════════════════════════════════════════════════════
    if enemy_trumps_estimate <= 0:
        phase = "FREE_PLAY"
        notes.append("enemy trumps exhausted→cash all winners")
        return _result("NEUTRAL", False, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)

    # ═══════════════════════════════════════════════════════════
    # DEFENSIVE HANDLING: Non-buyers
    # ═══════════════════════════════════════════════════════════
    if not we_are_buyers:
        # Defenders with ≤2 trumps: preserve
        if my_trumps <= 2:
            phase = "PRESERVE"
            notes.append(f"defending with {my_trumps} trumps→preserve")
            return _result("PRESERVE", False, safe_sides, ruff_targets, notes,
                           phase=phase, side_winner_suits=side_winner_suits)
        # Defenders with J+9: counterattack by drawing declarer's trumps!
        if has_j9:
            phase = "COUNTER_DRAW"
            notes.append(f"defender J+9 vs {enemy_trumps_estimate}e→counterattack")
            return _result("DRAW", True, safe_sides, ruff_targets, notes,
                           phase=phase, side_winner_suits=side_winner_suits)
        # Defenders with some trumps: preserve for ruffs
        phase = "PRESERVE"
        notes.append(f"defender {my_trumps}t→preserve for ruffs")
        return _result("PRESERVE", False, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)

    # ═══════════════════════════════════════════════════════════
    # BUYERS ONLY: Phased Trump Timing Engine
    # ═══════════════════════════════════════════════════════════

    # Late game: preserve last trump for critical ruff
    if tricks_played >= 5 and my_trumps == 1:
        phase = "PRESERVE"
        notes.append("late game, 1 trump left→save for critical ruff")
        return _result("PRESERVE", False, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)

    # --- PHASE 1: PARTIAL_DRAW ---
    # Lead trump with top honors to extract 1-2 enemy trumps.
    # Don't exhaust all trumps — save some for ruffs/control.
    # Conditions: we hold top trump honor(s), enemy has trumps, early/mid game
    if has_j9 and enemy_trumps_estimate > 0:
        phase = "PARTIAL_DRAW"
        # With J+9, always draw — we win the trump trick guaranteed
        notes.append(f"J+9 phase 1: draw {enemy_trumps_estimate} enemy trumps")
        return _result("DRAW", True, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)

    if (has_j or has_9) and my_trumps >= 3 and enemy_trumps_estimate >= 2:
        # Single top honor + length: draw once to thin the field
        phase = "PARTIAL_DRAW"
        notes.append(f"{'J' if has_j else '9'} + {my_trumps}t→partial draw (thin field)")
        return _result("DRAW", True, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)

    # --- PHASE 2: CASH_SIDES ---
    # After partial draw (enemy trumps reduced), cash side-suit winners
    # before they can ruff. Only safe when enemy has ≤1 trump remaining
    # or when our side winners are in suits enemies can't ruff.
    if side_winners > 0 and enemy_trumps_estimate <= 1:
        # Enemy has 0-1 trumps: safe to cash side winners
        phase = "CASH_SIDES"
        notes.append(f"phase 2: cash {side_winners} side winners ({side_winner_suits}), enemy≤1t")
        return _result("CASH_SIDES", False, side_winner_suits or safe_sides,
                       ruff_targets, notes, phase=phase,
                       side_winner_suits=side_winner_suits)

    if side_winners > 0 and safe_sides:
        # Some side winners exist and some suits are safe (enemy not void)
        safe_winners = [s for s in side_winner_suits if s in safe_sides]
        if safe_winners:
            phase = "CASH_SIDES"
            notes.append(f"phase 2: cash safe winners in {safe_winners}")
            return _result("CASH_SIDES", False, safe_winners, ruff_targets,
                           notes, phase=phase, side_winner_suits=side_winner_suits)

    # --- PHASE 3: FINISH ---
    # Lead remaining trumps to clear the last enemy trumps.
    # Only when we have trump superiority but haven't drawn yet.
    if (has_j or has_9 or has_a) and my_trumps >= 2 and enemy_trumps_estimate == 1:
        phase = "FINISH"
        notes.append(f"phase 3: finish last enemy trump ({my_trumps}t vs 1e)")
        return _result("DRAW", True, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)

    # --- CROSS_RUFF ---
    # Exploit matching voids between us and partner
    if partner_voids and my_trumps > 0 and ruff_targets:
        phase = "CROSS_RUFF"
        notes.append(f"cross-ruff: partner void {list(partner_voids)}, we void {ruff_targets}")
        return _result("CROSS_RUFF", False, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)
    if partner_voids and my_trumps > 0:
        phase = "CROSS_RUFF"
        notes.append(f"partner void {list(partner_voids)}→lead for ruff")
        return _result("CROSS_RUFF", False, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)

    # --- Outnumbered: preserve ---
    if my_trumps <= 2 and enemy_trumps_estimate > my_trumps:
        phase = "PRESERVE"
        notes.append(f"{my_trumps}t vs {enemy_trumps_estimate}e→preserve")
        return _result("PRESERVE", False, safe_sides, ruff_targets, notes,
                       phase=phase, side_winner_suits=side_winner_suits)

    # --- Default: neutral ---
    notes.append(f"{my_trumps}t vs {enemy_trumps_estimate}e→neutral")
    return _result("NEUTRAL", False, safe_sides, ruff_targets, notes,
                   phase=phase, side_winner_suits=side_winner_suits)


def _result(action, lead_trump, safe, ruffs, notes, phase="NEUTRAL",
            side_winner_suits=None):
    return {
        "action": action,
        "lead_trump": lead_trump,
        "safe_side_suits": safe,
        "ruff_target_suits": ruffs,
        "phase": phase,
        "side_winner_suits": side_winner_suits or [],
        "reasoning": "; ".join(notes),
    }
