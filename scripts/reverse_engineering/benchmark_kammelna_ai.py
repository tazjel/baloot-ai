"""Mission 3: Kammelna AI Benchmarking.

Evaluates how strong Kammelna's autoplay/bot AI actually is by analyzing
BOT-labeled moves from Mission 2 with full game context.

Prerequisites: Mission 2 output (move_labels.json)

Output: gbaloot/data/training/kammelna_ai_benchmark.json
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
LABELS_PATH = OUTPUT_DIR / "move_labels.json"

from gbaloot.core.card_mapping import index_to_card


def load_labels() -> dict:
    """Load Mission 2 move labels."""
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_games() -> dict[str, dict]:
    """Load all games indexed by name."""
    games = {}
    for fname in sorted(os.listdir(ARCHIVE_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(ARCHIVE_DIR / fname, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                name = data.get("n", fname)
                data["_filename"] = fname
                games[name] = data
            except json.JSONDecodeError:
                pass
    return games


def decode_bitmask(bitmask: int) -> list[int]:
    """Decode card bitmask to list of card indices."""
    cards = []
    for bit in range(64):
        if bitmask & (1 << bit):
            cards.append(bit)
    return cards


def analyze_bot_card_plays(labels: dict, games: dict[str, dict]) -> dict:
    """Analyze all BOT card plays with full game context."""
    bot_plays = [
        m for m in labels.get("labeled_moves", [])
        if m["player_type"] == "BOT" and m["event_type"] == 4
    ]

    if not bot_plays:
        return {"total_bot_plays": 0, "note": "No bot card plays found"}

    analyzed_plays = []
    rank_plays = Counter()  # What ranks does the bot play?
    position_plays = Counter()  # Is bot lead/follow?
    trick_outcomes = Counter()  # Does bot win tricks?

    for play in bot_plays:
        game_name = play["game"]
        round_idx = play["round"] - 1
        event_idx = play["event_idx"]
        card_id = play.get("card_id")

        game = games.get(game_name)
        if game is None or card_id is None:
            continue

        if round_idx >= len(game.get("rs", [])):
            continue

        events = game["rs"][round_idx]["r"]

        # Get card info
        card = index_to_card(card_id)
        if card is None:
            continue

        rank_plays[card.rank] += 1

        # Determine if bot was leading or following
        # Count card plays before this one in the current trick
        cards_before = 0
        for i in range(event_idx - 1, -1, -1):
            if events[i].get("e") == 4:
                cards_before += 1
            elif events[i].get("e") == 6:
                break  # Previous trick boundary
            elif events[i].get("e") in (3,):
                continue  # Skip declarations

        if cards_before == 0:
            position = "lead"
        else:
            position = f"follow_{cards_before}"
        position_plays[position] += 1

        # Check if bot won the trick (look forward for e=6)
        # Count remaining cards in trick
        cards_after = 0
        trick_won_by = None
        for i in range(event_idx + 1, len(events)):
            if events[i].get("e") == 4:
                cards_after += 1
            elif events[i].get("e") == 6:
                # Trick ended — but e=6.p is NOT the winner
                # We can't determine winner without engine, so skip
                break
            elif events[i].get("e") in (3,):
                continue

        analysis = {
            "game": game_name,
            "round": play["round"],
            "card": f"{card.rank}{card.suit}",
            "rank": card.rank,
            "suit": card.suit,
            "position": position,
            "cards_before_in_trick": cards_before,
        }
        analyzed_plays.append(analysis)

    # Compute stats
    high_cards = sum(rank_plays.get(r, 0) for r in ["A", "K", "10"])
    low_cards = sum(rank_plays.get(r, 0) for r in ["7", "8", "9"])
    mid_cards = sum(rank_plays.get(r, 0) for r in ["J", "Q"])
    total = sum(rank_plays.values())

    return {
        "total_bot_plays": len(analyzed_plays),
        "rank_distribution": dict(rank_plays.most_common()),
        "position_distribution": dict(position_plays.most_common()),
        "card_value_tendency": {
            "high_cards_pct": round(high_cards / total * 100, 1) if total > 0 else 0,
            "mid_cards_pct": round(mid_cards / total * 100, 1) if total > 0 else 0,
            "low_cards_pct": round(low_cards / total * 100, 1) if total > 0 else 0,
        },
        "plays_sample": analyzed_plays[:30],
    }


def analyze_bot_bidding(labels: dict) -> dict:
    """Analyze BOT bidding decisions."""
    bot_bids = [
        m for m in labels.get("labeled_moves", [])
        if m["player_type"] == "BOT" and m["event_type"] == 2
    ]

    bid_dist = Counter(b.get("bid", "?") for b in bot_bids)

    return {
        "total_bot_bids": len(bot_bids),
        "bid_distribution": dict(bid_dist.most_common()),
        "aggressive_bids": sum(1 for b in bot_bids if b.get("bid") in ("sun", "hokom", "hokom2", "ashkal")),
        "passive_bids": sum(1 for b in bot_bids if b.get("bid") in ("pass", "wala", "waraq")),
    }


def analyze_bot_impact(labels: dict, games: dict[str, dict]) -> dict:
    """Analyze whether bot presence correlates with losing."""
    # Group by game+round
    bot_rounds: dict[tuple, int] = defaultdict(int)
    for m in labels.get("labeled_moves", []):
        if m["player_type"] == "BOT":
            key = (m["game"], m["round"])
            bot_rounds[key] += 1

    bot_team_wins = 0
    bot_team_losses = 0
    non_bot_total = 0

    for (game_name, round_num), bot_count in bot_rounds.items():
        game = games.get(game_name)
        if game is None:
            continue
        round_idx = round_num - 1
        if round_idx >= len(game.get("rs", [])):
            continue

        events = game["rs"][round_idx]["r"]
        result = None
        for ev in events:
            if ev.get("e") == 12:
                result = ev.get("rs", {})
                break
        if result is None:
            continue

        # Determine which team had the bot
        bot_seats = set()
        for m in labels.get("labeled_moves", []):
            if m["player_type"] == "BOT" and m["game"] == game_name and m["round"] == round_num:
                bot_seats.add(m["player_seat"])

        bot_teams = set()
        for s in bot_seats:
            bot_teams.add(1 if s in (1, 3) else 2)

        w = result.get("w", 0)
        for team in bot_teams:
            if w == team:
                bot_team_wins += 1
            else:
                bot_team_losses += 1

    return {
        "rounds_with_bot": len(bot_rounds),
        "bot_team_wins": bot_team_wins,
        "bot_team_losses": bot_team_losses,
        "bot_team_win_rate": round(
            bot_team_wins / (bot_team_wins + bot_team_losses) * 100, 1
        ) if (bot_team_wins + bot_team_losses) > 0 else 0,
    }


def document_bot_strategy(labels: dict) -> dict:
    """Document the bot's apparent strategy patterns."""
    bot_plays = [
        m for m in labels.get("labeled_moves", [])
        if m["player_type"] == "BOT" and m["event_type"] == 4
    ]

    observations = []

    # Check if bot tends to play high or low
    high = sum(1 for p in bot_plays if p.get("card", "").startswith(("A", "K", "10")))
    low = sum(1 for p in bot_plays if p.get("card", "").startswith(("7", "8", "9")))
    total = len(bot_plays)

    if total > 10:
        if high > low * 1.5:
            observations.append("Bot tends to play HIGH-value cards (aces, kings, 10s)")
        elif low > high * 1.5:
            observations.append("Bot tends to play LOW-value cards (7s, 8s, 9s)")
        else:
            observations.append("Bot plays a mix of high and low cards (no strong preference)")
    else:
        observations.append(f"Too few bot plays ({total}) for reliable strategy analysis")

    # Bidding strategy
    bot_bids = [
        m for m in labels.get("labeled_moves", [])
        if m["player_type"] == "BOT" and m["event_type"] == 2
    ]
    aggressive = sum(1 for b in bot_bids if b.get("bid") in ("sun", "hokom", "hokom2", "ashkal"))
    passive = sum(1 for b in bot_bids if b.get("bid") in ("pass", "wala", "waraq"))

    if passive > aggressive * 3:
        observations.append("Bot bids very CONSERVATIVELY (mostly passes)")
    elif aggressive > passive:
        observations.append("Bot bids AGGRESSIVELY (more bids than passes)")
    else:
        observations.append("Bot bidding is moderately conservative")

    return {
        "observations": observations,
        "sample_size": total,
        "bid_sample_size": len(bot_bids),
    }


