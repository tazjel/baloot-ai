"""Mission 1: Event State Machine Extraction.

Parses all 109 mobile archive games and maps the complete game engine FSM —
every legal event transition, mandatory sequences, conditional branches, and frequencies.

Output: gbaloot/data/training/event_state_machine.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "gbaloot" / "data" / "archive_captures" / "mobile_export" / "savedGames"
OUTPUT_DIR = ROOT / "gbaloot" / "data" / "training"

EVENT_TYPES = {
    1: "Round Start",
    2: "Bid",
    3: "Declaration",
    4: "Card Play",
    5: "Foul/Khabsa",
    6: "Trick Won",
    7: "Challenge/Qayd",
    8: "Chat",
    9: "Session Resume",
    10: "Disconnect",
    11: "Rejoin",
    12: "Round Result",
    15: "Deal",
    16: "Kawesh",
}


def load_all_games() -> list[dict]:
    """Load all JSON game files from the archive directory."""
    games = []
    for fname in sorted(os.listdir(ARCHIVE_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(ARCHIVE_DIR / fname, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                data["_filename"] = fname
                games.append(data)
            except json.JSONDecodeError as exc:
                print(f"WARN: Failed to parse {fname}: {exc}", file=sys.stderr)
    return games


def extract_transitions(games: list[dict]) -> dict:
    """Extract all (event_type -> event_type) transition pairs across all games."""
    transition_counts: Counter = Counter()
    event_counts: Counter = Counter()
    # Track sequences of event types per round for pattern analysis
    round_sequences: list[list[int]] = []
    # Track transitions with context
    transition_context: dict[str, list[str]] = defaultdict(list)

    total_rounds = 0
    total_events = 0

    for game in games:
        game_name = game.get("n", game.get("_filename", "unknown"))
        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])
            if not events:
                continue

            total_rounds += 1
            sequence = []

            for i, event in enumerate(events):
                e_type = event.get("e")
                if e_type is None:
                    continue
                total_events += 1
                event_counts[e_type] += 1
                sequence.append(e_type)

                # Record transition to next event
                if i + 1 < len(events):
                    next_e = events[i + 1].get("e")
                    if next_e is not None:
                        key = f"{e_type}→{next_e}"
                        transition_counts[key] += 1

            round_sequences.append(sequence)

    return {
        "transition_counts": transition_counts,
        "event_counts": event_counts,
        "round_sequences": round_sequences,
        "total_rounds": total_rounds,
        "total_events": total_events,
    }


def find_mandatory_sequences(round_sequences: list[list[int]]) -> list[str]:
    """Find event sequences that appear in 100% of rounds (mandatory)."""
    total = len(round_sequences)
    if total == 0:
        return []

    # Check common opening patterns
    candidates = [
        [15, 1],       # Deal → Round Start
        [15, 1, 2],    # Deal → Round Start → First Bid
    ]

    mandatory = []
    for pattern in candidates:
        count = sum(
            1 for seq in round_sequences
            if len(seq) >= len(pattern) and seq[: len(pattern)] == pattern
        )
        pct = count / total * 100
        if pct >= 99.0:  # Allow tiny tolerance
            mandatory.append(f"{'→'.join(str(p) for p in pattern)} ({count}/{total} = {pct:.1f}%)")

    # Check if every trick sequence is 4 cards → trick_won
    # Look for 4→4→4→4→6 pattern
    four_card_trick_count = 0
    total_tricks = 0
    for seq in round_sequences:
        i = 0
        while i < len(seq):
            if seq[i] == 6:  # Trick won
                total_tricks += 1
                # Look backwards for 4 consecutive card plays
                # (may have declarations interspersed)
                card_count = 0
                j = i - 1
                while j >= 0 and seq[j] in (4, 3):  # Card play or declaration
                    if seq[j] == 4:
                        card_count += 1
                    j -= 1
                if card_count == 4:
                    four_card_trick_count += 1
            i += 1

    if total_tricks > 0:
        pct = four_card_trick_count / total_tricks * 100
        mandatory.append(
            f"4 cards → 6 (trick won): {four_card_trick_count}/{total_tricks} = {pct:.1f}%"
        )

    return mandatory


def find_conditional_branches(round_sequences: list[list[int]]) -> dict:
    """Identify conditional event patterns — when does e=3 appear mid-trick etc."""
    # Track where declarations (e=3) appear relative to card plays
    decl_positions = {
        "before_first_card": 0,
        "between_cards": 0,
        "after_trick_won": 0,
        "other": 0,
    }

    # Track where disconnects/rejoins happen
    disconnect_positions = {
        "during_bidding": 0,
        "during_play": 0,
        "between_tricks": 0,
        "other": 0,
    }

    for seq in round_sequences:
        phase = "bidding"  # start in bidding
        in_trick = False
        first_card_seen = False

        for i, e in enumerate(seq):
            if e == 4 and not first_card_seen:
                phase = "play"
                first_card_seen = True
                in_trick = True
            elif e == 4:
                in_trick = True
            elif e == 6:
                in_trick = False

            if e == 3:  # Declaration
                if not first_card_seen:
                    decl_positions["before_first_card"] += 1
                elif in_trick:
                    decl_positions["between_cards"] += 1
                elif not in_trick:
                    decl_positions["after_trick_won"] += 1
                else:
                    decl_positions["other"] += 1

            if e == 10:  # Disconnect
                if phase == "bidding":
                    disconnect_positions["during_bidding"] += 1
                elif in_trick:
                    disconnect_positions["during_play"] += 1
                elif not in_trick:
                    disconnect_positions["between_tricks"] += 1
                else:
                    disconnect_positions["other"] += 1

    return {
        "declaration_positions": decl_positions,
        "disconnect_positions": disconnect_positions,
    }


def generate_mermaid(transition_counts: Counter, event_counts: Counter) -> str:
    """Generate a Mermaid state diagram of the engine lifecycle."""
    lines = ["stateDiagram-v2"]

    # Define states
    for e_type, name in sorted(EVENT_TYPES.items()):
        count = event_counts.get(e_type, 0)
        safe_name = name.replace("/", "_").replace(" ", "_")
        lines.append(f"    e{e_type}: e={e_type} {name} (n={count})")

    lines.append("")

    # Sort transitions by count (descending) for readability
    sorted_transitions = sorted(transition_counts.items(), key=lambda x: -x[1])

    for key, count in sorted_transitions:
        src, dst = key.split("→")
        src_e, dst_e = int(src), int(dst)
        # Only show transitions that happen at least 5 times for clarity
        if count >= 5:
            lines.append(f"    e{src_e} --> e{dst_e}: {count}x")

    return "\n".join(lines)


def build_output(games: list[dict]) -> dict:
    """Build the complete state machine output."""
    result = extract_transitions(games)
    transition_counts = result["transition_counts"]
    event_counts = result["event_counts"]
    round_sequences = result["round_sequences"]

    # Build transitions dict with notes
    transitions = {}
    for key, count in sorted(transition_counts.items(), key=lambda x: -x[1]):
        src, dst = key.split("→")
        src_name = EVENT_TYPES.get(int(src), f"Unknown({src})")
        dst_name = EVENT_TYPES.get(int(dst), f"Unknown({dst})")
        transitions[key] = {
            "count": count,
            "note": f"{src_name} → {dst_name}",
        }

    # Find mandatory sequences
    mandatory = find_mandatory_sequences(round_sequences)

    # Find conditional branches
    branches = find_conditional_branches(round_sequences)

    # Generate mermaid diagram
    mermaid = generate_mermaid(transition_counts, event_counts)

    # Build from/to matrix for each event type
    from_matrix: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    to_matrix: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for key, count in transition_counts.items():
        src, dst = key.split("→")
        src_e, dst_e = int(src), int(dst)
        from_matrix[src_e][dst_e] = count
        to_matrix[dst_e][src_e] = count

    # Build adjacency summary
    adjacency = {}
    for e_type in sorted(EVENT_TYPES.keys()):
        successors = dict(sorted(from_matrix[e_type].items(), key=lambda x: -x[1]))
        predecessors = dict(sorted(to_matrix[e_type].items(), key=lambda x: -x[1]))
        if successors or predecessors:
            adjacency[str(e_type)] = {
                "name": EVENT_TYPES[e_type],
                "total_occurrences": event_counts.get(e_type, 0),
                "can_follow": {
                    f"e={k} ({EVENT_TYPES.get(k, '?')})": v
                    for k, v in successors.items()
                },
                "can_precede": {
                    f"e={k} ({EVENT_TYPES.get(k, '?')})": v
                    for k, v in predecessors.items()
                },
            }

    # Waraq detection: rounds that end without e=12
    waraq_rounds = sum(
        1 for seq in round_sequences if 12 not in seq
    )
    contracted_rounds = sum(
        1 for seq in round_sequences if 12 in seq
    )

    output = {
        "summary": {
            "total_games": len(games),
            "total_rounds": result["total_rounds"],
            "total_events": result["total_events"],
            "contracted_rounds": contracted_rounds,
            "waraq_rounds": waraq_rounds,
            "unique_transitions": len(transition_counts),
        },
        "transitions": transitions,
        "event_types": {str(k): v for k, v in EVENT_TYPES.items()},
        "event_counts": {
            f"e={k}": {"name": EVENT_TYPES.get(k, "Unknown"), "count": v}
            for k, v in sorted(event_counts.items(), key=lambda x: -x[1])
        },
        "mandatory_sequences": mandatory,
        "conditional_branches": branches,
        "adjacency": adjacency,
        "mermaid_diagram": mermaid,
    }

    return output


def main():
    """Run Mission 1: Event State Machine Extraction."""
    print("=" * 60)
    print("Mission 1: Event State Machine Extraction")
    print("=" * 60)

    print(f"\nLoading games from {ARCHIVE_DIR}...")
    games = load_all_games()
    print(f"Loaded {len(games)} games")

    print("\nExtracting state machine...")
    output = build_output(games)

    # Print summary
    summary = output["summary"]
    print(f"\n--- Summary ---")
    print(f"Total games: {summary['total_games']}")
    print(f"Total rounds: {summary['total_rounds']}")
    print(f"Total events: {summary['total_events']}")
    print(f"Contracted rounds: {summary['contracted_rounds']}")
    print(f"Waraq rounds: {summary['waraq_rounds']}")
    print(f"Unique transitions: {summary['unique_transitions']}")

    print(f"\n--- Event Counts ---")
    for key, val in output["event_counts"].items():
        print(f"  {key} ({val['name']}): {val['count']}")

    print(f"\n--- Top 20 Transitions ---")
    sorted_trans = sorted(
        output["transitions"].items(), key=lambda x: -x[1]["count"]
    )
    for key, val in sorted_trans[:20]:
        print(f"  {key}: {val['count']}x — {val['note']}")

    print(f"\n--- Mandatory Sequences ---")
    for seq in output["mandatory_sequences"]:
        print(f"  {seq}")

    print(f"\n--- Conditional Branches ---")
    print(f"  Declaration positions: {output['conditional_branches']['declaration_positions']}")
    print(f"  Disconnect positions: {output['conditional_branches']['disconnect_positions']}")

    # Save output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "event_state_machine.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Output saved to {output_path}")

    return output


if __name__ == "__main__":
    main()
