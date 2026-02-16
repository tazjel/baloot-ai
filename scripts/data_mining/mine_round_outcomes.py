"""Mission 5: Round Outcome Predictors.

Builds a comprehensive dataset connecting hand distributions, bidding,
and strategic choices to round outcomes for win probability estimation.

Produces:
  - round_outcomes.json: All round summaries with 4 hands + outcome
  - win_probability_model.json: P(win) lookup tables
  - outcome_analysis_report.md: Insights
"""
from __future__ import annotations

import json
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


def decode_bitmask(bitmask: int) -> list[int]:
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


def hand_metrics(hand: list[int], trump_suit: str | None) -> dict:
    """Compute comprehensive hand metrics."""
    suits = defaultdict(list)
    aces = kings = queens = jacks = 0
    pts_sun = pts_hokum = 0
    for idx in hand:
        info = card_idx_to_info(idx)
        r, s = info["rank"], info["suit"]
        suits[s].append(r)
        if r == "A": aces += 1
        elif r == "K": kings += 1
        elif r == "Q": queens += 1
        elif r == "J": jacks += 1
        pts_sun += PTS_SUN.get(r, 0)
        pts_hokum += PTS_HOKUM.get(r, 0)

    trump_count = len(suits.get(trump_suit, [])) if trump_suit else 0
    all_suits = ["♠", "♥", "♣", "♦"]
    suit_lens = {s: len(suits.get(s, [])) for s in all_suits}
    voids = sum(1 for s in all_suits if suit_lens[s] == 0)
    singletons = sum(1 for s in all_suits if suit_lens[s] == 1)
    longest = max(suit_lens.values()) if suit_lens else 0

    return {
        "trump_count": trump_count,
        "aces": aces, "kings": kings, "queens": queens, "jacks": jacks,
        "high_cards": aces + kings + queens + jacks,
        "point_value_sun": pts_sun,
        "point_value_hokum": pts_hokum,
        "voids": voids,
        "singletons": singletons,
        "longest_suit": longest,
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


def get_bid_type(events: list[dict]) -> str:
    """Get the winning bid type."""
    for ev in events:
        if ev.get("e") == 2:
            b = ev.get("b", "")
            if b in ("hokom", "sun", "ashkal", "hokom2", "turntosun"):
                return b
    return "unknown"


def get_multiplier(events: list[dict], mode: str) -> int:
    level = 1
    for ev in events:
        if ev.get("e") != 2: continue
        b = ev.get("b", "")
        if b in ("hokomclose", "beforeyou", "hokomopen"):
            level += 1
        elif b == "triple":
            level = max(level, 3)
        elif b == "qahwa":
            level = 99
        elif b in ("double", "redouble"):
            level = 2
    return min(level, 99)


def count_tricks_per_team(events: list[dict]) -> tuple[int, int]:
    """Count tricks won by each team by tracking card plays and trick boundaries."""
    t1_tricks = t2_tricks = 0
    trick_cards = []

    for ev in events:
        if ev.get("e") == 4:
            trick_cards.append(ev)
        elif ev.get("e") == 6:
            # Trick boundary — the winner is the leader of the next trick
            # We use the result to count, but approximate here
            p = ev.get("p")
            if p is not None and p > 0:
                team = player_team(p)
                if team == 1:
                    t1_tricks += 1
                else:
                    t2_tricks += 1
            trick_cards = []

    return t1_tricks, t2_tricks


def extract_round_outcomes(games: list[dict]) -> list[dict]:
    """Extract comprehensive round summaries."""
    records = []

    for game in games:
        game_name = game.get("n", game.get("_filename", "unknown"))

        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])

            # Get hands
            all_hands = {}
            for ev in events:
                if ev.get("e") == 15:
                    bhr = ev.get("bhr", [])
                    for si in range(min(4, len(bhr))):
                        all_hands[si + 1] = decode_bitmask(bhr[si])
                    break

            if not all_hands or len(all_hands) < 4:
                continue

            # Get round info
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
            bid_type = get_bid_type(events)
            multiplier = get_multiplier(events, game_mode)
            bidding_team = player_team(bidder_seat) if bidder_seat > 0 else 0

            # Result
            result = None
            for ev in events:
                if ev.get("e") == 12:
                    result = ev.get("rs", {})
                    break

            if result is None:
                continue  # Skip waraq rounds

            winner_team = result.get("w", 0)
            p1_raw = result.get("p1", 0)
            p2_raw = result.get("p2", 0)
            gp_t1 = result.get("s1", 0)
            gp_t2 = result.get("s2", 0)
            kbt = result.get("kbt", 0)
            khasara = (gp_t1 == 0 or gp_t2 == 0) and not kbt
            r1_decls = result.get("r1", [])
            r2_decls = result.get("r2", [])

            # Count tricks
            t1_tricks, t2_tricks = count_tricks_per_team(events)

            # Compute hand metrics for all 4 players
            player_metrics = {}
            for seat in range(1, 5):
                player_metrics[seat] = hand_metrics(all_hands.get(seat, []), trump_suit)

            # Team 1 = seats 1,3; Team 2 = seats 2,4
            m1 = player_metrics[1]
            m3 = player_metrics[3]
            m2 = player_metrics[2]
            m4 = player_metrics[4]

            # Bidder and partner metrics
            if bidding_team == 1:
                bidder_m = player_metrics.get(bidder_seat, m1)
                partner_seat = 3 if bidder_seat == 1 else 1
                partner_m = player_metrics.get(partner_seat, m3)
                defender_m1 = m2
                defender_m2 = m4
            else:
                bidder_m = player_metrics.get(bidder_seat, m2)
                partner_seat = 4 if bidder_seat == 2 else 2
                partner_m = player_metrics.get(partner_seat, m4)
                defender_m1 = m1
                defender_m2 = m3

            record = {
                "game_id": game_name,
                "round_idx": round_idx + 1,
                "team1_hands": [all_hands.get(1, []), all_hands.get(3, [])],
                "team2_hands": [all_hands.get(2, []), all_hands.get(4, [])],
                "floor_card": fc,
                "game_mode": game_mode,
                "trump_suit": trump_suit,
                "bidding_team": bidding_team,
                "bidder_seat": bidder_seat,
                "bid_type": bid_type,
                "multiplier": multiplier,
                "team1_score_before": t1s,
                "team2_score_before": t2s,
                # Bidder metrics
                "bidder_trump_count": bidder_m["trump_count"],
                "bidder_high_cards": bidder_m["high_cards"],
                "bidder_aces": bidder_m["aces"],
                "bidder_point_total_sun": bidder_m["point_value_sun"],
                "bidder_point_total_hokum": bidder_m["point_value_hokum"],
                "partner_trump_count": partner_m["trump_count"],
                "partner_high_cards": partner_m["high_cards"],
                "combined_trump": bidder_m["trump_count"] + partner_m["trump_count"],
                "combined_aces": bidder_m["aces"] + partner_m["aces"],
                "combined_high_cards": bidder_m["high_cards"] + partner_m["high_cards"],
                # Defender metrics
                "defender_combined_trump": defender_m1["trump_count"] + defender_m2["trump_count"],
                "defender_combined_aces": defender_m1["aces"] + defender_m2["aces"],
                "defender_combined_high_cards": defender_m1["high_cards"] + defender_m2["high_cards"],
                # Outcome
                "winner_team": winner_team,
                "bidder_won": winner_team == bidding_team,
                "team1_tricks": t1_tricks,
                "team2_tricks": t2_tricks,
                "team1_raw_points": p1_raw,
                "team2_raw_points": p2_raw,
                "team1_gp": gp_t1,
                "team2_gp": gp_t2,
                "khasara": khasara,
                "kaboot": bool(kbt),
                "declarations": {
                    "r1": [{"n": d.get("n"), "val": d.get("val")} for d in r1_decls],
                    "r2": [{"n": d.get("n"), "val": d.get("val")} for d in r2_decls],
                },
            }
            records.append(record)

    return records


