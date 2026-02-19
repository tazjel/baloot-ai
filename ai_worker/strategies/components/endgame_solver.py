"""Endgame solver for Baloot AI (≤3 cards per player).

With so few cards remaining the game tree is tiny (≤12 plies), making
exhaustive minimax with alpha-beta pruning both feasible and provably
optimal.  Called when each player holds 1–3 cards.
"""
from __future__ import annotations

POSITIONS = ["Bottom", "Right", "Top", "Left"]
TEAMS = {"Bottom": 0, "Top": 0, "Right": 1, "Left": 1}
from ai_worker.strategies.constants import (
    ORDER_SUN, ORDER_HOKUM, PTS_SUN_FULL as PTS_SUN, PTS_HOKUM_FULL as PTS_HOKUM,
)
_nxt = lambda p: POSITIONS[(POSITIONS.index(p) + 1) % 4]
_pts = lambda r, m: (PTS_HOKUM if m == "HOKUM" else PTS_SUN)[r]


def _strength(rank: str, suit: str, led: str, mode: str, trump: str | None) -> int:
    """Sortable trick-strength of a card."""
    if mode == "HOKUM" and trump and suit == trump:
        return 100 + ORDER_HOKUM.index(rank)
    if suit != led:
        return -1
    return (ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN).index(rank)


def resolve_trick(
    cards_played: list[tuple[str, object]], mode: str, trump_suit: str | None,
) -> str:
    """Determine which position wins a completed 4-card trick."""
    led = cards_played[0][1].suit
    return max(cards_played,
               key=lambda t: _strength(t[1].rank, t[1].suit, led, mode, trump_suit))[0]


def _legal(hand: list, led_suit: str | None) -> list[int]:
    """Indices of legally playable cards (must follow suit if able)."""
    if led_suit:
        follow = [i for i, c in enumerate(hand) if c.suit == led_suit]
        if follow:
            return follow
    return list(range(len(hand)))


def _finish(hands, trick, scores, mode, trump, my_team, a, b, forced):
    """Score a completed trick, then recurse or return terminal value."""
    winner = resolve_trick(trick, mode, trump)
    ns = list(scores)
    ns[TEAMS[winner]] += sum(_pts(c.rank, mode) for _, c in trick)
    if all(len(h) == 0 for h in hands.values()):
        return ns[my_team] - ns[1 - my_team]
    return _mm(hands, winner, [], ns, mode, trump, my_team, a, b, forced=None)


def _mm(hands, cur, trick, scores, mode, trump, my_team, a, b, forced) -> int:
    """Minimax with alpha-beta.  *forced*: optional (pos, idx) constraint
    that locks one player's move for the current trick only."""
    led = trick[0][1].suit if trick else None
    hand = hands[cur]
    if not hand and not trick:
        return scores[my_team] - scores[1 - my_team]
    if not hand:
        return (_finish(hands, trick, scores, mode, trump, my_team, a, b, forced)
                if len(trick) == 4
                else _mm(hands, _nxt(cur), trick, scores, mode, trump, my_team, a, b, forced))

    # Determine legal indices; override if this position is forced
    if forced and forced[0] == cur:
        indices = [forced[1]]
    else:
        indices = _legal(hand, led)

    maximizing = TEAMS[cur] == my_team
    best = -9999 if maximizing else 9999
    for i in indices:
        card = hand[i]
        nh = {p: ([c for j, c in enumerate(h) if j != i] if p == cur else list(h))
              for p, h in hands.items()}
        nt = trick + [(cur, card)]
        val = (_finish(nh, nt, scores, mode, trump, my_team, a, b, forced)
               if len(nt) == 4
               else _mm(nh, _nxt(cur), nt, scores, mode, trump, my_team, a, b, forced))
        if maximizing:
            best = max(best, val); a = max(a, val)
        else:
            best = min(best, val); b = min(b, val)
        if b <= a:
            break
    return best


def solve_endgame(
    my_hand: list, known_hands: dict[str, list], my_position: str,
    leader_position: str, mode: str, trump_suit: str | None = None,
) -> dict:
    """Find the optimal play via exhaustive minimax search.

    Returns ``{'cardIndex': int, 'expected_points': int, 'reasoning': str}``.
    Falls back to lowest-value heuristic when opponent hands are unknown.
    """
    my_team = TEAMS[my_position]
    hands: dict[str, list] = {my_position: list(my_hand)}
    for p in POSITIONS:
        if p != my_position:
            hands[p] = list(known_hands.get(p, []))
    # Graceful fallback for incomplete information
    if any(len(hands[p]) == 0 for p in POSITIONS if p != my_position):
        idx = min(range(len(my_hand)), key=lambda i: _pts(my_hand[i].rank, mode))
        return {"cardIndex": idx, "expected_points": 0,
                "reasoning": "Incomplete info — heuristic lowest-value discard"}
    # Evaluate each legal card by forcing our choice inside full minimax
    best_idx, best_val = 0, -9999
    led = None  # we may or may not be leading; _legal handles both
    for i in _legal(my_hand, led):
        forced = (my_position, i)
        val = _mm(hands, leader_position, [], [0, 0], mode, trump_suit,
                  my_team, -9999, 9999, forced)
        if val > best_val:
            best_val, best_idx = val, i
    n = len(my_hand)
    return {"cardIndex": best_idx, "expected_points": best_val,
            "reasoning": f"Minimax depth-{n * 4}: diff={best_val:+d}"}
