"""Endgame solver for Baloot AI (≤4 cards per player).

With few cards remaining, the game tree is small enough for exhaustive minimax
search with alpha-beta pruning. When opponent hands are uncertain, uses Monte
Carlo sampling to find the robust best move.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict

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
        # Recursion Guard: If trick is partial but nobody has cards, stop.
        if all(not h for h in hands.values()):
            # This is an invalid state (running out of cards mid-trick)
            # Just return current score diff to avoid infinite loop
            return scores[my_team] - scores[1 - my_team]

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


def _generate_distributions(
    unseen_cards: list,
    hand_counts: dict[str, int],
    voids: dict[str, set[str]],
    count: int = 10
) -> list[dict[str, list]]:
    """Generate random valid deal scenarios consistent with voids."""
    distributions = []
    attempts = 0
    max_attempts = count * 10

    players = [p for p in POSITIONS if hand_counts.get(p, 0) > 0]
    total_needed = sum(hand_counts[p] for p in players)

    if len(unseen_cards) < total_needed:
        return []

    while len(distributions) < count and attempts < max_attempts:
        attempts += 1
        pool = list(unseen_cards)
        random.shuffle(pool)

        hands = {}
        valid = True
        current_idx = 0

        for p in players:
            needed = hand_counts[p]
            segment = pool[current_idx : current_idx + needed]
            current_idx += needed

            # Check void constraints
            if any(c.suit in voids.get(p, set()) for c in segment):
                valid = False
                break
            hands[p] = segment

        if valid:
            distributions.append(hands)

    return distributions


def solve_endgame(
    my_hand: list,
    known_hands: dict[str, list],
    my_position: str,
    leader_position: str,
    mode: str,
    trump_suit: str | None = None,
    unseen_cards: list | None = None,
    voids: dict[str, set[str]] | None = None,
    current_trick: list[tuple[str, object]] | None = None,
) -> dict:
    """Find the optimal play via exhaustive minimax or Monte Carlo search.

    Args:
        my_hand: List of cards in bot's hand.
        known_hands: partial or complete dict of opponent hands.
        my_position: 'Bottom', 'Right', 'Top', or 'Left'.
        leader_position: Who leads the current trick.
        mode: 'SUN' or 'HOKUM'.
        trump_suit: Trump suit (if HOKUM).
        unseen_cards: List of cards not in my hand and not played (optional).
        voids: Dict of player_pos -> set of void suits (optional).
        current_trick: Cards already played in the current trick (optional).

    Returns:
        dict with keys 'cardIndex', 'expected_points', 'reasoning'.
    """
    my_team = TEAMS[my_position]
    current_trick = current_trick or []

    if not my_hand:
        return {"cardIndex": 0, "expected_points": 0, "reasoning": "Empty hand"}

    # 1. Check if we have perfect information
    is_perfect_info = True
    hands = {my_position: list(my_hand)}

    for p in POSITIONS:
        if p != my_position:
            if p not in known_hands or not known_hands[p]:
                # If hand is supposed to be empty (e.g. they played all cards), that's fine
                # But we don't know expected length easily here without trick count context
                # Assuming caller provides non-empty known_hands if they have cards.
                # If they have 0 cards and known_hands[p] is [], that's perfect info.
                # But here we assume if passed known_hands is empty/missing, it's imperfect.
                if unseen_cards: # If we have unseen cards, likely imperfect
                     is_perfect_info = False
                     # Don't break here, we need to populate hands for check below?
                     # No, if is_perfect_info is False, we might skip to MC.
                     # But let's let it finish to be consistent
            hands[p] = list(known_hands.get(p, []))

    # Determine start player for minimax
    if current_trick:
        start_player = _nxt(current_trick[-1][0])
    else:
        start_player = leader_position

    # 2. Perfect Information Search
    # Double check hand sizes match target_len
    target_len = len(my_hand)
    if is_perfect_info:
        for p in POSITIONS:
             if p == my_position: continue

             # If player already played in current trick, their hand should be target_len - 1?
             # No, if I have target_len cards.
             # If P played, P has target_len-1.
             # But current_trick is considered separate.
             # hands dict should contain REMAINING cards.

             trick_players = {t[0] for t in current_trick}
             expected = target_len if p not in trick_players else target_len - 1

             if len(hands[p]) != expected:
                  # If mismatch, assume imperfect info
                  is_perfect_info = False
                  break

    if is_perfect_info:
        best_idx, best_val = _find_best_move(
            my_hand, hands, start_player, current_trick, mode, trump_suit, my_team, my_position
        )
        return {
            "cardIndex": best_idx,
            "expected_points": best_val,
            "reasoning": f"Minimax depth-{len(my_hand) * 4}: diff={best_val:+d}"
        }

    # 3. Monte Carlo Search (if imperfect info)
    if unseen_cards and voids:
        hand_counts = {}
        trick_players = {t[0] for t in current_trick}

        for p in POSITIONS:
            if p == my_position:
                continue

            # Count logic
            if p in trick_players:
                count = len(my_hand) - 1
            else:
                count = len(my_hand)

            if count > 0:
                hand_counts[p] = count

        distributions = _generate_distributions(unseen_cards, hand_counts, voids, count=10)

        if distributions:
            vote_counts = Counter()
            score_sums = defaultdict(int)

            for dist in distributions:
                dist[my_position] = list(my_hand)
                idx, val = _find_best_move(
                    my_hand, dist, start_player, current_trick, mode, trump_suit, my_team, my_position
                )
                vote_counts[idx] += 1
                score_sums[idx] += val

            best_idx = vote_counts.most_common(1)[0][0]
            avg_val = score_sums[best_idx] / len(distributions)

            return {
                "cardIndex": best_idx,
                "expected_points": int(avg_val),
                "reasoning": f"Monte Carlo ({len(distributions)} samples): best_idx={best_idx}"
            }

    # 4. Fallback Heuristic
    if not my_hand:
         # Empty hand? Should not happen.
         return {"cardIndex": 0, "expected_points": 0, "reasoning": "Empty hand"}

    idx = min(range(len(my_hand)), key=lambda i: _pts(my_hand[i].rank, mode))
    return {
        "cardIndex": idx,
        "expected_points": 0,
        "reasoning": "Incomplete info — heuristic lowest-value discard"
    }


def _find_best_move(
    my_hand, hands, start_player, current_trick, mode, trump_suit, my_team, my_position
) -> tuple[int, int]:
    """Run minimax for a specific hand configuration."""

    cur = my_position
    led = current_trick[0][1].suit if current_trick else None

    # Determine legal indices
    indices = _legal(my_hand, led)

    best_idx, best_val = 0, -9999

    for i in indices:
        card = my_hand[i]

        nh = {p: ([c for j, c in enumerate(h) if j != i] if p == cur else list(h))
              for p, h in hands.items()}

        nt = current_trick + [(cur, card)]

        # If trick is full (4 cards), finish it
        if len(nt) == 4:
            val = _finish(nh, nt, [0, 0], mode, trump_suit, my_team, -9999, 9999, forced=None)
        else:
            val = _mm(nh, _nxt(cur), nt, [0, 0], mode, trump_suit, my_team, -9999, 9999, forced=None)

        if val > best_val:
            best_val, best_idx = val, i

    return best_idx, best_val