def build_win_probability_model(records: list[dict]) -> dict:
    """Build P(win) lookup tables from outcomes."""
    # P(bidder wins | combined_trump, combined_high_cards, game_mode)
    hokum_lookup = defaultdict(lambda: {"total": 0, "wins": 0})
    sun_lookup = defaultdict(lambda: {"total": 0, "wins": 0})

    # P(bidder wins | combined_trump) - simplified
    trump_win = defaultdict(lambda: {"total": 0, "wins": 0})

    # Khasara predictors
    khasara_lookup = defaultdict(lambda: {"total": 0, "khasara": 0})

    # Mode comparison
    mode_win = defaultdict(lambda: {"total": 0, "wins": 0})

    # Score influence
    score_win = defaultdict(lambda: {"total": 0, "wins": 0})

    for r in records:
        mode = r["game_mode"]
        ct = r["combined_trump"]
        ch = r["combined_high_cards"]
        won = r["bidder_won"]

        key = "{}t_{}h".format(ct, ch)

        if mode == "HOKUM":
            hokum_lookup[key]["total"] += 1
            if won: hokum_lookup[key]["wins"] += 1
        else:
            sun_lookup[key]["total"] += 1
            if won: sun_lookup[key]["wins"] += 1

        # Simplified trump model
        trump_win[str(ct)]["total"] += 1
        if won: trump_win[str(ct)]["wins"] += 1

        # Khasara
        khasara_key = "{}t_{}h_{}a".format(ct, ch, r["combined_aces"])
        khasara_lookup[khasara_key]["total"] += 1
        if r["kaboot"]: khasara_lookup[khasara_key]["khasara"] += 1

        # Mode comparison
        mode_key = "{}_{}h".format(mode, ch)
        mode_win[mode_key]["total"] += 1
        if won: mode_win[mode_key]["wins"] += 1

        # Score influence
        t1s = r["team1_score_before"]
        t2s = r["team2_score_before"]
        bt = r["bidding_team"]
        bidder_score = t1s if bt == 1 else t2s
        opp_score = t2s if bt == 1 else t1s
        diff = bidder_score - opp_score

        if diff <= -30: sbucket = "far_behind"
        elif diff < 0: sbucket = "behind"
        elif diff == 0: sbucket = "tied"
        elif diff <= 30: sbucket = "ahead"
        else: sbucket = "far_ahead"
        score_win[sbucket]["total"] += 1
        if won: score_win[sbucket]["wins"] += 1

    def serialize(lookup):
        out = {}
        for k, v in sorted(lookup.items()):
            total = v["total"]
            wins = v.get("wins", v.get("khasara", 0))
            pct = wins / total * 100 if total > 0 else 0
            out[k] = {"total": total, "wins": wins, "win_pct": round(pct, 1)}
        return out

    return {
        "hokum_win_prob": serialize(hokum_lookup),
        "sun_win_prob": serialize(sun_lookup),
        "win_by_combined_trump": serialize(trump_win),
        "kaboot_predictors": serialize(khasara_lookup),
        "mode_comparison": serialize(mode_win),
        "score_influence": serialize(score_win),
    }


