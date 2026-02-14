"""Cross-module integration layer ("Brain") for Baloot AI.

Orchestrates multiple AI strategy modules and reconciles conflicting
advice using a strict priority cascade:

  1. Kaboot Pursuit  — sweep override when winning every trick
  2. Point Density   — evaluate if the current trick is worth fighting
  3. Trump Manager   — HOKUM lead strategy (DRAW / PRESERVE / CROSS_RUFF)
  4. Opponent Model  — avoid dangerous suits, prefer safe leads
  5. Defense Plan    — defender lead guidance (priority / avoid suits)
  6. Partner Signal  — lead toward partner's inferred strong suits
  7. Default         — yield to existing heuristics

Confidence threshold is dynamically adjusted by trick_review momentum.
When a module returns confidence ≥ threshold it wins and the cascade stops.
If multiple consulted modules agree on the same index, confidence gets
a +0.1 boost.
"""
from __future__ import annotations
from ai_worker.strategies.constants import (
    ORDER_SUN, ORDER_HOKUM, PTS_SUN_FULL as PV_SUN, PTS_HOKUM_FULL as PV_HOKUM,
)


def consult_brain(
    hand: list,
    table_cards: list[dict],
    mode: str,
    trump_suit: str | None,
    position: str,
    we_are_buyers: bool,
    partner_winning: bool,
    tricks_played: int,
    tricks_won_by_us: int,
    master_indices: list[int],
    tracker_voids: dict[str, list[str]],
    partner_info: dict | None,
    legal_indices: list[int] | None = None,
    opponent_info: dict | None = None,
    trick_review_info: dict | None = None,
) -> dict:
    """Run the priority cascade and return a single play recommendation.

    Each module is checked in order; the first to return confidence >= threshold
    wins.  Secondary opinions that agree boost the winner's confidence.

    New optional params:
        opponent_info: output of model_opponents() — safe/avoid suits, danger
        trick_review_info: output of review_tricks() — momentum, strategy_shift
    """
    if not hand:
        return _out(None, 0.0, [], "empty hand")

    order = ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN
    pv = PV_HOKUM if mode == "HOKUM" else PV_SUN
    leading = len(table_cards) == 0
    consulted: list[str] = []
    # Collect (module_name, index, confidence, reason) from each active module
    opinions: list[tuple[str, int | None, float, str]] = []

    # ── Trick Review: dynamic confidence threshold ────────────
    # Default cascade threshold is 0.5; trick_review shifts it
    threshold = 0.5
    if trick_review_info:
        consulted.append("trick_review")
        shift = trick_review_info.get("strategy_shift", "NONE")
        momentum = trick_review_info.get("momentum", "TIED")
        if shift == "AGGRESSIVE":
            threshold = 0.4   # Accept riskier plays when behind
        elif shift == "DAMAGE_CONTROL" or momentum == "COLLAPSING":
            threshold = 0.6   # Require higher confidence when collapsing
        elif shift == "CONSERVATIVE":
            threshold = 0.55  # Slightly tighter when protecting a lead

    # Build opponent avoid/safe suit sets for use across cascade
    opp_avoid: set[str] = set()
    opp_safe: list[str] = []
    if opponent_info:
        opp_avoid = set(opponent_info.get("avoid_lead_suits", []))
        opp_safe = opponent_info.get("safe_lead_suits", [])

    # ── 1. Kaboot Pursuit ───────────────────────────────────────
    pursuing = (tricks_won_by_us == tricks_played and tricks_played > 0
                and we_are_buyers)
    if pursuing:
        consulted.append("kaboot_pursuit")
        if master_indices:
            opinions.append(("kaboot_pursuit", master_indices[0], 0.9,
                             f"Kaboot: cash master {hand[master_indices[0]].rank}"
                             f"{hand[master_indices[0]].suit}"))
        else:
            # No masters but still sweeping — lead highest card
            best = max(range(len(hand)), key=lambda i: order.index(hand[i].rank))
            opinions.append(("kaboot_pursuit", best, 0.6,
                             f"Kaboot: no master, lead highest {hand[best].rank}"
                             f"{hand[best].suit}"))

    # ── 2. Point Density ────────────────────────────────────────
    if table_cards:
        consulted.append("point_density")
        pts = sum(pv.get(tc.get("rank", ""), 0) for tc in table_cards)
        if pts >= 26:  # CRITICAL
            best = max(range(len(hand)), key=lambda i: order.index(hand[i].rank))
            opinions.append(("point_density", best, 0.85,
                             f"CRITICAL {pts}pts→play {hand[best].rank}{hand[best].suit}"))
        elif pts >= 16 and not partner_winning:  # HIGH
            best = max(range(len(hand)), key=lambda i: order.index(hand[i].rank))
            opinions.append(("point_density", best, 0.7,
                             f"HIGH {pts}pts→fight with {hand[best].rank}{hand[best].suit}"))
        elif partner_winning and pts < 16:
            # Partner has it, play low
            low = min(range(len(hand)), key=lambda i: pv.get(hand[i].rank, 0))
            opinions.append(("point_density", low, 0.6,
                             f"partner winning {pts}pts→shed {hand[low].rank}{hand[low].suit}"))

    # ── 3. Trump Manager (HOKUM, leading) ───────────────────────
    if mode == "HOKUM" and trump_suit and leading:
        consulted.append("trump_manager")
        my_trumps = [i for i, c in enumerate(hand) if c.suit == trump_suit]
        trump_ranks = {hand[i].rank for i in my_trumps}
        has_j9 = {"J", "9"} <= trump_ranks

        if has_j9 and my_trumps:
            # DRAW: lead highest trump
            best_t = max(my_trumps, key=lambda i: order.index(hand[i].rank))
            opinions.append(("trump_manager", best_t, 0.8,
                             f"DRAW: J+9 trump→lead {hand[best_t].rank}{hand[best_t].suit}"))
        elif len(my_trumps) <= 1:
            # PRESERVE: lead from strongest non-trump
            non_t = [i for i in range(len(hand)) if hand[i].suit != trump_suit]
            if non_t:
                best_nt = max(non_t, key=lambda i: order.index(hand[i].rank))
                opinions.append(("trump_manager", best_nt, 0.6,
                                 f"PRESERVE: ≤1 trump→lead side {hand[best_nt].rank}"
                                 f"{hand[best_nt].suit}"))

    # ── 4. Opponent Model (leading) ─────────────────────────────
    if opponent_info and leading and opp_safe:
        consulted.append("opponent_model")
        danger = opponent_info.get("combined_danger", 0)
        # Pick strongest card in a safe suit
        safe_cards = [i for i in range(len(hand)) if hand[i].suit in opp_safe
                      and hand[i].suit != trump_suit]
        if safe_cards:
            pick = max(safe_cards, key=lambda i: (
                pv.get(hand[i].rank, 0), order.index(hand[i].rank)))
            # Confidence scales with danger: higher danger = stronger signal
            conf = min(0.85, 0.45 + danger * 0.4)
            opinions.append(("opponent_model", pick, round(conf, 2),
                             f"opp danger {danger:.0%}→safe lead "
                             f"{hand[pick].rank}{hand[pick].suit}"))

    # ── 5. Defense Plan (defending, leading) ────────────────────
    if not we_are_buyers and leading:
        consulted.append("defense_plan")
        enemy_void_suits = {s for s, ps in tracker_voids.items() if ps}
        # Also avoid suits flagged by opponent model
        avoid_all = enemy_void_suits | opp_avoid
        non_trump = [i for i in range(len(hand))
                     if hand[i].suit != trump_suit and hand[i].suit not in avoid_all]
        if non_trump:
            best_def = max(non_trump, key=lambda i: (
                pv.get(hand[i].rank, 0), order.index(hand[i].rank)))
            opinions.append(("defense_plan", best_def, 0.55,
                             f"defend: safe lead {hand[best_def].rank}{hand[best_def].suit}"))

    # ── 6. Partner Signal ───────────────────────────────────────
    if partner_info and partner_info.get("likely_strong_suits") and leading:
        consulted.append("partner_signal")
        target = partner_info["likely_strong_suits"][0]
        cands = [i for i, c in enumerate(hand) if c.suit == target]
        if cands:
            pick = cands[0]
            conf = min(1.0, partner_info.get("confidence", 0.3) * 0.8)
            opinions.append(("partner_signal", pick, conf,
                             f"partner strong in {target}→lead {hand[pick].rank}{hand[pick].suit}"))

    # ── 7. Default ──────────────────────────────────────────────
    consulted.append("default")

    # ── Legal index filtering ─────────────────────────────────
    # Remove any opinions recommending illegal card indices
    if legal_indices is not None:
        legal_set = set(legal_indices)
        opinions = [(n, idx, c, r) for n, idx, c, r in opinions
                    if idx is None or idx in legal_set]

    # ── Cascade resolution ──────────────────────────────────────
    winner_name: str | None = None
    rec: int | None = None
    conf = 0.0
    reason = "no module confident"

    for name, idx, c, r in opinions:
        if c >= threshold:
            winner_name, rec, conf, reason = name, idx, c, r
            break

    # Agreement boost: if another module picked the same index, +0.1
    if rec is not None:
        for name, idx, c, _ in opinions:
            if name != winner_name and idx == rec and c > 0:
                conf = min(1.0, conf + 0.1)
                reason += f" (+{name} agrees)"
                break

    return _out(rec, round(conf, 2), consulted, reason)


def _out(rec, conf, consulted, reason):
    return {
        "recommendation": rec,
        "confidence": conf,
        "modules_consulted": consulted,
        "reasoning": reason,
    }