def main():
    """Run Mission 3: Kammelna AI Benchmarking."""
    print("=" * 60)
    print("Mission 3: Kammelna AI Benchmarking")
    print("=" * 60)

    # Load data
    if not LABELS_PATH.exists():
        print(f"ERROR: Labels not found at {LABELS_PATH}. Run Mission 2 first.")
        return

    print(f"\nLoading move labels from {LABELS_PATH}...")
    labels = load_labels()
    stats = labels.get("statistics", {})
    print(f"Total moves: {stats.get('total_moves', 0)}")
    print(f"Bot moves: {stats.get('bot_moves', 0)} ({stats.get('bot_move_percentage', 0)}%)")

    print(f"\nLoading games...")
    games = load_all_games()
    print(f"Loaded {len(games)} games")

    # Analyze bot card plays
    print("\nAnalyzing bot card plays...")
    card_analysis = analyze_bot_card_plays(labels, games)
    print(f"Bot plays analyzed: {card_analysis['total_bot_plays']}")
    if "rank_distribution" in card_analysis:
        print(f"Rank distribution: {card_analysis['rank_distribution']}")
        print(f"Card value tendency: {card_analysis['card_value_tendency']}")
        print(f"Position distribution: {card_analysis['position_distribution']}")

    # Analyze bot bidding
    print("\nAnalyzing bot bidding...")
    bid_analysis = analyze_bot_bidding(labels)
    print(f"Bot bids: {bid_analysis['total_bot_bids']}")
    print(f"Bid distribution: {bid_analysis['bid_distribution']}")
    print(f"Aggressive: {bid_analysis['aggressive_bids']}, Passive: {bid_analysis['passive_bids']}")

    # Analyze bot impact
    print("\nAnalyzing bot impact on outcomes...")
    impact = analyze_bot_impact(labels, games)
    print(f"Rounds with bot: {impact['rounds_with_bot']}")
    print(f"Bot team wins: {impact['bot_team_wins']}, losses: {impact['bot_team_losses']}")
    print(f"Bot team win rate: {impact['bot_team_win_rate']}%")

    # Document strategy
    print("\nDocumenting bot strategy...")
    strategy = document_bot_strategy(labels)
    for obs in strategy["observations"]:
        print(f"  • {obs}")

    # Build output
    output = {
        "summary": {
            "total_bot_moves": stats.get("bot_moves", 0),
            "bot_percentage": stats.get("bot_move_percentage", 0),
            "games_with_bots": stats.get("games_with_bot_moves", 0),
        },
        "card_play_analysis": card_analysis,
        "bidding_analysis": bid_analysis,
        "impact_analysis": impact,
        "strategy_documentation": strategy,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "kammelna_ai_benchmark.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Output saved to {output_path}")

    return output


if __name__ == "__main__":
    main()