def generate_report(records: list[dict], model: dict) -> str:
    """Generate outcome analysis report."""
    lines = [
        "# Round Outcome Analysis Report",
        "",
        "## Summary",
        "",
        "- **Total rounds analyzed**: N={}".format(len(records)),
        "- **HOKUM rounds**: {}".format(sum(1 for r in records if r["game_mode"] == "HOKUM")),
        "- **SUN rounds**: {}".format(sum(1 for r in records if r["game_mode"] == "SUN")),
        "- **Bidder won**: {} ({:.1f}%)".format(
            sum(1 for r in records if r["bidder_won"]),
            sum(1 for r in records if r["bidder_won"]) / len(records) * 100 if records else 0),
        "- **Kaboot**: {} ({:.1f}%)".format(
            sum(1 for r in records if r["kaboot"]),
            sum(1 for r in records if r["kaboot"]) / len(records) * 100 if records else 0),
        "",
    ]

    # Win probability by combined trump
    lines.append("## Win Probability by Combined Trump Count")
    lines.append("")
    lines.append("| Combined Trump | Total | Wins | Win% |")
    lines.append("|:---|---:|---:|---:|")
    for key, data in sorted(model["win_by_combined_trump"].items(), key=lambda x: int(x[0])):
        if data["total"] >= 3:
            lines.append("| {} | {} | {} | {}% |".format(
                key, data["total"], data["wins"], data["win_pct"]))
    lines.append("")

    # Mode comparison
    lines.append("## Mode Comparison (Win% by high cards)")
    lines.append("")
    lines.append("| Mode + High Cards | Total | Wins | Win% |")
    lines.append("|:---|---:|---:|---:|")
    for key, data in sorted(model["mode_comparison"].items()):
        if data["total"] >= 5:
            lines.append("| {} | {} | {} | {}% |".format(
                key, data["total"], data["wins"], data["win_pct"]))
    lines.append("")

    # Score influence
    lines.append("## Score Influence on Bidder Win Rate")
    lines.append("")
    lines.append("| Score Context | Total | Wins | Win% |")
    lines.append("|:---|---:|---:|---:|")
    for key in ["far_behind", "behind", "tied", "ahead", "far_ahead"]:
        data = model["score_influence"].get(key, {"total": 0, "wins": 0, "win_pct": 0})
        lines.append("| {} | {} | {} | {}% |".format(
            key, data["total"], data["wins"], data["win_pct"]))
    lines.append("")

    # Hokum win prob details (high sample)
    lines.append("## HOKUM Win Probability (trump × high_cards)")
    lines.append("")
    lines.append("| Key | Total | Wins | Win% |")
    lines.append("|:---|---:|---:|---:|")
    for key, data in sorted(model["hokum_win_prob"].items(), key=lambda x: -x[1]["total"]):
        if data["total"] >= 5:
            lines.append("| {} | {} | {} | {}% |".format(
                key, data["total"], data["wins"], data["win_pct"]))
    lines.append("")

    # Sun win prob details
    lines.append("## SUN Win Probability (trump × high_cards)")
    lines.append("")
    lines.append("| Key | Total | Wins | Win% |")
    lines.append("|:---|---:|---:|---:|")
    for key, data in sorted(model["sun_win_prob"].items(), key=lambda x: -x[1]["total"]):
        if data["total"] >= 5:
            lines.append("| {} | {} | {} | {}% |".format(
                key, data["total"], data["wins"], data["win_pct"]))
    lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Mission 5: Round Outcome Predictors")
    print("=" * 60)

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

    print("\nExtracting round outcomes...")
    records = extract_round_outcomes(games)
    print("  Total rounds: {}".format(len(records)))
    print("  HOKUM: {}".format(sum(1 for r in records if r["game_mode"] == "HOKUM")))
    print("  SUN: {}".format(sum(1 for r in records if r["game_mode"] == "SUN")))

    print("\nBuilding win probability model...")
    model = build_win_probability_model(records)

    print("Generating report...")
    report = generate_report(records, model)

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    db_path = TRAINING_DIR / "round_outcomes.json"
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump({"summary": {"total_rounds": len(records)}, "records": records},
                  f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(db_path))

    model_path = TRAINING_DIR / "win_probability_model.json"
    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(model_path))

    report_path = TRAINING_DIR / "outcome_analysis_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("  ✅ {}".format(report_path))


if __name__ == "__main__":
    main()
