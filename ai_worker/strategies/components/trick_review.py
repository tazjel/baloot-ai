"""Trick review engine for Baloot AI.

Analyses completed tricks to detect momentum, suit safety patterns,
partner contribution, and opponent cooperation — then recommends
strategic shifts (CONSERVATIVE / AGGRESSIVE / DAMAGE_CONTROL).
"""
from __future__ import annotations

from ai_worker.strategies.constants import PTS_SUN, PTS_HOKUM
POSITIONS = ["Bottom", "Right", "Top", "Left"]
_PTS = {"SUN": PTS_SUN, "HOKUM": PTS_HOKUM}


def _team(pos: str) -> int:
    """0 = Bottom+Top, 1 = Right+Left."""
    return 0 if pos in ("Bottom", "Top") else 1


def _partner(pos: str) -> str:
    return POSITIONS[(POSITIONS.index(pos) + 2) % 4]


def review_tricks(
    my_position: str,
    trick_history: list[dict],
    mode: str,
    trump_suit: str | None = None,
    we_are_buyers: bool = True,
) -> dict:
    """Review completed tricks and return strategic adjustments.

    Tracks per-suit results, momentum, point totals, partner
    contribution, and opponent cooperation to recommend strategy shifts.
    """
    pv = _PTS.get(mode, _PTS["SUN"])
    my_team = _team(my_position)
    partner = _partner(my_position)

    our_tricks = their_tricks = our_pts = their_pts = 0
    suit_res: dict[str, dict] = {}
    partner_led = partner_won_as_leader = 0
    opp_feed_count = opp_won_tricks = 0
    last_winners: list[int] = []  # team ids of recent winners

    for trick in trick_history or []:
        cards = trick.get("cards", [])
        if not cards:
            continue
        winner = trick.get("winner", "")
        leader = trick.get("leader", "")
        w_team = _team(winner)
        led_suit = cards[0].get("card", {}).get("suit", "")

        # Points in trick
        trick_pts = sum(pv.get(e.get("card", {}).get("rank", ""), 0) for e in cards)
        if w_team == my_team:
            our_tricks += 1; our_pts += trick_pts
        else:
            their_tricks += 1; their_pts += trick_pts
        last_winners.append(w_team)

        # Partner contribution
        if leader == partner:
            partner_led += 1
            if winner == partner:
                partner_won_as_leader += 1

        # Opponent cooperation: opp discarded 10+ pt card to winning opp
        if w_team != my_team:
            opp_won_tricks += 1
            for e in cards:
                p = e.get("playedBy", "")
                if _team(p) != my_team and p != winner:
                    if pv.get(e.get("card", {}).get("rank", ""), 0) >= 10:
                        opp_feed_count += 1

        # Suit tracking
        sr = suit_res.setdefault(led_suit, {"led": 0, "won": 0, "lost": 0,
                                             "points_lost": 0, "got_trumped": False})
        sr["led"] += 1
        if w_team == my_team:
            sr["won"] += 1
        else:
            sr["lost"] += 1
            sr["points_lost"] += trick_pts
        # Detect trumping
        if trump_suit and mode == "HOKUM":
            for e in cards:
                cd = e.get("card", {})
                if cd.get("suit") == trump_suit and led_suit != trump_suit:
                    if _team(e.get("playedBy", "")) != my_team:
                        sr["got_trumped"] = True

    played = our_tricks + their_tricks

    # Momentum
    if not last_winners:
        momentum = "TIED"
    elif our_tricks > their_tricks and last_winners[-1] == my_team:
        momentum = "WINNING"
    elif their_tricks > our_tricks and last_winners[-1] != my_team:
        if len(last_winners) >= 2 and last_winners[-2] != my_team:
            momentum = "COLLAPSING"
        else:
            momentum = "LOSING"
    else:
        momentum = "TIED"

    # Strategy shift
    diff = our_tricks - their_tricks
    shift = "NONE"
    if played >= 4 and diff <= -2:
        shift = "DAMAGE_CONTROL"
    elif diff >= 2 and we_are_buyers:
        shift = "CONSERVATIVE"
    elif diff < 0 and we_are_buyers:
        shift = "AGGRESSIVE"

    # Suit analysis
    avoid = [s for s, d in suit_res.items()
             if d["got_trumped"] or (d["led"] > 0 and d["won"] / d["led"] < 0.3)]
    strong = [s for s, d in suit_res.items()
              if d["led"] > 0 and d["won"] / d["led"] >= 0.7]

    p_contrib = (partner_won_as_leader / partner_led) if partner_led else 0.5
    o_coop = (opp_feed_count / opp_won_tricks) if opp_won_tricks else 0.0

    notes = [f"{momentum} {our_tricks}-{their_tricks}, {'+' if our_pts >= their_pts else ''}{our_pts - their_pts}pts"]
    if avoid:
        notes.append(f"avoid {''.join(avoid)}")
    if strong:
        notes.append(f"strong {''.join(strong)}")
    if shift != "NONE":
        notes.append(shift.lower())

    return {
        "our_tricks": our_tricks, "their_tricks": their_tricks,
        "momentum": momentum,
        "points_won_by_us": our_pts, "points_won_by_them": their_pts,
        "strategy_shift": shift,
        "suit_results": suit_res,
        "avoid_suits": avoid, "strong_suits": strong,
        "partner_contribution": round(p_contrib, 2),
        "opponent_cooperation": round(o_coop, 2),
        "reasoning": "; ".join(notes),
    }
