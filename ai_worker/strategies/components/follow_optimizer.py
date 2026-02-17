"""Follow-suit card optimizer for Baloot AI.

Determines the optimal card to play when following suit (seats 2, 3, 4
in a trick).  Implements an 8-tactic priority cascade covering winning,
dodging, trumping, and shedding scenarios for both SUN and HOKUM modes.

Thresholds calibrated against 12,693 pro follow plays (109 games):
- Feed partner: 41.4% high cards (seat 4: 51.8%)
- Conserve vs opponent: 23.0% high (seat 4: 19.3%)
- Second-hand-low: 42.7% early tricks
- Trump-in when void: only 26.8% (pros save trumps)
"""
from __future__ import annotations

from ai_worker.strategies.constants import (
    ORDER_SUN, ORDER_HOKUM, ALL_SUITS, PTS_SUN as _PTS_SUN, PTS_HOKUM as _PTS_HOKUM,
)


def _rank_index(rank: str, mode: str) -> int:
    """Positional strength of a rank (higher = stronger)."""
    order = ORDER_HOKUM if mode == "HOKUM" else ORDER_SUN
    return order.index(rank) if rank in order else -1


def _card_points(rank: str, mode: str) -> int:
    """Point value of a card rank in the given mode."""
    pts = _PTS_HOKUM if mode == "HOKUM" else _PTS_SUN
    return pts.get(rank, 0)


def _beats(card_rank: str, current_winner_rank: str, mode: str) -> bool:
    """Does card_rank beat current_winner_rank in the given mode?"""
    return _rank_index(card_rank, mode) > _rank_index(current_winner_rank, mode)


def _current_winner(table_cards: list[dict], led_suit: str, mode: str,
                    trump_suit: str | None) -> tuple[str, str, int]:
    """Find current winning rank, suit, and index from table_cards.

    Returns (winner_rank, winner_suit, winner_index).
    """
    if not table_cards:
        return ("7", led_suit, 0)

    best_idx = 0
    best_rank = table_cards[0].get("rank", "7")
    best_suit = table_cards[0].get("suit", led_suit)
    best_is_trump = (trump_suit and best_suit == trump_suit)

    for i, tc in enumerate(table_cards[1:], start=1):
        r, s = tc.get("rank", "7"), tc.get("suit", led_suit)
        is_trump = (trump_suit and s == trump_suit)

        if is_trump and not best_is_trump:
            best_idx, best_rank, best_suit, best_is_trump = i, r, s, True
        elif is_trump and best_is_trump:
            if _rank_index(r, mode) > _rank_index(best_rank, mode):
                best_idx, best_rank, best_suit = i, r, s
        elif not is_trump and not best_is_trump and s == best_suit:
            if _rank_index(r, mode) > _rank_index(best_rank, mode):
                best_idx, best_rank, best_suit = i, r, s

    return (best_rank, best_suit, best_idx)


def _result(idx: int, tactic: str, conf: float, reason: str) -> dict:
    return {"card_index": idx, "tactic": tactic,
            "confidence": round(conf, 2), "reasoning": reason}


