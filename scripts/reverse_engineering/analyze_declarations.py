"""Mission 4: Declaration & Project System Analysis.

Fully documents when and how declarations (projects/mashru3) are triggered,
validated, and scored. Maps e=3 timing relative to card plays and trick boundaries.

Output: gbaloot/data/training/declaration_analysis.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "gbaloot" / "data" / "archive_captures" / "mobile_export" / "savedGames"
OUTPUT_DIR = ROOT / "gbaloot" / "data" / "training"

DECL_TYPES = {
    1: "sira",    # 20 pts — 3 consecutive same-suit cards
    2: "50",      # 50 pts — 4 consecutive same-suit cards
    3: "100",     # 100 pts — 5+ consecutive same-suit cards
    4: "400",     # 400 pts — 4 of a kind
    5: "khamsin", # UI-only announcement (NOT scored — never in results)
    6: "baloot",  # K+Q of trump, 20 pts
}

DECL_VALUES = {
    1: 20, 2: 50, 3: 100, 4: 400, 5: 0, 6: 20,  # khamsin=0 (not scored)
}

# prj types that actually appear in round results
SCORED_PRJ_TYPES = {1, 2, 3, 4, 6}
# prj=5 (khamsin) is a UI event only — never appears in round results

# Suit order: 0=Spades(5), 1=Hearts(18), 2=Clubs(31), 3=Diamonds(44)
SUIT_OFFSETS = {0: ("♠", 5), 1: ("♥", 18), 2: ("♣", 31), 3: ("♦", 44)}
RANK_NAMES = {0: "7", 1: "8", 2: "9", 3: "10", 4: "J", 5: "Q", 6: "K", 7: "A"}


def card_id_to_str(card_id: int) -> str:
    """Convert archive card ID to human-readable string."""
    for suit_idx, (suit_sym, offset) in SUIT_OFFSETS.items():
        if offset <= card_id <= offset + 7:
            rank_idx = card_id - offset
            return f"{RANK_NAMES[rank_idx]}{suit_sym}"
    return f"?({card_id})"


def decode_bitmask(bitmask: int) -> list[int]:
    """Decode a card bitmask to list of card IDs."""
    cards = []
    for bit in range(52):
        if bitmask & (1 << bit):
            cards.append(bit)
    return cards


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


def resolve_game_mode(events: list[dict]) -> tuple[str, str | None]:
    """Resolve game mode (SUN/HOKUM) and trump suit from bid events."""
    mode = "UNKNOWN"
    trump_suit = None

    for ev in events:
        if ev.get("e") != 2:
            continue
        gm = ev.get("gm")
        if gm == 1:
            mode = "SUN"
        elif gm == 2:
            mode = "HOKUM"
        elif gm == 3:
            mode = "ASHKAL"

        b = ev.get("b", "")
        if b in ("clubs", "hearts", "spades", "diamonds"):
            trump_suit = b

    # For R1 Hokum, derive trump from fc
    if mode == "HOKUM" and trump_suit is None:
        for ev in events:
            if ev.get("e") == 1:
                fc = ev.get("fc")
                if fc is not None:
                    suit_idx = fc // 13
                    trump_suit = {0: "spades", 1: "hearts", 2: "clubs", 3: "diamonds"}.get(suit_idx)
                break

    return mode, trump_suit


def analyze_round_declarations(
    game: dict,
    round_idx: int,
    events: list[dict],
) -> list[dict]:
    """Analyze all declarations in a single round."""
    game_name = game.get("n", game.get("_filename", "unknown"))
    mode, trump_suit = resolve_game_mode(events)

    declarations = []
    card_play_count = 0
    trick_count = 0
    first_card_idx = None
    current_trick_cards = 0

    for i, ev in enumerate(events):
        e_type = ev.get("e")

        if e_type == 4:
            card_play_count += 1
            current_trick_cards += 1
            if first_card_idx is None:
                first_card_idx = i

        elif e_type == 6:
            trick_count += 1
            current_trick_cards = 0

        elif e_type == 3:
            prj = ev.get("prj")
            prj_cards_bitmask = ev.get("prjC")
            player_seat = ev.get("p")

            # Skip proof-only events (prj=None, only prjC present)
            # These are "show cards" confirmations, not new declarations
            if prj is None:
                continue

            # Determine timing
            if first_card_idx is None:
                timing = "before_first_card"
                timing_detail = "pre-play"
            elif current_trick_cards == 0:
                timing = "between_tricks"
                timing_detail = f"after_trick_{trick_count}"
            else:
                timing = "mid_trick"
                timing_detail = f"trick_{trick_count + 1}_card_{current_trick_cards}"

            # Decode proof cards
            proof_cards = []
            if prj_cards_bitmask is not None and prj_cards_bitmask > 0:
                proof_card_ids = decode_bitmask(prj_cards_bitmask)
                proof_cards = [card_id_to_str(c) for c in proof_card_ids]

            # Determine team
            team = 1 if player_seat in (1, 3) else 2

            decl = {
                "game": game_name,
                "round": round_idx + 1,
                "event_idx": i,
                "player_seat": player_seat,
                "team": team,
                "declaration_type": prj,
                "declaration_name": DECL_TYPES.get(prj, f"unknown({prj})"),
                "declaration_value": DECL_VALUES.get(prj, 0),
                "game_mode": mode,
                "trump_suit": trump_suit,
                "timing": timing,
                "timing_detail": timing_detail,
                "cards_played_before": card_play_count,
                "tricks_completed_before": trick_count,
                "proof_cards": proof_cards,
                "has_proof": len(proof_cards) > 0,
            }
            declarations.append(decl)

    return declarations


def validate_declarations_vs_results(games: list[dict]) -> dict:
    """Compare e=3 declarations against e=12 result r1/r2 arrays."""
    matches = 0
    mismatches = 0
    mismatch_details = []

    for game in games:
        game_name = game.get("n", game.get("_filename", "unknown"))
        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])

            # Collect SCORED e=3 declarations (skip proof-only and khamsin)
            e3_decls_t1: list[str] = []
            e3_decls_t2: list[str] = []
            for ev in events:
                if ev.get("e") != 3:
                    continue
                prj = ev.get("prj")
                if prj is None or prj not in SCORED_PRJ_TYPES:
                    continue  # proof event or UI-only announcement
                p = ev.get("p")
                name = DECL_TYPES.get(prj, f"?{prj}")
                team = 1 if p in (1, 3) else 2
                if team == 1:
                    e3_decls_t1.append(name)
                else:
                    e3_decls_t2.append(name)

            # Get e=12 result
            result_event = None
            for ev in events:
                if ev.get("e") == 12:
                    result_event = ev
                    break

            if result_event is None:
                continue  # waraq round

            rs = result_event.get("rs", {})
            r1 = [d.get("n") for d in rs.get("r1", [])]
            r2 = [d.get("n") for d in rs.get("r2", [])]

            # Compare (sorted for order-independence)
            e3_t1_sorted = sorted(e3_decls_t1)
            e3_t2_sorted = sorted(e3_decls_t2)
            r1_sorted = sorted(r1)
            r2_sorted = sorted(r2)

            if e3_t1_sorted == r1_sorted and e3_t2_sorted == r2_sorted:
                matches += 1
            else:
                mismatches += 1
                mismatch_details.append({
                    "game": game_name,
                    "round": round_idx + 1,
                    "e3_team1": e3_t1_sorted,
                    "e3_team2": e3_t2_sorted,
                    "result_r1": r1_sorted,
                    "result_r2": r2_sorted,
                })

    return {
        "total_compared": matches + mismatches,
        "matches": matches,
        "mismatches": mismatches,
        "match_rate": round(matches / (matches + mismatches) * 100, 2) if (matches + mismatches) > 0 else 0,
        "mismatch_details": mismatch_details[:20],  # Limit to first 20
    }


def analyze_competing_declarations(all_declarations: list[dict]) -> dict:
    """Analyze rounds where both teams declared — who gets priority?"""
    # Group declarations by (game, round)
    by_round: dict[tuple, list[dict]] = defaultdict(list)
    for d in all_declarations:
        key = (d["game"], d["round"])
        by_round[key].append(d)

    competing_rounds = []
    for key, decls in by_round.items():
        teams_declaring = set(d["team"] for d in decls)
        if len(teams_declaring) == 2:
            t1_decls = [d for d in decls if d["team"] == 1]
            t2_decls = [d for d in decls if d["team"] == 2]
            competing_rounds.append({
                "game": key[0],
                "round": key[1],
                "team1_declarations": [d["declaration_name"] for d in t1_decls],
                "team2_declarations": [d["declaration_name"] for d in t2_decls],
                "team1_total_value": sum(d["declaration_value"] for d in t1_decls),
                "team2_total_value": sum(d["declaration_value"] for d in t2_decls),
            })

    return {
        "total_competing_rounds": len(competing_rounds),
        "examples": competing_rounds[:20],
    }


def analyze_baloot_specifics(all_declarations: list[dict], games: list[dict]) -> dict:
    """Deep analysis of Baloot (prj=6) — King+Queen of trump."""
    baloot_decls = [d for d in all_declarations if d["declaration_type"] == 6]

    # Timing distribution
    timing_dist = Counter(d["timing"] for d in baloot_decls)

    # Mode distribution
    mode_dist = Counter(d["game_mode"] for d in baloot_decls)

    # Check if baloot always has proof cards
    with_proof = sum(1 for d in baloot_decls if d["has_proof"])
    without_proof = sum(1 for d in baloot_decls if not d["has_proof"])

    return {
        "total_baloot_declarations": len(baloot_decls),
        "timing_distribution": dict(timing_dist),
        "mode_distribution": dict(mode_dist),
        "with_proof_cards": with_proof,
        "without_proof_cards": without_proof,
    }


def main():
    """Run Mission 4: Declaration & Project System Analysis."""
    print("=" * 60)
    print("Mission 4: Declaration & Project System Analysis")
    print("=" * 60)

    print(f"\nLoading games from {ARCHIVE_DIR}...")
    games = load_all_games()
    print(f"Loaded {len(games)} games")

    # Analyze all declarations
    print("\nAnalyzing declarations...")
    all_declarations: list[dict] = []
    for game in games:
        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])
            decls = analyze_round_declarations(game, round_idx, events)
            all_declarations.extend(decls)

    print(f"Found {len(all_declarations)} declarations")

    # Statistics
    type_dist = Counter(d["declaration_name"] for d in all_declarations)
    timing_dist = Counter(d["timing"] for d in all_declarations)
    mode_dist = Counter(d["game_mode"] for d in all_declarations)

    print(f"\n--- Declaration Type Distribution ---")
    for name, count in type_dist.most_common():
        print(f"  {name}: {count}")

    print(f"\n--- Declaration Timing ---")
    for timing, count in timing_dist.most_common():
        print(f"  {timing}: {count}")

    print(f"\n--- By Game Mode ---")
    for mode, count in mode_dist.most_common():
        print(f"  {mode}: {count}")

    # Validate against results
    print("\nValidating declarations vs round results...")
    validation = validate_declarations_vs_results(games)
    print(f"  Matches: {validation['matches']}/{validation['total_compared']} ({validation['match_rate']}%)")
    if validation['mismatches'] > 0:
        print(f"  ⚠️ Mismatches: {validation['mismatches']}")
        for mm in validation['mismatch_details'][:5]:
            print(f"    {mm['game']} R{mm['round']}: e3_t1={mm['e3_team1']}, e3_t2={mm['e3_team2']}, "
                  f"r1={mm['result_r1']}, r2={mm['result_r2']}")

    # Competing declarations
    print("\nAnalyzing competing declarations...")
    competing = analyze_competing_declarations(all_declarations)
    print(f"  Rounds with both teams declaring: {competing['total_competing_rounds']}")

    # Baloot specifics
    print("\nAnalyzing Baloot specifics...")
    baloot = analyze_baloot_specifics(all_declarations, games)
    print(f"  Total Baloot declarations: {baloot['total_baloot_declarations']}")
    print(f"  Timing: {baloot['timing_distribution']}")
    print(f"  With proof cards: {baloot['with_proof_cards']}")
    print(f"  Without proof cards: {baloot['without_proof_cards']}")

    # Build output
    output = {
        "summary": {
            "total_declarations": len(all_declarations),
            "type_distribution": dict(type_dist.most_common()),
            "timing_distribution": dict(timing_dist.most_common()),
            "mode_distribution": dict(mode_dist.most_common()),
        },
        "declarations": all_declarations,
        "validation_vs_results": validation,
        "competing_declarations": competing,
        "baloot_analysis": baloot,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "declaration_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Output saved to {output_path}")

    return output


if __name__ == "__main__":
    main()
