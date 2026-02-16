"""Mission 2: Human vs AI Move Labeling.

For every card played and bid made, label it as HUMAN, BOT, or UNKNOWN.
BOT = moves within disconnect (e=10) to rejoin (e=11) windows.

Output: gbaloot/data/training/move_labels.json
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

# Card ID → human-readable
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


def find_disconnect_windows(events: list[dict], player_ids: list[int]) -> dict[int, list[tuple[int, int]]]:
    """Find disconnect/rejoin windows for each player.

    Returns: {player_id: [(disconnect_event_idx, rejoin_event_idx or len(events))]}
    """
    windows: dict[int, list[tuple[int, int]]] = defaultdict(list)

    # Track active disconnects: player_id -> disconnect_event_idx
    active_disconnects: dict[int, int] = {}

    for i, event in enumerate(events):
        e_type = event.get("e")

        if e_type == 10:  # Disconnect
            db_id = event.get("dbId")
            if db_id is not None:
                active_disconnects[db_id] = i

        elif e_type == 11:  # Rejoin
            # e=11 might have dbId or p field
            db_id = event.get("dbId")
            if db_id is None:
                # Try matching by p field to player_ids
                p = event.get("p")
                if p and 1 <= p <= 4 and p - 1 < len(player_ids):
                    db_id = player_ids[p - 1]

            if db_id is not None and db_id in active_disconnects:
                start_idx = active_disconnects.pop(db_id)
                windows[db_id].append((start_idx, i))

    # Close any still-open disconnect windows at end of round
    for db_id, start_idx in active_disconnects.items():
        windows[db_id].append((start_idx, len(events)))

    return windows


def player_id_to_seat(player_ids: list[int], db_id: int) -> int | None:
    """Convert player database ID to seat number (1-4)."""
    try:
        return player_ids.index(db_id) + 1
    except ValueError:
        return None


def is_in_disconnect_window(
    event_idx: int,
    player_seat: int,
    player_ids: list[int],
    windows: dict[int, list[tuple[int, int]]],
) -> bool:
    """Check if a player's event falls within a disconnect window."""
    if player_seat < 1 or player_seat > 4:
        return False
    player_id = player_ids[player_seat - 1]
    for start, end in windows.get(player_id, []):
        if start < event_idx < end:
            return True
    return False


def label_round(
    game: dict,
    round_idx: int,
    round_events: list[dict],
) -> list[dict]:
    """Label all actionable events in a round as HUMAN or BOT."""
    player_ids = game.get("ps", [0, 0, 0, 0])
    game_name = game.get("n", game.get("_filename", "unknown"))

    # Find disconnect windows
    windows = find_disconnect_windows(round_events, player_ids)

    labeled = []

    for i, event in enumerate(round_events):
        e_type = event.get("e")
        player_seat = event.get("p")

        # Only label actionable events: bids (e=2), card plays (e=4), declarations (e=3)
        if e_type not in (2, 4, 3):
            continue

        if player_seat is None or player_seat < 1 or player_seat > 4:
            continue

        is_bot = is_in_disconnect_window(i, player_seat, player_ids, windows)

        label_entry = {
            "game": game_name,
            "round": round_idx + 1,
            "event_idx": i,
            "event_type": e_type,
            "event_type_name": {2: "bid", 4: "card_play", 3: "declaration"}.get(e_type, "?"),
            "player_seat": player_seat,
            "player_type": "BOT" if is_bot else "HUMAN",
        }

        # Add event-specific data
        if e_type == 4:
            card_id = event.get("c")
            label_entry["card_id"] = card_id
            label_entry["card"] = card_id_to_str(card_id) if card_id is not None else None
        elif e_type == 2:
            label_entry["bid"] = event.get("b")
        elif e_type == 3:
            label_entry["declaration_type"] = event.get("prj")

        if is_bot:
            label_entry["context"] = "disconnect_window"

        labeled.append(label_entry)

    return labeled


def analyze_bot_play_patterns(labeled_moves: list[dict]) -> dict:
    """Analyze patterns in BOT-labeled card plays."""
    bot_plays = [m for m in labeled_moves if m["player_type"] == "BOT" and m["event_type"] == 4]
    bot_bids = [m for m in labeled_moves if m["player_type"] == "BOT" and m["event_type"] == 2]

    # Card distribution of bot plays
    bot_card_counts: Counter = Counter()
    for play in bot_plays:
        card = play.get("card", "?")
        bot_card_counts[card] += 1

    # Bot bid distribution
    bot_bid_counts: Counter = Counter()
    for bid in bot_bids:
        bot_bid_counts[bid.get("bid", "?")] += 1

    # Rank distribution (are bots playing high or low?)
    rank_counts = {"high": 0, "low": 0}
    for play in bot_plays:
        card = play.get("card", "")
        if any(r in card for r in ["A", "K", "10"]):
            rank_counts["high"] += 1
        elif any(r in card for r in ["7", "8", "9"]):
            rank_counts["low"] += 1

    return {
        "total_bot_card_plays": len(bot_plays),
        "total_bot_bids": len(bot_bids),
        "bot_card_distribution": dict(bot_card_counts.most_common(20)),
        "bot_bid_distribution": dict(bot_bid_counts.most_common()),
        "bot_rank_tendency": rank_counts,
    }


