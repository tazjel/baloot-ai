"""Mission 1: Professional Bidding Database.

Extracts every bidding decision from 109 professional mobile app games
with full hand metrics, context, and outcomes.

Produces:
  - pro_bidding_database.json: Raw decision records (~12,000+)
  - bidding_thresholds.json: (trump_count x high_cards) matrix + Sun profile
  - bidding_analysis_report.md: Human-readable analysis with actionable thresholds

Uses move_labels.json to exclude BOT bids.
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

# Card mapping (from card_mapping.py)
SOURCE_SUITS = {0: "♠", 1: "♥", 2: "♣", 3: "♦"}
SOURCE_RANKS = {5: "7", 6: "8", 7: "9", 8: "10", 9: "J", 10: "Q", 11: "K", 12: "A"}
VALID_RANK_RANGE = range(5, 13)

# Point values
PTS_SUN = {"7": 0, "8": 0, "9": 0, "J": 2, "Q": 3, "K": 4, "10": 10, "A": 11}
PTS_HOKUM = {"7": 0, "8": 0, "Q": 3, "K": 4, "10": 10, "A": 11, "9": 14, "J": 20}

# Bids that represent an actual contract bid (not pass/transition)
CONTRACT_BIDS = {"hokom", "sun", "ashkal", "hokom2", "turntosun",
                 "clubs", "hearts", "spades", "diamonds"}
PASS_BIDS = {"pass", "wala", "thany", "waraq"}
DOUBLING_BIDS = {"double", "redouble", "hokomclose", "hokomopen",
                 "beforeyou", "triple", "qahwa"}

# Archive ts → suit symbol mapping
TS_TO_SUIT = {1: "♥", 2: "♣", 3: "♦", None: "♠", 0: "♠"}


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
    """Convert card index to rank/suit info."""
    suit_idx = idx // 13
    rank_idx = idx % 13
    return {
        "suit": SOURCE_SUITS.get(suit_idx, "?"),
        "rank": SOURCE_RANKS.get(rank_idx, "?"),
        "suit_idx": suit_idx,
    }


def compute_hand_metrics(hand_cards: list[int], trump_suit: str | None,
                         mode: str) -> dict:
    """Compute hand strength metrics."""
    suits = defaultdict(list)
    aces = 0
    kings = 0
    queens = 0
    jacks = 0
    point_value_sun = 0
    point_value_hokum = 0

    for idx in hand_cards:
        info = card_idx_to_info(idx)
        rank = info["rank"]
        suit = info["suit"]
        suits[suit].append(rank)

        if rank == "A":
            aces += 1
        elif rank == "K":
            kings += 1
        elif rank == "Q":
            queens += 1
        elif rank == "J":
            jacks += 1

        point_value_sun += PTS_SUN.get(rank, 0)
        point_value_hokum += PTS_HOKUM.get(rank, 0)

    suit_lengths = {s: len(ranks) for s, ranks in suits.items()}
    all_suits = ["♠", "♥", "♣", "♦"]
    voids = sum(1 for s in all_suits if suit_lengths.get(s, 0) == 0)
    singletons = sum(1 for s in all_suits if suit_lengths.get(s, 0) == 1)
    longest_suit = max(suit_lengths.values()) if suit_lengths else 0

    trump_count = 0
    if trump_suit and trump_suit in suits:
        trump_count = len(suits[trump_suit])

    high_cards = aces + kings + queens + jacks

    return {
        "trump_count": trump_count,
        "aces": aces,
        "kings": kings,
        "queens": queens,
        "jacks": jacks,
        "high_cards": high_cards,
        "point_value_sun": point_value_sun,
        "point_value_hokum": point_value_hokum,
        "voids": voids,
        "singletons": singletons,
        "longest_suit": longest_suit,
        "suit_distribution": suit_lengths,
    }


def resolve_trump_suit(events: list[dict], fc: int | None) -> str | None:
    """Resolve the trump suit from bid events and floor card."""
    suit_bids = {"clubs": "♣", "hearts": "♥", "spades": "♠", "diamonds": "♦"}

    for ev in events:
        if ev.get("e") != 2:
            continue
        b = ev.get("b", "")
        # Explicit suit selection
        if b in suit_bids:
            return suit_bids[b]
        # turntosun means no trump
        if b == "turntosun":
            return None
        if b == "sun" or b == "ashkal":
            return None

    # For R1 hokom, trump = floor card suit
    for ev in events:
        if ev.get("e") != 2:
            continue
        b = ev.get("b", "")
        if b == "hokom" and fc is not None:
            suit_idx = fc // 13
            return SOURCE_SUITS.get(suit_idx, None)

    return None


def resolve_game_mode(events: list[dict]) -> str:
    """Resolve game mode from bid events."""
    mode = "SUN"
    for ev in events:
        if ev.get("e") != 2:
            continue
        gm = ev.get("gm")
        if gm == 1 or gm == 3:
            mode = "SUN"
        elif gm == 2:
            mode = "HOKUM"
    return mode


def get_floor_card(events: list[dict]) -> int | None:
    """Get the floor card from e=1 event."""
    for ev in events:
        if ev.get("e") == 1:
            return ev.get("fc")
    return None


def get_round_start_scores(events: list[dict]) -> tuple[int, int]:
    """Get team scores at round start from e=1."""
    for ev in events:
        if ev.get("e") == 1:
            return ev.get("t1s", 0), ev.get("t2s", 0)
    return 0, 0


def get_dealer_seat(events: list[dict]) -> int:
    """Get dealer seat from e=1.p field."""
    for ev in events:
        if ev.get("e") == 1:
            return ev.get("p", 1)
    return 1


def get_bidder_seat(events: list[dict]) -> int:
    """Get the seat of the player who won the bid (rb field)."""
    rb = -1
    for ev in events:
        if ev.get("e") == 2:
            v = ev.get("rb", -1)
            if v > 0:
                rb = v
    return rb


def get_round_result(events: list[dict]) -> dict | None:
    """Get the e=12 round result."""
    for ev in events:
        if ev.get("e") == 12:
            return ev.get("rs", {})
    return None


def get_hokum_multiplier(events: list[dict]) -> int:
    """Derive HOKUM multiplier from bid events."""
    level = 1
    for evt in events:
        if evt.get("e") != 2:
            continue
        b = evt.get("b", "")
        if b in ("hokomclose", "beforeyou", "hokomopen"):
            level += 1
        elif b == "triple":
            level = max(level, 3)
        elif b == "qahwa":
            level = 99
    return min(level, 99)


def has_sun_radda(events: list[dict]) -> bool:
    """Check if SUN round has a radda."""
    return any(
        evt.get("e") == 2 and evt.get("b") in ("double", "redouble")
        for evt in events
    )


def player_team(seat: int) -> int:
    """Convert seat (1-4) to team (1 or 2)."""
    return 1 if seat in (1, 3) else 2


def load_bot_moves() -> set[tuple[str, int, int]]:
    """Load BOT move keys from move_labels.json.

    Returns set of (game, round, event_idx) for BOT moves.
    """
    labels_path = TRAINING_DIR / "move_labels.json"
    if not labels_path.exists():
        return set()
    with open(labels_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bot_keys = set()
    for m in data.get("labeled_moves", []):
        if m.get("player_type") == "BOT":
            bot_keys.add((m["game"], m["round"], m["event_idx"]))
    return bot_keys


def extract_bidding_records(games: list[dict], bot_moves: set) -> list[dict]:
    """Extract all bidding records from all games."""
    records = []

    for game in games:
        game_name = game.get("n", game.get("_filename", "unknown"))

        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])

            # Get deal info
            hands = {}
            for ev in events:
                if ev.get("e") == 15:
                    bhr = ev.get("bhr", [])
                    for seat_idx in range(min(4, len(bhr))):
                        hands[seat_idx + 1] = decode_bitmask(bhr[seat_idx])
                    break

            fc = get_floor_card(events)
            t1s, t2s = get_round_start_scores(events)
            dealer = get_dealer_seat(events)

            # Resolve game mode and trump from this round's bids
            game_mode = resolve_game_mode(events)
            trump_suit = resolve_trump_suit(events, fc)

            # Floor card suit
            fc_suit = None
            if fc is not None:
                fc_suit_idx = fc // 13
                fc_suit = SOURCE_SUITS.get(fc_suit_idx)

            # Get round result
            result = get_round_result(events)
            round_won_by = 0
            gp_t1 = 0
            gp_t2 = 0
            khasara = False
            was_doubled = False
            multiplier = 1
            bidding_team = 0

            if result:
                round_won_by = result.get("w", 0)
                gp_t1 = result.get("s1", 0)
                gp_t2 = result.get("s2", 0)
                bidding_team = result.get("b", 0)
                kbt = result.get("kbt", 0)

                if game_mode == "HOKUM":
                    multiplier = get_hokum_multiplier(events)
                    was_doubled = multiplier > 1
                elif game_mode == "SUN":
                    was_doubled = has_sun_radda(events)
                    multiplier = 2 if was_doubled else 1

                # Khasara: loser gets 0 GP
                khasara = (gp_t1 == 0 or gp_t2 == 0) and not kbt

            # Track bids to build previous_bids context
            bid_sequence = []
            bidding_round = 1

            for ev_idx, ev in enumerate(events):
                if ev.get("e") != 2:
                    continue

                b = ev.get("b", "")
                seat = ev.get("p", 0)

                # Track bidding round transitions
                if b == "thany":
                    bidding_round = 2
                    bid_sequence.append({"seat": seat, "bid": b})
                    continue

                # Skip non-bid transitions
                if b in ("waraq",):
                    bid_sequence.append({"seat": seat, "bid": b})
                    continue

                # Skip doubling bids — they go to Mission 3
                if b in DOUBLING_BIDS:
                    bid_sequence.append({"seat": seat, "bid": b})
                    continue

                # Check if this is a BOT move
                is_bot = (game_name, round_idx + 1, ev_idx) in bot_moves

                # Determine seat position relative to dealer
                seat_pos = ((seat - dealer - 1) % 4) + 1

                # Get hand for this player
                hand = hands.get(seat, [])

                # For R1 hokom, trump suit = floor card suit
                # For this specific bid, what's the relevant trump?
                if b == "hokom" and fc_suit:
                    bid_trump = fc_suit
                elif b in ("clubs", "hearts", "spades", "diamonds"):
                    suit_map = {"clubs": "♣", "hearts": "♥", "spades": "♠", "diamonds": "♦"}
                    bid_trump = suit_map[b]
                elif b in ("sun", "ashkal", "turntosun"):
                    bid_trump = None
                else:
                    bid_trump = fc_suit  # For passes, use floor card suit as context

                metrics = compute_hand_metrics(hand, bid_trump, game_mode)

                # Team info
                team = player_team(seat) if seat > 0 else 0
                team_score = t1s if team == 1 else t2s
                opp_score = t2s if team == 1 else t1s

                # Outcome
                round_won = (round_won_by == team) if result else None
                gp_earned = (gp_t1 if team == 1 else gp_t2) if result else 0

                is_contract_bid = b in CONTRACT_BIDS
                is_pass = b in PASS_BIDS

                record = {
                    "game_id": game_name,
                    "round_idx": round_idx + 1,
                    "player_seat": seat,
                    "hand_cards": hand,
                    "floor_card": fc,
                    "floor_card_suit": fc_suit,
                    "bid": b,
                    "is_contract_bid": is_contract_bid,
                    "is_pass": is_pass,
                    "bidding_round": bidding_round,
                    "seat_position": seat_pos,
                    "previous_bids": [x["bid"] for x in bid_sequence],
                    "game_mode_chosen": game_mode,
                    "trump_suit": trump_suit,
                    "team": team,
                    "team_score": team_score,
                    "opponent_score": opp_score,
                    "score_differential": team_score - opp_score,
                    **metrics,
                    "round_won": round_won,
                    "gp_earned": gp_earned,
                    "khasara": khasara,
                    "was_doubled": was_doubled,
                    "multiplier": multiplier,
                    "is_human": not is_bot,
                }
                records.append(record)
                bid_sequence.append({"seat": seat, "bid": b})

    return records


def build_threshold_matrix(records: list[dict]) -> dict:
    """Build bidding threshold matrix from records."""
    # Filter: human-only, R1 hokom bids + passes (before R2)
    hokum_matrix = defaultdict(lambda: {"bid": 0, "pass": 0, "win": 0})
    sun_profile = defaultdict(lambda: {"bid": 0, "total": 0})
    win_rate = defaultdict(lambda: {"bid": 0, "win": 0})
    position_stats = defaultdict(lambda: {"bid": 0, "pass": 0})
    score_bidding = defaultdict(lambda: {"bid": 0, "pass": 0})

    for r in records:
        if not r["is_human"]:
            continue
        if r["bid"] in DOUBLING_BIDS:
            continue

        trump_count = r["trump_count"]
        high_cards = r["high_cards"]
        seat_pos = r["seat_position"]
        diff = r["score_differential"]

        # Hokum threshold matrix (R1 only, hokom vs pass)
        if r["bidding_round"] == 1 and r["bid"] in ("hokom", "pass"):
            key = "{}t_{}h".format(trump_count, high_cards)
            if r["bid"] == "hokom":
                hokum_matrix[key]["bid"] += 1
                if r["round_won"]:
                    hokum_matrix[key]["win"] += 1
            else:
                hokum_matrix[key]["pass"] += 1

        # Sun bidding profile
        if r["bid"] == "sun":
            sun_profile["aces_{}".format(r["aces"])]["bid"] += 1
            sun_profile["pts_{}".format(r["point_value_sun"] // 10 * 10)]["bid"] += 1
            sun_profile["voids_{}".format(r["voids"])]["bid"] += 1
            sun_profile["longest_{}".format(r["longest_suit"])]["bid"] += 1

        # Win rate by hand strength (for contract bids)
        if r["is_contract_bid"] and r["round_won"] is not None:
            wkey = "{}t_{}h".format(trump_count, high_cards)
            win_rate[wkey]["bid"] += 1
            if r["round_won"]:
                win_rate[wkey]["win"] += 1

        # Position effect
        if r["bidding_round"] == 1:
            if r["is_contract_bid"]:
                position_stats["pos_{}".format(seat_pos)]["bid"] += 1
            elif r["is_pass"]:
                position_stats["pos_{}".format(seat_pos)]["pass"] += 1

        # Score-dependent bidding
        if diff <= -30:
            bucket = "far_behind"
        elif diff < 0:
            bucket = "slightly_behind"
        elif diff == 0:
            bucket = "tied"
        elif diff <= 30:
            bucket = "slightly_ahead"
        else:
            bucket = "far_ahead"

        if r["is_contract_bid"]:
            score_bidding[bucket]["bid"] += 1
        elif r["is_pass"]:
            score_bidding[bucket]["pass"] += 1

    # Convert to serializable format
    hokum_table = {}
    for key, val in sorted(hokum_matrix.items()):
        total = val["bid"] + val["pass"]
        bid_pct = val["bid"] / total * 100 if total > 0 else 0
        win_pct = val["win"] / val["bid"] * 100 if val["bid"] > 0 else 0
        hokum_table[key] = {
            "bids": val["bid"],
            "passes": val["pass"],
            "total": total,
            "bid_pct": round(bid_pct, 1),
            "win_pct_when_bid": round(win_pct, 1),
        }

    win_rate_table = {}
    for key, val in sorted(win_rate.items()):
        pct = val["win"] / val["bid"] * 100 if val["bid"] > 0 else 0
        win_rate_table[key] = {
            "bids": val["bid"],
            "wins": val["win"],
            "win_pct": round(pct, 1),
        }

    position_table = {}
    for key, val in sorted(position_stats.items()):
        total = val["bid"] + val["pass"]
        pct = val["bid"] / total * 100 if total > 0 else 0
        position_table[key] = {
            "bids": val["bid"],
            "passes": val["pass"],
            "total": total,
            "bid_pct": round(pct, 1),
        }

    score_table = {}
    for key, val in sorted(score_bidding.items()):
        total = val["bid"] + val["pass"]
        pct = val["bid"] / total * 100 if total > 0 else 0
        score_table[key] = {
            "bids": val["bid"],
            "passes": val["pass"],
            "total": total,
            "bid_pct": round(pct, 1),
        }

    return {
        "hokum_r1_threshold_matrix": hokum_table,
        "sun_profile": dict(sun_profile),
        "win_rate_by_hand_strength": win_rate_table,
        "position_effect": position_table,
        "score_dependent_bidding": score_table,
    }


def generate_report(records: list[dict], thresholds: dict) -> str:
    """Generate a markdown analysis report."""
    human_records = [r for r in records if r["is_human"]]
    contract_bids = [r for r in human_records if r["is_contract_bid"]]
    passes = [r for r in human_records if r["is_pass"]]

    lines = [
        "# Professional Bidding Analysis Report",
        "",
        "## Summary",
        "",
        "- **Total bid events analyzed**: N={}".format(len(human_records)),
        "- **Contract bids**: {} ({:.1f}%)".format(
            len(contract_bids),
            len(contract_bids) / len(human_records) * 100 if human_records else 0),
        "- **Passes**: {} ({:.1f}%)".format(
            len(passes),
            len(passes) / len(human_records) * 100 if human_records else 0),
        "- **Games**: 109 professional mobile app sessions",
        "- **BOT moves excluded**: Yes (from move_labels.json)",
        "",
    ]

    # Bid type distribution
    bid_counts = Counter(r["bid"] for r in human_records)
    lines.append("## Bid Type Distribution")
    lines.append("")
    lines.append("| Bid | Count | % |")
    lines.append("|:---|---:|---:|")
    for bid, count in bid_counts.most_common():
        pct = count / len(human_records) * 100
        lines.append("| {} | {} | {:.1f}% |".format(bid, count, pct))
    lines.append("")

    # Mode distribution
    mode_counts = Counter(r["game_mode_chosen"] for r in contract_bids)
    lines.append("## Mode Distribution (contract bids only)")
    lines.append("")
    for mode, count in mode_counts.most_common():
        lines.append("- **{}**: {} ({:.1f}%)".format(
            mode, count, count / len(contract_bids) * 100 if contract_bids else 0))
    lines.append("")

    # Hokum R1 threshold matrix
    lines.append("## Hokum R1 Bidding Threshold Matrix")
    lines.append("")
    lines.append("(trump_count × high_cards) → % of time pros bid Hokum in Round 1")
    lines.append("")
    lines.append("| Key | Bids | Passes | Total | Bid% | Win% (when bid) |")
    lines.append("|:---|---:|---:|---:|---:|---:|")
    hm = thresholds["hokum_r1_threshold_matrix"]
    for key in sorted(hm.keys(), key=lambda k: (int(k.split("t_")[0]), int(k.split("_")[1].rstrip("h")))):
        v = hm[key]
        if v["total"] >= 3:  # Min sample size
            lines.append("| {} | {} | {} | {} | {}% | {}% |".format(
                key, v["bids"], v["passes"], v["total"], v["bid_pct"], v["win_pct_when_bid"]))
    lines.append("")

    # Win rate by hand strength
    lines.append("## Win Rate by Hand Strength (all contract bids)")
    lines.append("")
    lines.append("| Key | Bids | Wins | Win% |")
    lines.append("|:---|---:|---:|---:|")
    wr = thresholds["win_rate_by_hand_strength"]
    for key in sorted(wr.keys(), key=lambda k: -wr[k]["bids"]):
        v = wr[key]
        if v["bids"] >= 5:
            lines.append("| {} | {} | {} | {}% |".format(
                key, v["bids"], v["wins"], v["win_pct"]))
    lines.append("")

    # Position effect
    lines.append("## Position Effect (R1 only)")
    lines.append("")
    lines.append("| Position | Bids | Passes | Total | Bid% |")
    lines.append("|:---|---:|---:|---:|---:|")
    for key, v in sorted(thresholds["position_effect"].items()):
        lines.append("| {} | {} | {} | {} | {}% |".format(
            key, v["bids"], v["passes"], v["total"], v["bid_pct"]))
    lines.append("")

    # Score-dependent bidding
    lines.append("## Score-Dependent Bidding")
    lines.append("")
    lines.append("| Score Context | Bids | Passes | Total | Bid% |")
    lines.append("|:---|---:|---:|---:|---:|")
    for key in ["far_behind", "slightly_behind", "tied", "slightly_ahead", "far_ahead"]:
        v = thresholds["score_dependent_bidding"].get(key, {"bids": 0, "passes": 0, "total": 0, "bid_pct": 0})
        lines.append("| {} | {} | {} | {} | {}% |".format(
            key, v["bids"], v["passes"], v["total"], v["bid_pct"]))
    lines.append("")

    # Sun bidding profile
    lines.append("## Sun Bidding Profile")
    lines.append("")
    sun_bids = [r for r in human_records if r["bid"] == "sun"]
    if sun_bids:
        ace_dist = Counter(r["aces"] for r in sun_bids)
        lines.append("### Aces in hand when bidding Sun")
        lines.append("")
        for aces, count in sorted(ace_dist.items()):
            lines.append("- {} aces: {} bids ({:.1f}%)".format(
                aces, count, count / len(sun_bids) * 100))
        lines.append("")

        pts_dist = Counter(r["point_value_sun"] for r in sun_bids)
        avg_pts = sum(r["point_value_sun"] for r in sun_bids) / len(sun_bids)
        lines.append("### Point value (SUN) when bidding Sun")
        lines.append("")
        lines.append("- Average: {:.1f}".format(avg_pts))
        lines.append("- Min: {}".format(min(r["point_value_sun"] for r in sun_bids)))
        lines.append("- Max: {}".format(max(r["point_value_sun"] for r in sun_bids)))
        lines.append("")

        void_dist = Counter(r["voids"] for r in sun_bids)
        lines.append("### Voids when bidding Sun")
        lines.append("")
        for v, count in sorted(void_dist.items()):
            lines.append("- {} voids: {} ({:.1f}%)".format(
                v, count, count / len(sun_bids) * 100))
        lines.append("")

    # Key thresholds for AI calibration
    lines.append("## Actionable Thresholds for AI Calibration")
    lines.append("")
    lines.append("### Hokum R1 Decision Boundaries")
    lines.append("")

    # Find threshold where bid% crosses 50%
    for key, v in sorted(hm.items(), key=lambda x: x[1]["bid_pct"]):
        if v["total"] >= 5 and v["bid_pct"] >= 50:
            lines.append("- **{}**: Pros bid {}% of the time (N={})".format(
                key, v["bid_pct"], v["total"]))

    lines.append("")
    lines.append("### Sun Minimum Requirements")
    lines.append("")
    if sun_bids:
        min_aces = min(r["aces"] for r in sun_bids)
        min_pts = min(r["point_value_sun"] for r in sun_bids)
        avg_high = sum(r["high_cards"] for r in sun_bids) / len(sun_bids)
        lines.append("- Minimum aces: {} (based on N={} Sun bids)".format(min_aces, len(sun_bids)))
        lines.append("- Minimum point value: {} (SUN scoring)".format(min_pts))
        lines.append("- Average high cards: {:.1f}".format(avg_high))

    lines.append("")
    return "\n".join(lines)


def main():
    """Run Mission 1: Professional Bidding Database."""
    print("=" * 60)
    print("Mission 1: Professional Bidding Database")
    print("=" * 60)

    # Load bot moves
    print("\nLoading BOT move labels...")
    bot_moves = load_bot_moves()
    print("  BOT moves to exclude: {}".format(len(bot_moves)))

    # Load games
    print("Loading games from {}...".format(ARCHIVE_DIR))
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

    # Extract records
    print("\nExtracting bidding records...")
    records = extract_bidding_records(games, bot_moves)
    print("  Total bid events: {}".format(len(records)))

    human_records = [r for r in records if r["is_human"]]
    bot_records = [r for r in records if not r["is_human"]]
    print("  Human bids: {}".format(len(human_records)))
    print("  BOT bids excluded: {}".format(len(bot_records)))

    contract = [r for r in human_records if r["is_contract_bid"]]
    passes = [r for r in human_records if r["is_pass"]]
    print("  Contract bids: {}".format(len(contract)))
    print("  Passes: {}".format(len(passes)))

    # Build thresholds
    print("\nBuilding threshold matrix...")
    thresholds = build_threshold_matrix(records)

    # Generate report
    print("Generating analysis report...")
    report = generate_report(records, thresholds)

    # Save outputs
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    db_path = TRAINING_DIR / "pro_bidding_database.json"
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_records": len(records),
                "human_records": len(human_records),
                "bot_records": len(bot_records),
                "contract_bids": len(contract),
                "passes": len(passes),
                "games": len(games),
            },
            "records": records,
        }, f, indent=2, ensure_ascii=False)
    print("  ✅ Saved: {}".format(db_path))

    thresh_path = TRAINING_DIR / "bidding_thresholds.json"
    with open(thresh_path, "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=2, ensure_ascii=False)
    print("  ✅ Saved: {}".format(thresh_path))

    report_path = TRAINING_DIR / "bidding_analysis_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("  ✅ Saved: {}".format(report_path))

    # Quick summary
    print("\n--- Quick Summary ---")
    bid_dist = Counter(r["bid"] for r in human_records)
    for bid, count in bid_dist.most_common(10):
        print("  {}: {}".format(bid, count))


if __name__ == "__main__":
    main()
