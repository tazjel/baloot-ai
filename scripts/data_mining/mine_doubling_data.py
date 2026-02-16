"""Mission 3: Doubling & Risk Management Database.

Extracts every doubling decision (and opportunity NOT taken) from 109
professional games, with hand strength and score context for Kelly Criterion.

Produces:
  - pro_doubling_database.json: Raw decision records
  - doubling_thresholds.json: Score-dependent thresholds
  - kelly_analysis_report.md: Kelly Criterion validation
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "gbaloot" / "data" / "archive_captures" / "mobile_export" / "savedGames"
TRAINING_DIR = ROOT / "gbaloot" / "data" / "training"

SOURCE_SUITS = {0: "♠", 1: "♥", 2: "♣", 3: "♦"}
SOURCE_RANKS = {5: "7", 6: "8", 7: "9", 8: "10", 9: "J", 10: "Q", 11: "K", 12: "A"}
VALID_RANK_RANGE = range(5, 13)

PTS_SUN = {"7": 0, "8": 0, "9": 0, "J": 2, "Q": 3, "K": 4, "10": 10, "A": 11}
PTS_HOKUM = {"7": 0, "8": 0, "Q": 3, "K": 4, "10": 10, "A": 11, "9": 14, "J": 20}

DOUBLING_BIDS = {"double", "redouble", "hokomclose", "hokomopen",
                 "beforeyou", "triple", "qahwa"}
DOUBLING_PASS_CONTEXT = {"pass"}  # Passes during doubling phase


def decode_bitmask(bitmask: int) -> list[int]:
    """Decode a 64-bit card bitmask into card indices."""
    cards = []
    for idx in range(52):
        if idx % 13 not in VALID_RANK_RANGE:
            continue
        if bitmask & (1 << idx):
            cards.append(idx)
    return sorted(cards)


def card_idx_to_info(idx: int) -> dict:
    suit_idx = idx // 13
    rank_idx = idx % 13
    return {"suit": SOURCE_SUITS.get(suit_idx, "?"), "rank": SOURCE_RANKS.get(rank_idx, "?")}


def compute_hand_metrics(hand_cards: list[int], trump_suit: str | None) -> dict:
    suits = defaultdict(list)
    aces = kings = queens = jacks = 0
    pts_sun = pts_hokum = 0
    for idx in hand_cards:
        info = card_idx_to_info(idx)
        rank, suit = info["rank"], info["suit"]
        suits[suit].append(rank)
        if rank == "A": aces += 1
        elif rank == "K": kings += 1
        elif rank == "Q": queens += 1
        elif rank == "J": jacks += 1
        pts_sun += PTS_SUN.get(rank, 0)
        pts_hokum += PTS_HOKUM.get(rank, 0)

    trump_count = len(suits.get(trump_suit, [])) if trump_suit else 0
    return {
        "trump_count": trump_count,
        "aces": aces, "kings": kings, "queens": queens, "jacks": jacks,
        "high_cards": aces + kings + queens + jacks,
        "point_value_sun": pts_sun, "point_value_hokum": pts_hokum,
        "longest_suit": max((len(v) for v in suits.values()), default=0),
    }


def player_team(seat: int) -> int:
    return 1 if seat in (1, 3) else 2


def resolve_game_mode(events: list[dict]) -> str:
    mode = "SUN"
    for ev in events:
        if ev.get("e") == 2:
            gm = ev.get("gm")
            if gm == 2: mode = "HOKUM"
            elif gm in (1, 3): mode = "SUN"
    return mode


def resolve_trump_suit(events: list[dict], fc: int | None) -> str | None:
    suit_bids = {"clubs": "♣", "hearts": "♥", "spades": "♠", "diamonds": "♦"}
    for ev in events:
        if ev.get("e") != 2: continue
        b = ev.get("b", "")
        if b in suit_bids: return suit_bids[b]
        if b in ("turntosun", "sun", "ashkal"): return None
    for ev in events:
        if ev.get("e") != 2: continue
        if ev.get("b") == "hokom" and fc is not None:
            return SOURCE_SUITS.get(fc // 13)
    return None


def get_bidder_seat(events: list[dict]) -> int:
    rb = -1
    for ev in events:
        if ev.get("e") == 2:
            v = ev.get("rb", -1)
            if v > 0: rb = v
    return rb


def load_bot_moves() -> set[tuple[str, int, int]]:
    labels_path = TRAINING_DIR / "move_labels.json"
    if not labels_path.exists(): return set()
    with open(labels_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {(m["game"], m["round"], m["event_idx"])
            for m in data.get("labeled_moves", []) if m.get("player_type") == "BOT"}


def extract_doubling_records(games: list[dict], bot_moves: set) -> list[dict]:
    """Extract all doubling decisions and missed opportunities."""
    records = []

    for game in games:
        game_name = game.get("n", game.get("_filename", "unknown"))

        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])

            # Get hands
            hands = {}
            for ev in events:
                if ev.get("e") == 15:
                    for si in range(min(4, len(ev.get("bhr", [])))):
                        hands[si + 1] = decode_bitmask(ev["bhr"][si])
                    break

            fc = None
            t1s = t2s = 0
            for ev in events:
                if ev.get("e") == 1:
                    fc = ev.get("fc")
                    t1s = ev.get("t1s", 0)
                    t2s = ev.get("t2s", 0)
                    break

            game_mode = resolve_game_mode(events)
            trump_suit = resolve_trump_suit(events, fc)
            bidder_seat = get_bidder_seat(events)
            bidding_team = player_team(bidder_seat) if bidder_seat > 0 else 0

            # Round result
            result = None
            for ev in events:
                if ev.get("e") == 12:
                    result = ev.get("rs", {})
                    break

            round_won_by = result.get("w", 0) if result else 0
            gp_t1 = result.get("s1", 0) if result else 0
            gp_t2 = result.get("s2", 0) if result else 0

            # Track doubling phase
            in_doubling_phase = False
            doubling_level = 1
            contract_set = False

            for ev_idx, ev in enumerate(events):
                if ev.get("e") != 2:
                    continue
                b = ev.get("b", "")
                seat = ev.get("p", 0)

                # Detect doubling phase entry
                if b in DOUBLING_BIDS:
                    in_doubling_phase = True

                if not in_doubling_phase and b not in DOUBLING_BIDS:
                    # Check if this is a pass during doubling opportunity
                    # Passes after a contract bid but before play = doubling opportunity
                    if b == "pass" and bidder_seat > 0 and not contract_set:
                        # This could be a normal bidding pass, not a doubling opportunity
                        # We only count it if the contract has been set
                        pass
                    continue

                is_bot = (game_name, round_idx + 1, ev_idx) in bot_moves
                team = player_team(seat) if seat > 0 else 0
                is_bidding_team = (team == bidding_team)

                hand = hands.get(seat, [])
                metrics = compute_hand_metrics(hand, trump_suit)

                team_score = t1s if team == 1 else t2s
                opp_score = t2s if team == 1 else t1s

                if b in DOUBLING_BIDS:
                    # Actual doubling action
                    if b in ("hokomclose", "hokomopen", "double", "beforeyou"):
                        doubling_level += 1
                    elif b == "triple":
                        doubling_level = max(doubling_level, 3)
                    elif b == "qahwa":
                        doubling_level = 99

                    gem = ev.get("gem", doubling_level - 1)
                    round_won = (round_won_by == team)
                    gp_earned = gp_t1 if team == 1 else gp_t2
                    gp_lost = gp_t2 if team == 1 else gp_t1

                    record = {
                        "game_id": game_name,
                        "round_idx": round_idx + 1,
                        "action": b,
                        "action_type": "double",
                        "doubling_level": doubling_level,
                        "gem_value": gem,
                        "player_seat": seat,
                        "is_bidding_team": is_bidding_team,
                        "hand_cards": hand,
                        "hand_metrics": metrics,
                        "game_mode": game_mode,
                        "trump_suit": trump_suit,
                        "team_score_before": team_score,
                        "opponent_score_before": opp_score,
                        "score_differential": team_score - opp_score,
                        "points_to_win": 152 - team_score,
                        "round_won": round_won,
                        "gp_earned": gp_earned if round_won else 0,
                        "gp_lost": gp_lost if not round_won else 0,
                        "khasara": gp_t1 == 0 or gp_t2 == 0,
                        "is_human": not is_bot,
                    }
                    records.append(record)

                elif b == "pass" and in_doubling_phase:
                    # Doubling opportunity NOT taken
                    record = {
                        "game_id": game_name,
                        "round_idx": round_idx + 1,
                        "action": "pass_on_double",
                        "action_type": "pass",
                        "doubling_level": doubling_level,
                        "gem_value": ev.get("gem", 0),
                        "player_seat": seat,
                        "is_bidding_team": is_bidding_team,
                        "hand_cards": hand,
                        "hand_metrics": metrics,
                        "game_mode": game_mode,
                        "trump_suit": trump_suit,
                        "team_score_before": team_score,
                        "opponent_score_before": opp_score,
                        "score_differential": team_score - opp_score,
                        "points_to_win": 152 - team_score,
                        "round_won": (round_won_by == team) if result else None,
                        "gp_earned": 0,
                        "gp_lost": 0,
                        "khasara": False,
                        "is_human": not is_bot,
                    }
                    records.append(record)

    return records


def compute_kelly(p_win: float, odds: float) -> float:
    """Compute Kelly fraction: f* = (p*b - q) / b."""
    if odds <= 0:
        return 0.0
    q = 1 - p_win
    return (p_win * odds - q) / odds


def build_thresholds(records: list[dict]) -> dict:
    """Build doubling analysis thresholds."""
    human = [r for r in records if r["is_human"]]
    doubles = [r for r in human if r["action_type"] == "double"]
    passes = [r for r in human if r["action_type"] == "pass"]

    # Win rate by doubling level
    level_stats = defaultdict(lambda: {"count": 0, "wins": 0})
    for r in doubles:
        level = r["doubling_level"]
        level_stats[level]["count"] += 1
        if r["round_won"]:
            level_stats[level]["wins"] += 1

    win_by_level = {}
    for level, stats in sorted(level_stats.items()):
        pct = stats["wins"] / stats["count"] * 100 if stats["count"] > 0 else 0
        win_by_level[str(level)] = {
            "count": stats["count"],
            "wins": stats["wins"],
            "win_pct": round(pct, 1),
        }

    # Doubling by score differential
    diff_buckets = defaultdict(lambda: {"doubles": 0, "passes": 0})
    for r in human:
        diff = r["score_differential"]
        if diff <= -50: bucket = "far_behind_-50"
        elif diff <= -20: bucket = "behind_-20_to_-50"
        elif diff < 0: bucket = "slightly_behind_0_to_-20"
        elif diff == 0: bucket = "tied"
        elif diff <= 20: bucket = "slightly_ahead_0_to_20"
        elif diff <= 50: bucket = "ahead_20_to_50"
        else: bucket = "far_ahead_50+"
        if r["action_type"] == "double":
            diff_buckets[bucket]["doubles"] += 1
        else:
            diff_buckets[bucket]["passes"] += 1

    diff_analysis = {}
    for bucket, stats in sorted(diff_buckets.items()):
        total = stats["doubles"] + stats["passes"]
        pct = stats["doubles"] / total * 100 if total > 0 else 0
        diff_analysis[bucket] = {
            "doubles": stats["doubles"],
            "passes": stats["passes"],
            "total": total,
            "double_pct": round(pct, 1),
        }

    # Hand strength vs doubling
    strength_buckets = defaultdict(lambda: {"doubles": 0, "passes": 0})
    for r in human:
        hc = r["hand_metrics"]["high_cards"]
        key = "high_cards_{}".format(hc)
        if r["action_type"] == "double":
            strength_buckets[key]["doubles"] += 1
        else:
            strength_buckets[key]["passes"] += 1

    strength_analysis = {}
    for key, stats in sorted(strength_buckets.items()):
        total = stats["doubles"] + stats["passes"]
        pct = stats["doubles"] / total * 100 if total > 0 else 0
        strength_analysis[key] = {
            "doubles": stats["doubles"],
            "passes": stats["passes"],
            "total": total,
            "double_pct": round(pct, 1),
        }

    # Kelly Criterion for each doubling decision
    kelly_records = []
    for r in doubles:
        level = r["doubling_level"]
        # Base GP: 26 for SUN, 16 for HOKUM (approximate)
        base = 26 if r["game_mode"] == "SUN" else 16
        potential_gain = base * level  # Approximate
        potential_loss = base * level

        # Odds = gain/loss ratio (simplified)
        odds = 1.0  # Symmetric for doubling

        # Estimate p_win from overall win rate at this level
        level_data = level_stats.get(level, {"count": 0, "wins": 0})
        p_win = level_data["wins"] / level_data["count"] if level_data["count"] > 0 else 0.5

        f_star = compute_kelly(p_win, odds)

        kelly_records.append({
            "game_id": r["game_id"],
            "round_idx": r["round_idx"],
            "level": level,
            "action": r["action"],
            "p_win": round(p_win, 3),
            "odds": odds,
            "kelly_fraction": round(f_star, 4),
            "round_won": r["round_won"],
            "score_diff": r["score_differential"],
        })

    return {
        "win_rate_by_level": win_by_level,
        "doubling_by_score_differential": diff_analysis,
        "hand_strength_vs_doubling": strength_analysis,
        "kelly_validation": kelly_records,
    }


def generate_report(records: list[dict], thresholds: dict) -> str:
    """Generate Kelly analysis markdown report."""
    human = [r for r in records if r["is_human"]]
    doubles = [r for r in human if r["action_type"] == "double"]
    passes = [r for r in human if r["action_type"] == "pass"]

    lines = [
        "# Doubling & Risk Management Report",
        "",
        "## Summary",
        "",
        "- **Total doubling-phase events**: N={}".format(len(human)),
        "- **Actual doubles**: {} ({:.1f}%)".format(
            len(doubles), len(doubles) / len(human) * 100 if human else 0),
        "- **Passed on doubling**: {} ({:.1f}%)".format(
            len(passes), len(passes) / len(human) * 100 if human else 0),
        "- **Games**: 109 professional sessions",
        "",
    ]

    # Action distribution
    action_dist = Counter(r["action"] for r in doubles)
    lines.append("## Doubling Action Distribution")
    lines.append("")
    lines.append("| Action | Count |")
    lines.append("|:---|---:|")
    for action, count in action_dist.most_common():
        lines.append("| {} | {} |".format(action, count))
    lines.append("")

    # Win rate by level
    lines.append("## Win Rate by Doubling Level")
    lines.append("")
    lines.append("| Level | Count | Wins | Win% |")
    lines.append("|:---|---:|---:|---:|")
    for level, data in sorted(thresholds["win_rate_by_level"].items()):
        lines.append("| {} | {} | {} | {}% |".format(
            level, data["count"], data["wins"], data["win_pct"]))
    lines.append("")

    # Score differential
    lines.append("## Doubling by Score Differential")
    lines.append("")
    lines.append("| Context | Doubles | Passes | Total | Double% |")
    lines.append("|:---|---:|---:|---:|---:|")
    for key, data in thresholds["doubling_by_score_differential"].items():
        lines.append("| {} | {} | {} | {} | {}% |".format(
            key, data["doubles"], data["passes"], data["total"], data["double_pct"]))
    lines.append("")

    # Hand strength
    lines.append("## Hand Strength vs Doubling")
    lines.append("")
    lines.append("| High Cards | Doubles | Passes | Total | Double% |")
    lines.append("|:---|---:|---:|---:|---:|")
    for key, data in sorted(thresholds["hand_strength_vs_doubling"].items()):
        lines.append("| {} | {} | {} | {} | {}% |".format(
            key, data["doubles"], data["passes"], data["total"], data["double_pct"]))
    lines.append("")

    # Kelly validation
    kelly = thresholds["kelly_validation"]
    if kelly:
        avg_f = sum(k["kelly_fraction"] for k in kelly) / len(kelly)
        lines.append("## Kelly Criterion Validation")
        lines.append("")
        lines.append("- **Doubling decisions analyzed**: N={}".format(len(kelly)))
        lines.append("- **Average Kelly fraction f***: {:.4f}".format(avg_f))
        lines.append("- **Interpretation**: f* > 0 means doubling is profitable on average")
        lines.append("")

        # Are pros close to Kelly-optimal?
        positive_kelly = sum(1 for k in kelly if k["kelly_fraction"] > 0)
        lines.append("- **Positive f* decisions**: {} ({:.1f}%)".format(
            positive_kelly, positive_kelly / len(kelly) * 100))
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Mission 3: Doubling & Risk Management Database")
    print("=" * 60)

    bot_moves = load_bot_moves()
    print("\nLoading games...")
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
    print("  Loaded {} games".format(len(games)))

    print("\nExtracting doubling records...")
    records = extract_doubling_records(games, bot_moves)
    print("  Total records: {}".format(len(records)))
    doubles = [r for r in records if r["action_type"] == "double"]
    passes = [r for r in records if r["action_type"] == "pass"]
    print("  Doubles: {}, Passes: {}".format(len(doubles), len(passes)))

    print("\nBuilding thresholds...")
    thresholds = build_thresholds(records)

    print("Generating report...")
    report = generate_report(records, thresholds)

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    db_path = TRAINING_DIR / "pro_doubling_database.json"
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump({"summary": {"total": len(records), "doubles": len(doubles),
                                "passes": len(passes)},
                    "records": records}, f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(db_path))

    thresh_path = TRAINING_DIR / "doubling_thresholds.json"
    with open(thresh_path, "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(thresh_path))

    report_path = TRAINING_DIR / "kelly_analysis_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("  ✅ {}".format(report_path))


if __name__ == "__main__":
    main()
