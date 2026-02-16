"""Mission 5: Trick Resolution & Card Hierarchy Verification.

Verifies trick resolution by computing winners using our game engine's logic
and validating via the leader chain (winner of trick N = leader of trick N+1).

NOTE: The archive's e=6.p field is NOT the trick winner — it's an animation
target. The actual winner must be computed from the cards using game engine logic.

Output: gbaloot/data/training/trick_resolution_verify.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ARCHIVE_DIR = ROOT / "gbaloot" / "data" / "archive_captures" / "mobile_export" / "savedGames"
OUTPUT_DIR = ROOT / "gbaloot" / "data" / "training"

from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM
from gbaloot.core.card_mapping import index_to_card, SUIT_SYMBOL_TO_IDX

# Bid action → suit symbol
BID_SUIT_MAP = {
    "clubs": "♣",
    "diamonds": "♦",
    "hearts": "♥",
    "spades": "♠",
}


def load_all_games() -> list[dict]:
    """Load all JSON game files."""
    games = []
    for fname in sorted(os.listdir(ARCHIVE_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(ARCHIVE_DIR / fname, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                data["_filename"] = fname
                games.append(data)
            except json.JSONDecodeError:
                pass
    return games


def resolve_mode_and_trump(events: list[dict]) -> tuple[str, str | None]:
    """Resolve game mode and trump suit from bid events.

    Returns (mode, trump_symbol) where trump_symbol is a suit symbol like ♠.
    """
    mode = "SUN"
    trump_symbol = None

    for ev in events:
        if ev.get("e") != 2:
            continue
        gm = ev.get("gm")
        if gm == 1:
            mode = "SUN"
        elif gm == 2:
            mode = "HOKUM"
        elif gm == 3:
            mode = "SUN"  # Ashkal = SUN for scoring

        b = ev.get("b", "")
        suit = BID_SUIT_MAP.get(b)
        if suit is not None:
            trump_symbol = suit

    # For HOKUM without explicit suit bid, use fc (first card) suit
    if mode == "HOKUM" and trump_symbol is None:
        for ev in events:
            if ev.get("e") == 1:
                fc = ev.get("fc")
                if fc is not None:
                    fc_card = index_to_card(fc)
                    if fc_card is not None:
                        trump_symbol = fc_card.suit
                break

    if mode != "HOKUM":
        trump_symbol = None

    return mode, trump_symbol


def compute_winner(
    plays: list[tuple[int, int]],
    mode: str,
    trump_symbol: str | None,
) -> int:
    """Compute trick winner using game engine logic.

    Uses the proven algorithm from archive_trick_extractor._compute_winner.

    Args:
        plays: List of (player_seat_1indexed, card_index) in play order.
        mode: 'SUN' or 'HOKUM'.
        trump_symbol: Trump suit symbol for HOKUM, None for SUN.

    Returns:
        Winner's seat (1-indexed).
    """
    lead_card = index_to_card(plays[0][1])
    if lead_card is None:
        return plays[0][0]
    lead_suit = lead_card.suit

    best_seat = plays[0][0]
    best_strength = -1

    for p_seat, cidx in plays:
        card = index_to_card(cidx)
        if card is None:
            continue

        strength = -1
        if mode == "HOKUM" and trump_symbol and card.suit == trump_symbol:
            strength = 100 + ORDER_HOKUM.index(card.rank)
        elif card.suit == lead_suit:
            strength = ORDER_SUN.index(card.rank)

        if strength > best_strength:
            best_strength = strength
            best_seat = p_seat

    return best_seat


def extract_and_verify_tricks(games: list[dict]) -> dict:
    """Extract all tricks, compute winners, and verify via leader chain."""
    all_tricks = []
    leader_chain_valid = 0
    leader_chain_invalid = 0
    leader_chain_details = []
    total_tricks = 0

    # Track card hierarchy evidence
    sun_wins: list[dict] = []
    hokum_trump_wins: list[dict] = []

    for game in games:
        game_name = game.get("n", game.get("_filename", "unknown"))

        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])
            mode, trump_symbol = resolve_mode_and_trump(events)

            # Check if this is a waraq round (no card plays)
            has_cards = any(ev.get("e") == 4 for ev in events)
            if not has_cards:
                continue

            # Extract tricks: groups of 4 card plays, delimited by e=6
            current_plays: list[tuple[int, int]] = []
            round_tricks = []
            trick_num = 0

            for ev in events:
                e_type = ev.get("e")

                if e_type == 4:
                    p = ev.get("p", 0)
                    c = ev.get("c", -1)
                    if 1 <= p <= 4 and c >= 0:
                        current_plays.append((p, c))

                elif e_type == 6:
                    if len(current_plays) == 4:
                        trick_num += 1
                        total_tricks += 1

                        winner = compute_winner(current_plays, mode, trump_symbol)

                        # Build card display
                        cards_display = []
                        for p_seat, cidx in current_plays:
                            card = index_to_card(cidx)
                            if card:
                                cards_display.append(f"P{p_seat}:{card.rank}{card.suit}")
                            else:
                                cards_display.append(f"P{p_seat}:?({cidx})")

                        lead_card = index_to_card(current_plays[0][1])
                        lead_suit = lead_card.suit if lead_card else "?"

                        trick_data = {
                            "game": game_name,
                            "round": round_idx + 1,
                            "trick": trick_num,
                            "mode": mode,
                            "trump": trump_symbol,
                            "cards": cards_display,
                            "lead_suit": lead_suit,
                            "leader": current_plays[0][0],
                            "winner": winner,
                            "e6_p": ev.get("p"),  # Animation target, NOT winner
                        }
                        round_tricks.append(trick_data)

                    current_plays = []

            # Validate leader chain: winner of trick N should be leader of trick N+1
            for i in range(len(round_tricks) - 1):
                current_winner = round_tricks[i]["winner"]
                next_leader = round_tricks[i + 1]["leader"]
                if current_winner == next_leader:
                    leader_chain_valid += 1
                else:
                    leader_chain_invalid += 1
                    leader_chain_details.append({
                        "game": game_name,
                        "round": round_idx + 1,
                        "trick": round_tricks[i]["trick"],
                        "winner": current_winner,
                        "next_leader": next_leader,
                        "cards": round_tricks[i]["cards"],
                        "next_cards": round_tricks[i + 1]["cards"],
                        "mode": mode,
                        "trump": trump_symbol,
                    })

            all_tricks.extend(round_tricks)

    # Compare e=6.p against computed winner
    e6_agrees = sum(1 for t in all_tricks if t.get("e6_p") == t["winner"])
    e6_disagrees = sum(1 for t in all_tricks if t.get("e6_p") != t["winner"])

    chain_total = leader_chain_valid + leader_chain_invalid
    chain_rate = round(leader_chain_valid / chain_total * 100, 2) if chain_total > 0 else 0

    return {
        "summary": {
            "total_tricks": total_tricks,
            "leader_chain_valid": leader_chain_valid,
            "leader_chain_invalid": leader_chain_invalid,
            "leader_chain_rate": chain_rate,
            "e6_vs_engine_agrees": e6_agrees,
            "e6_vs_engine_disagrees": e6_disagrees,
            "e6_note": "e=6.p is animation target, NOT trick winner",
        },
        "card_hierarchy": {
            "ORDER_SUN": ORDER_SUN,
            "ORDER_HOKUM": ORDER_HOKUM,
            "explanation": {
                "sun": "7(0) < 8(1) < 9(2) < J(3) < Q(4) < K(5) < 10(6) < A(7)",
                "hokum_trump": "7(0) < 8(1) < Q(2) < K(3) < 10(4) < A(5) < 9(6) < J(7)",
                "hokum_nontrump": "Same as SUN order (A highest)",
                "trump_beats_nontrump": "Any trump card beats any non-trump card",
            },
        },
        "leader_chain_failures": leader_chain_details[:50],
        "trick_sample": all_tricks[:100],
        "total_tricks_available": len(all_tricks),
    }


def main():
    """Run Mission 5: Trick Resolution & Card Hierarchy Verification."""
    print("=" * 60)
    print("Mission 5: Trick Resolution & Card Hierarchy Verification")
    print("=" * 60)

    print(f"\nLoading games from {ARCHIVE_DIR}...")
    games = load_all_games()
    print(f"Loaded {len(games)} games")

    print("\nExtracting and verifying tricks via leader chain...")
    result = extract_and_verify_tricks(games)

    summary = result["summary"]
    print(f"\n--- Results ---")
    print(f"Total tricks: {summary['total_tricks']}")
    print(f"Leader chain valid: {summary['leader_chain_valid']}")
    print(f"Leader chain invalid: {summary['leader_chain_invalid']}")
    print(f"Leader chain rate: {summary['leader_chain_rate']}%")
    print(f"\ne=6.p vs engine: agrees={summary['e6_vs_engine_agrees']}, "
          f"disagrees={summary['e6_vs_engine_disagrees']}")
    print(f"NOTE: {summary['e6_note']}")

    if result["leader_chain_failures"]:
        print(f"\n--- First 10 Leader Chain Failures ---")
        for f in result["leader_chain_failures"][:10]:
            print(f"  {f['game']} R{f['round']} T{f['trick']}: "
                  f"winner=P{f['winner']}, next_leader=P{f['next_leader']}, "
                  f"mode={f['mode']}, trump={f['trump']}")
            print(f"    Cards: {f['cards']}")
            print(f"    Next:  {f['next_cards']}")

    print(f"\n--- Card Hierarchy ---")
    for name, desc in result["card_hierarchy"]["explanation"].items():
        print(f"  {name}: {desc}")

    # Save output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "trick_resolution_verify.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_path.name, f)  # placeholder
    # Write actual output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Output saved to {output_path}")

    return result


if __name__ == "__main__":
    main()