def compute_statistics(labeled_moves: list[dict]) -> dict:
    """Compute overall statistics."""
    total = len(labeled_moves)
    by_type = Counter(m["player_type"] for m in labeled_moves)
    by_event = Counter(m["event_type_name"] for m in labeled_moves)
    by_seat = Counter(m["player_seat"] for m in labeled_moves if m["player_type"] == "BOT")

    # Per-game bot frequency
    bot_by_game: Counter = Counter()
    total_by_game: Counter = Counter()
    for m in labeled_moves:
        total_by_game[m["game"]] += 1
        if m["player_type"] == "BOT":
            bot_by_game[m["game"]] += 1

    games_with_bots = sum(1 for g in bot_by_game if bot_by_game[g] > 0)

    return {
        "total_moves": total,
        "human_moves": by_type.get("HUMAN", 0),
        "bot_moves": by_type.get("BOT", 0),
        "bot_move_percentage": round(by_type.get("BOT", 0) / total * 100, 2) if total > 0 else 0,
        "moves_by_event_type": dict(by_event),
        "bot_moves_by_seat": dict(sorted(by_seat.items())),
        "games_with_bot_moves": games_with_bots,
        "total_games": len(total_by_game),
    }


def find_disconnect_summary(games: list[dict]) -> dict:
    """Summarize all disconnect/rejoin events across all games."""
    total_disconnects = 0
    total_rejoins = 0
    disconnect_durations = []  # in event count

    for game in games:
        player_ids = game.get("ps", [0, 0, 0, 0])
        for round_obj in game.get("rs", []):
            events = round_obj.get("r", [])
            windows = find_disconnect_windows(events, player_ids)
            for player_id, win_list in windows.items():
                for start, end in win_list:
                    total_disconnects += 1
                    if end < len(events):
                        total_rejoins += 1
                    duration = end - start
                    disconnect_durations.append(duration)

    return {
        "total_disconnect_events": total_disconnects,
        "total_rejoin_events": total_rejoins,
        "disconnect_windows": total_disconnects,
        "avg_window_duration_events": (
            round(sum(disconnect_durations) / len(disconnect_durations), 1)
            if disconnect_durations else 0
        ),
        "max_window_duration_events": max(disconnect_durations) if disconnect_durations else 0,
    }


def main():
    """Run Mission 2: Human vs AI Move Labeling."""
    print("=" * 60)
    print("Mission 2: Human vs AI Move Labeling")
    print("=" * 60)

    print(f"\nLoading games from {ARCHIVE_DIR}...")
    games = load_all_games()
    print(f"Loaded {len(games)} games")

    # Label all moves
    print("\nLabeling moves...")
    all_labeled: list[dict] = []

    for game in games:
        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])
            labeled = label_round(game, round_idx, events)
            all_labeled.extend(labeled)

    print(f"Labeled {len(all_labeled)} actionable moves")

    # Compute statistics
    stats = compute_statistics(all_labeled)
    print(f"\n--- Statistics ---")
    print(f"Total moves: {stats['total_moves']}")
    print(f"Human moves: {stats['human_moves']}")
    print(f"Bot moves: {stats['bot_moves']} ({stats['bot_move_percentage']}%)")
    print(f"Games with bot activity: {stats['games_with_bot_moves']}/{stats['total_games']}")
    print(f"Bot moves by seat: {stats['bot_moves_by_seat']}")

    # Disconnect summary
    disconnect_info = find_disconnect_summary(games)
    print(f"\n--- Disconnect Windows ---")
    print(f"Total disconnect events: {disconnect_info['total_disconnect_events']}")
    print(f"Total rejoin events: {disconnect_info['total_rejoin_events']}")
    print(f"Avg window size: {disconnect_info['avg_window_duration_events']} events")
    print(f"Max window size: {disconnect_info['max_window_duration_events']} events")

    # Analyze bot play patterns
    bot_patterns = analyze_bot_play_patterns(all_labeled)
    print(f"\n--- Bot Play Patterns ---")
    print(f"Bot card plays: {bot_patterns['total_bot_card_plays']}")
    print(f"Bot bids: {bot_patterns['total_bot_bids']}")
    print(f"Bot rank tendency: {bot_patterns['bot_rank_tendency']}")
    if bot_patterns['bot_bid_distribution']:
        print(f"Bot bid distribution: {bot_patterns['bot_bid_distribution']}")

    # Build output
    output = {
        "labeled_moves": all_labeled,
        "statistics": stats,
        "disconnect_summary": disconnect_info,
        "bot_play_patterns": bot_patterns,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "move_labels.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Output saved to {output_path}")

    return output


if __name__ == "__main__":
    main()