def optimize_follow(
    hand: list,
    legal_indices: list[int],
    table_cards: list[dict],
    led_suit: str,
    mode: str,
    trump_suit: str | None,
    seat: int,
    partner_winning: bool,
    partner_card_index: int | None,
    trick_points: int,
    tricks_remaining: int,
    we_are_buyers: bool,
    suit_probs: dict[str, dict[str, float]] | None = None,
) -> dict:
    """Optimize follow-suit card selection.

    Args:
        hand: card objects with .rank, .suit
        legal_indices: indices of playable cards (pre-filtered by rules)
        table_cards: cards already played [{rank, suit, position}, ...]
        led_suit: suit that was led
        mode: "SUN" or "HOKUM"
        trump_suit: trump suit (None for SUN)
        seat: 2, 3, or 4 (position in trick)
        partner_winning: whether partner currently holds the trick
        partner_card_index: which table_card is partner's (0-based)
        trick_points: total points currently on table
        tricks_remaining: tricks left in round
        we_are_buyers: whether our team bought the bid
        suit_probs: Bayesian per-opponent suit probabilities. Used for
            smarter discard decisions (shed from suits opps are void in).

    Returns:
        dict with card_index, tactic, confidence, reasoning.
    """
    if not legal_indices:
        return _result(0, "SHED_SAFE", 0.0, "No legal cards")

    # Single legal card — no choice
    if len(legal_indices) == 1:
        c = hand[legal_indices[0]]
        return _result(legal_indices[0], "SHED_SAFE", 1.0,
                       f"Only legal card: {c.rank}{c.suit}")

    # Split legal cards into same-suit vs off-suit
    same_suit = [i for i in legal_indices if hand[i].suit == led_suit]
    off_suit = [i for i in legal_indices if hand[i].suit != led_suit]

    w_rank, w_suit, _ = _current_winner(table_cards, led_suit, mode, trump_suit)
    winner_is_trump = (trump_suit and w_suit == trump_suit)

    # ──────────────── FOLLOWING SUIT ────────────────
    if same_suit:
        # Cards that beat current winner
        if not winner_is_trump:
            beaters = [i for i in same_suit if _beats(hand[i].rank, w_rank, mode)]
        elif led_suit == trump_suit:
            # Following in trump suit — can beat with higher trump
            beaters = [i for i in same_suit if _beats(hand[i].rank, w_rank, mode)]
        else:
            beaters = []  # Can't beat a trump with a non-trump

        lowest_idx = min(same_suit, key=lambda i: _rank_index(hand[i].rank, mode))
        highest_idx = max(same_suit, key=lambda i: _rank_index(hand[i].rank, mode))

        # — Partner winning → FEED_PARTNER or DODGE —
        # Pro data: 41.4% feed high (A/10/K); seat 4 feeds 51.8%
        if partner_winning:
            # Tier 1: Feed A (11pts) or 10 (10pts) — massive point dump
            # Pro data: 30.0% feed A or 10 specifically (N=1706)
            big_feedable = [i for i in same_suit if _card_points(hand[i].rank, mode) >= 10]
            if big_feedable:
                idx = max(big_feedable, key=lambda i: _card_points(hand[i].rank, mode))
                c = hand[idx]
                # Seat 4 feeds more aggressively (pro: 51.8% vs 39.1%)
                conf = 0.88 if seat == 4 else 0.82
                return _result(idx, "FEED_PARTNER", conf,
                               f"Feed {c.rank}{c.suit} ({_card_points(c.rank, mode)}pts) to partner")
            # Tier 2: Feed K (4pts) or Q (3pts) — smaller but still valuable
            mid_feedable = [i for i in same_suit if _card_points(hand[i].rank, mode) >= 3]
            if mid_feedable and trick_points >= 5:
                idx = max(mid_feedable, key=lambda i: _card_points(hand[i].rank, mode))
                c = hand[idx]
                conf = 0.78 if seat == 4 else 0.70
                return _result(idx, "FEED_PARTNER", conf,
                               f"Feed {c.rank}{c.suit} ({_card_points(c.rank, mode)}pts) to partner's trick")
            # Tier 3: Just play lowest — dodge
            c = hand[lowest_idx]
            return _result(lowest_idx, "DODGE", 0.85,
                           f"Partner winning — play lowest {c.rank}{c.suit}")

        # ── SECOND-HAND-LOW DISCIPLINE ──
        # Pro data: seat 2 plays lowest 42.7% early, 36.6% overall (N=4188)
        # Seat 2: Play low unless master or high-value trick — let partner handle it
        if seat == 2 and beaters:
            masters = [i for i in beaters if _rank_index(hand[i].rank, mode) >= 7]  # Top rank = master-level
            if masters and trick_points >= 10:
                # We have the top card AND trick is valuable — take it
                idx = min(masters, key=lambda i: _rank_index(hand[i].rank, mode))
                c = hand[idx]
                return _result(idx, "SECOND_HAND_HIGH", 0.75,
                               f"2nd seat exception: take {trick_points}pts with master {c.rank}{c.suit}")
            if trick_points < 10:
                # Low-value trick — play low, let partner handle from seat 4
                c = hand[lowest_idx]
                # Pro data: stronger discipline in early tricks (42.7% vs 36.6%)
                conf = 0.75 if tricks_remaining >= 6 else 0.65
                return _result(lowest_idx, "SECOND_HAND_LOW", conf,
                               f"2nd seat low: save strength, play {c.rank}{c.suit}")

        # — Can we beat the current winner? —
        if beaters:
            cheapest_beater = min(beaters, key=lambda i: _rank_index(hand[i].rank, mode))

            # WIN_BIG: high-value trick (15+ points) — prioritize regardless of seat
            if trick_points >= 15:
                c = hand[cheapest_beater]
                return _result(cheapest_beater, "WIN_BIG", 0.88,
                               f"{c.rank}{c.suit} beats {w_rank}; {trick_points}pts on table")

            # DESPERATION: seat 4, opponent winning medium-value pot (10-14 pts)
            # Pro data: seat 4 aggression increases late-game (17.5%→23.8%)
            if seat == 4 and trick_points >= 10:
                c = hand[cheapest_beater]
                conf = 0.78 if tricks_remaining <= 3 else 0.72
                return _result(cheapest_beater, "DESPERATION", conf,
                               f"Seat 4, must win {trick_points}pt trick with {c.rank}{c.suit}")

            # WIN_CHEAP: seat 4 = guaranteed win for low-value tricks (<10 pts)
            if seat == 4:
                c = hand[cheapest_beater]
                return _result(cheapest_beater, "WIN_CHEAP", 0.9,
                               f"Seat 4 guaranteed win: {c.rank}{c.suit} beats {w_rank}")

            # Seat 3: only win cheap with a top-3 card
            if seat == 3 and _rank_index(hand[cheapest_beater].rank, mode) >= 5:
                c = hand[cheapest_beater]
                return _result(cheapest_beater, "WIN_CHEAP", 0.65,
                               f"Strong {c.rank}{c.suit} likely holds vs {w_rank}")

        # — Can't win → SHED_SAFE —
        c = hand[lowest_idx]
        return _result(lowest_idx, "SHED_SAFE", 0.6,
                       f"Can't beat {w_rank}{w_suit} — shed {c.rank}{c.suit}")

    # ──────────────── VOID (OFF-SUIT) ────────────────
    trump_cards = [i for i in off_suit if trump_suit and hand[i].suit == trump_suit]
    non_trump = [i for i in off_suit if not trump_suit or hand[i].suit != trump_suit]

    # Partner winning → FEED_OFFSUIT or DODGE (don't waste trump)
    # Pro data: 39.2% discard high (A/10/K) when partner winning (N=2082)
    if partner_winning:
        discard = non_trump if non_trump else off_suit
        # Feed high-point off-suit cards to partner (A, 10, K, Q)
        feedable_off = [i for i in discard if _card_points(hand[i].rank, mode) >= 4]
        if feedable_off:
            idx = max(feedable_off, key=lambda i: _card_points(hand[i].rank, mode))
            c = hand[idx]
            conf = 0.82 if seat == 4 else 0.75
            return _result(idx, "FEED_OFFSUIT", conf,
                           f"Feed {c.rank}{c.suit} ({_card_points(c.rank, mode)}pts) off-suit to partner")
        idx = min(discard, key=lambda i: _card_points(hand[i].rank, mode))
        c = hand[idx]
        return _result(idx, "DODGE", 0.8,
                       f"Partner winning, void — discard {c.rank}{c.suit}")

    # HOKUM: trump logic
    # Pro data: only 26.8% trump when void (N=3284) — pros conserve trumps
    if mode == "HOKUM" and trump_cards:
        # Opponent already trumped? → TRUMP_OVER
        if winner_is_trump:
            over_trumpers = [i for i in trump_cards
                             if _beats(hand[i].rank, w_rank, mode)]
            if over_trumpers:
                idx = min(over_trumpers, key=lambda i: _rank_index(hand[i].rank, mode))
                c = hand[idx]
                return _result(idx, "TRUMP_OVER", 0.7,
                               f"Over-trump {w_rank} with {c.rank}{c.suit}")

        # Worth trumping? Pro data: raise threshold — only trump for high-value tricks
        # Pros trump only 26.8% of void plays, so require >= 15 pts (was 10)
        if not partner_winning and trick_points >= 15:
            idx = min(trump_cards, key=lambda i: _rank_index(hand[i].rank, mode))
            c = hand[idx]
            return _result(idx, "TRUMP_IN", 0.78,
                           f"Ruff with {c.rank}{c.suit} for {trick_points}pt trick")

        # Medium-value trick: only trump from seat 4 (guaranteed last play)
        if not partner_winning and trick_points >= 10 and seat == 4:
            idx = min(trump_cards, key=lambda i: _rank_index(hand[i].rank, mode))
            c = hand[idx]
            return _result(idx, "TRUMP_IN", 0.65,
                           f"Seat 4 ruff {c.rank}{c.suit} for {trick_points}pt trick")

        # Below threshold — save trump, discard instead
        if non_trump:
            idx = min(non_trump, key=lambda i: _card_points(hand[i].rank, mode))
            c = hand[idx]
            return _result(idx, "SHED_SAFE", 0.6,
                           f"Save trump ({trick_points}pts) — shed {c.rank}{c.suit}")

    # SHED_SAFE: discard lowest-value card, prefer creating voids
    discard_pool = non_trump if non_trump else off_suit
    if discard_pool:
        # Prefer cards from shortest suits (void creation)
        # When Bayesian probs available, also prefer suits opps are unlikely to hold
        # (discarding from "dead" suits preserves cards in suits we might still win)
        suits_count: dict[str, int] = {}
        for i in discard_pool:
            s = hand[i].suit
            suits_count[s] = suits_count.get(s, 0) + 1

        def _shed_key(i: int) -> tuple:
            s = hand[i].suit
            suit_len = suits_count.get(s, 0)
            pts = _card_points(hand[i].rank, mode)
            # If Bayesian probs available, prefer shedding from suits opponents
            # are unlikely to hold (low avg probability = "dead" suit for opps)
            if suit_probs:
                opp_probs = [p.get(s, 0.5) for p in suit_probs.values()]
                avg_opp = sum(opp_probs) / max(len(opp_probs), 1)
            else:
                avg_opp = 0.5
            return (suit_len, avg_opp, pts)

        idx = min(discard_pool, key=_shed_key)
        c = hand[idx]
        return _result(idx, "SHED_SAFE", 0.5,
                       f"Void — discard {c.rank}{c.suit}")

    # Ultimate fallback
    idx = off_suit[0] if off_suit else legal_indices[0]
    c = hand[idx]
    return _result(idx, "SHED_SAFE", 0.3,
                   f"Fallback discard: {c.rank}{c.suit}")
