"""Mission 2: Professional Card Play Database.

Extracts every card play decision with complete game context:
- Player's hand BEFORE play (reconstructed by tracking)
- Legal moves (reconstructed from Baloot rules)
- Trick context (cards on table, current winner)
- Game state (tricks/points won by each team)
- Outcome (won trick, trick points, round won)

Filters BOT moves using move_labels.json.

Produces:
  - pro_card_play_database.json: Raw decision records (HUMAN only)
  - lead_frequency_table.json: Lead preferences
  - play_patterns_report.md: Human-readable analysis
  - endgame_positions.json: Solvable endgame states (last 3 tricks)
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "gbaloot" / "data" / "archive_captures" / "mobile_export" / "savedGames"
TRAINING_DIR = ROOT / "gbaloot" / "data" / "training"

# Card mapping
SOURCE_SUITS = {0: "♠", 1: "♥", 2: "♣", 3: "♦"}
SOURCE_RANKS = {5: "7", 6: "8", 7: "9", 8: "10", 9: "J", 10: "Q", 11: "K", 12: "A"}
VALID_RANK_RANGE = range(5, 13)

PTS_SUN = {"7": 0, "8": 0, "9": 0, "J": 2, "Q": 3, "K": 4, "10": 10, "A": 11}
PTS_HOKUM = {"7": 0, "8": 0, "Q": 3, "K": 4, "10": 10, "A": 11, "9": 14, "J": 20}

# Rank orders for trick resolution
ORDER_SUN = ["7", "8", "9", "J", "Q", "K", "10", "A"]
ORDER_HOKUM = ["7", "8", "Q", "K", "10", "A", "9", "J"]


def decode_bitmask(bitmask: int) -> list[int]:
    cards = []
    for idx in range(52):
        if idx % 13 not in VALID_RANK_RANGE:
            continue
        if bitmask & (1 << idx):
            cards.append(idx)
    return sorted(cards)


def card_suit(idx: int) -> str:
    return SOURCE_SUITS.get(idx // 13, "?")


def card_rank(idx: int) -> str:
    return SOURCE_RANKS.get(idx % 13, "?")


def card_name(idx: int) -> str:
    return "{}{}".format(card_rank(idx), card_suit(idx))


def card_points(idx: int, mode: str) -> int:
    rank = card_rank(idx)
    if mode == "HOKUM":
        return PTS_HOKUM.get(rank, 0)
    return PTS_SUN.get(rank, 0)


def player_team(seat: int) -> int:
    return 1 if seat in (1, 3) else 2


def partner_seat(seat: int) -> int:
    return {1: 3, 2: 4, 3: 1, 4: 2}.get(seat, 0)


def compute_legal_moves(hand: list[int], lead_suit: str | None,
                        trump_suit: str | None) -> list[int]:
    """Compute legal moves following Baloot rules.

    Rules:
    - If leading: any card is legal
    - If following: must follow lead suit if possible
    - If void in lead suit: can play any card (including trump)
    """
    if lead_suit is None:
        return list(hand)  # Leading: any card

    # Must follow lead suit if possible
    follow_cards = [c for c in hand if card_suit(c) == lead_suit]
    if follow_cards:
        return follow_cards

    # Void in lead suit: can play anything
    return list(hand)


def compute_trick_winner(plays: list[tuple[int, int]], mode: str,
                         trump_suit: str | None) -> int:
    """Compute which seat wins the trick.

    Args:
        plays: list of (seat, card_idx) in play order
        mode: "SUN" or "HOKUM"
        trump_suit: trump suit symbol or None for SUN

    Returns: winning seat number
    """
    if not plays:
        return 0

    lead_suit = card_suit(plays[0][1])
    best_seat = plays[0][0]
    best_strength = -1

    for seat, cidx in plays:
        c_suit = card_suit(cidx)
        c_rank = card_rank(cidx)
        strength = -1

        if mode == "HOKUM" and trump_suit and c_suit == trump_suit:
            strength = 100 + ORDER_HOKUM.index(c_rank) if c_rank in ORDER_HOKUM else 100
        elif c_suit == lead_suit:
            strength = ORDER_SUN.index(c_rank) if c_rank in ORDER_SUN else 0

        if strength > best_strength:
            best_strength = strength
            best_seat = seat

    return best_seat


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


def extract_card_plays(games: list[dict], bot_moves: set) -> tuple[list[dict], list[dict]]:
    """Extract all card play decisions with full context.

    Returns: (play_records, endgame_positions)
    """
    play_records = []
    endgame_positions = []

    for game in games:
        game_name = game.get("n", game.get("_filename", "unknown"))

        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])

            # Get initial hands
            initial_hands = {}
            for ev in events:
                if ev.get("e") == 15:
                    bhr = ev.get("bhr", [])
                    for si in range(min(4, len(bhr))):
                        initial_hands[si + 1] = set(decode_bitmask(bhr[si]))
                    break

            if len(initial_hands) < 4:
                continue

            fc = None
            for ev in events:
                if ev.get("e") == 1:
                    fc = ev.get("fc")
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

            round_winner = result.get("w", 0) if result else 0

            # Track state as we walk through events
            current_hands = {s: set(h) for s, h in initial_hands.items()}
            trick_number = 0
            trick_plays = []  # list of (seat, card_idx) for current trick
            all_played_cards = []  # all cards played so far
            tricks_won = {1: 0, 2: 0}  # team -> tricks won
            points_won = {1: 0, 2: 0}  # team -> points won
            trump_played_count = 0

            for ev_idx, ev in enumerate(events):
                if ev.get("e") != 4:
                    # Track trick boundaries
                    if ev.get("e") == 6:
                        # Trick completed — compute winner from played cards
                        if trick_plays:
                            winner_seat = compute_trick_winner(
                                trick_plays, game_mode, trump_suit)
                            winner_team = player_team(winner_seat)
                            tricks_won[winner_team] += 1

                            # Compute trick points
                            trick_pts = sum(
                                card_points(c, game_mode) for _, c in trick_plays)
                            points_won[winner_team] += trick_pts

                        trick_plays = []
                        trick_number += 1
                    continue

                seat = ev.get("p", 0)
                card_idx = ev.get("c", -1)

                if seat < 1 or seat > 4 or card_idx < 0:
                    continue

                # Position in trick (1=leader, 2-4=followers)
                position_in_trick = len(trick_plays) + 1

                # Lead suit (None if this player is leading)
                lead_suit = None
                if trick_plays:
                    lead_suit = card_suit(trick_plays[0][1])

                # Current winner of trick so far
                current_winner = None
                if trick_plays:
                    current_winner = compute_trick_winner(
                        trick_plays, game_mode, trump_suit)

                # Hand before this play
                hand_before = sorted(current_hands.get(seat, set()))

                # Legal moves
                legal = compute_legal_moves(hand_before, lead_suit, trump_suit)

                # Check if BOT
                is_bot = (game_name, round_idx + 1, ev_idx) in bot_moves
                is_human = not is_bot

                # Team info
                team = player_team(seat)
                my_tricks = tricks_won[team]
                opp_tricks = tricks_won[3 - team]
                my_points = points_won[team]
                opp_points = points_won[3 - team]
                is_bidding_team = (team == bidding_team)

                # Cards on table
                cards_on_table = [c for _, c in trick_plays]

                # Is partner currently winning?
                partner_winning = False
                if current_winner is not None:
                    partner_winning = player_team(current_winner) == team

                # Card being played
                played_suit = card_suit(card_idx)
                played_rank = card_rank(card_idx)
                is_trump = (played_suit == trump_suit) if trump_suit else False

                # Is this a discard? (void in lead suit, not playing trump)
                is_discard = (lead_suit is not None and
                              played_suit != lead_suit and
                              not is_trump)

                # The effective trick number (1-indexed)
                eff_trick = trick_number + 1

                record = {
                    "game_id": game_name,
                    "round_idx": round_idx + 1,
                    "trick_number": eff_trick,
                    "position_in_trick": position_in_trick,
                    "card_played": card_idx,
                    "card_name": card_name(card_idx),
                    "card_suit": played_suit,
                    "card_rank": played_rank,
                    "hand_before": hand_before,
                    "legal_moves": legal,
                    "num_options": len(legal),
                    "cards_on_table": cards_on_table,
                    "lead_suit": lead_suit,
                    "current_winner": current_winner,
                    "partner_winning": partner_winning,
                    "game_mode": game_mode,
                    "trump_suit": trump_suit,
                    "tricks_won_my_team": my_tricks,
                    "tricks_won_opponent": opp_tricks,
                    "points_my_team": my_points,
                    "points_opponent": opp_points,
                    "cards_played_so_far": list(all_played_cards),
                    "cards_remaining": 32 - len(all_played_cards),
                    "trump_played_count": trump_played_count,
                    "partner_seat": partner_seat(seat),
                    "is_bidding_team": is_bidding_team,
                    "is_leader": position_in_trick == 1,
                    "is_trump_play": is_trump,
                    "is_discard": is_discard,
                    "round_won": (round_winner == team) if result else None,
                    "is_human": is_human,
                    "player_seat": seat,
                }
                play_records.append(record)

                # Track endgame positions (last 3 tricks = cards_remaining <= 12)
                if eff_trick >= 6 and position_in_trick == 1:
                    # Snapshot all 4 hands for endgame
                    endgame = {
                        "game_id": game_name,
                        "round_idx": round_idx + 1,
                        "trick_number": eff_trick,
                        "hands": {str(s): sorted(h) for s, h in current_hands.items()},
                        "game_mode": game_mode,
                        "trump_suit": trump_suit,
                        "leader": seat,
                        "tricks_won_t1": tricks_won[1],
                        "tricks_won_t2": tricks_won[2],
                        "points_t1": points_won[1],
                        "points_t2": points_won[2],
                        "bidding_team": bidding_team,
                        "round_won_by": round_winner,
                    }
                    endgame_positions.append(endgame)

                # Update state
                current_hands[seat].discard(card_idx)
                all_played_cards.append(card_idx)
                if is_trump:
                    trump_played_count += 1

                trick_plays.append((seat, card_idx))

    return play_records, endgame_positions


def build_lead_frequency(records: list[dict]) -> dict:
    """Build lead card frequency table."""
    human_leads = [r for r in records if r["is_human"] and r["is_leader"]]

    # Lead by rank
    rank_counter = Counter(r["card_rank"] for r in human_leads)
    total_leads = len(human_leads)

    lead_by_rank = {}
    for rank, count in rank_counter.most_common():
        lead_by_rank[rank] = {
            "count": count,
            "pct": round(count / total_leads * 100, 1) if total_leads > 0 else 0,
        }

    # Lead by trick number
    lead_by_trick = defaultdict(lambda: Counter())
    for r in human_leads:
        lead_by_trick[r["trick_number"]][r["card_rank"]] += 1

    trick_leads = {}
    for trick, ranks in sorted(lead_by_trick.items()):
        total = sum(ranks.values())
        trick_leads[str(trick)] = {
            r: {"count": c, "pct": round(c / total * 100, 1)}
            for r, c in ranks.most_common(3)
        }

    # Lead trump vs non-trump (HOKUM)
    hokum_leads = [r for r in human_leads if r["game_mode"] == "HOKUM"]
    trump_leads = sum(1 for r in hokum_leads if r["is_trump_play"])
    trump_lead_pct = trump_leads / len(hokum_leads) * 100 if hokum_leads else 0

    # Lead by position (bidder vs defender)
    bidder_leads = [r for r in human_leads if r["is_bidding_team"]]
    defender_leads = [r for r in human_leads if not r["is_bidding_team"]]

    bidder_rank_dist = Counter(r["card_rank"] for r in bidder_leads)
    defender_rank_dist = Counter(r["card_rank"] for r in defender_leads)

    return {
        "total_leads": total_leads,
        "lead_by_rank": lead_by_rank,
        "lead_by_trick_number": trick_leads,
        "hokum_trump_lead_pct": round(trump_lead_pct, 1),
        "hokum_trump_leads": trump_leads,
        "hokum_total_leads": len(hokum_leads),
        "bidder_lead_ranks": {r: c for r, c in bidder_rank_dist.most_common()},
        "defender_lead_ranks": {r: c for r, c in defender_rank_dist.most_common()},
    }


def generate_report(records: list[dict], lead_freq: dict) -> str:
    """Generate play patterns analysis report."""
    human = [r for r in records if r["is_human"]]
    leaders = [r for r in human if r["is_leader"]]
    followers = [r for r in human if not r["is_leader"]]

    lines = [
        "# Professional Card Play Analysis Report",
        "",
        "## Summary",
        "",
        "- **Total card plays**: N={}".format(len(human)),
        "- **Leading plays**: {} ({:.1f}%)".format(
            len(leaders), len(leaders) / len(human) * 100 if human else 0),
        "- **Following plays**: {} ({:.1f}%)".format(
            len(followers), len(followers) / len(human) * 100 if human else 0),
        "- **HOKUM plays**: {}".format(sum(1 for r in human if r["game_mode"] == "HOKUM")),
        "- **SUN plays**: {}".format(sum(1 for r in human if r["game_mode"] == "SUN")),
        "",
    ]

    # Lead card frequency
    lines.append("## Lead Card Frequency")
    lines.append("")
    lines.append("| Rank | Count | % |")
    lines.append("|:---|---:|---:|")
    for rank, data in sorted(lead_freq["lead_by_rank"].items(),
                              key=lambda x: -x[1]["count"]):
        lines.append("| {} | {} | {}% |".format(rank, data["count"], data["pct"]))
    lines.append("")

    lines.append("### HOKUM: Trump Lead Rate")
    lines.append("")
    lines.append("- Trump leads: {}/{} ({:.1f}%)".format(
        lead_freq["hokum_trump_leads"],
        lead_freq["hokum_total_leads"],
        lead_freq["hokum_trump_lead_pct"]))
    lines.append("")

    # Follow play patterns
    partner_wins = [r for r in followers if r["partner_winning"]]
    opp_wins = [r for r in followers if not r["partner_winning"] and r["current_winner"]]

    if partner_wins:
        # When partner winning, do they play high or low?
        pw_high = sum(1 for r in partner_wins if r["card_rank"] in ("A", "K", "10"))
        pw_low = sum(1 for r in partner_wins if r["card_rank"] in ("7", "8", "9"))
        lines.append("## Follow Play Patterns")
        lines.append("")
        lines.append("### When Partner is Winning")
        lines.append("")
        lines.append("- Play high (A/K/10): {} ({:.1f}%)".format(
            pw_high, pw_high / len(partner_wins) * 100))
        lines.append("- Play low (7/8/9): {} ({:.1f}%)".format(
            pw_low, pw_low / len(partner_wins) * 100))
        lines.append("- **Interpretation**: Pros {} when partner is winning".format(
            "play LOW" if pw_low > pw_high else "play HIGH"))
        lines.append("")

    if opp_wins:
        ow_high = sum(1 for r in opp_wins if r["card_rank"] in ("A", "K", "10"))
        ow_low = sum(1 for r in opp_wins if r["card_rank"] in ("7", "8", "9"))
        lines.append("### When Opponent is Winning")
        lines.append("")
        lines.append("- Play high (A/K/10): {} ({:.1f}%)".format(
            ow_high, ow_high / len(opp_wins) * 100))
        lines.append("- Play low (7/8/9): {} ({:.1f}%)".format(
            ow_low, ow_low / len(opp_wins) * 100))
        lines.append("")

    # Trump usage
    hokum_follows = [r for r in followers if r["game_mode"] == "HOKUM"]
    void_plays = [r for r in hokum_follows
                  if r["lead_suit"] and not any(card_suit(c) == r["lead_suit"]
                                                 for c in r["hand_before"])]
    if void_plays:
        trumped = sum(1 for r in void_plays if r["is_trump_play"])
        discarded = sum(1 for r in void_plays if r["is_discard"])
        lines.append("## Trump Usage (HOKUM, void in lead suit)")
        lines.append("")
        lines.append("- Total void situations: {}".format(len(void_plays)))
        lines.append("- Trumped: {} ({:.1f}%)".format(
            trumped, trumped / len(void_plays) * 100 if void_plays else 0))
        lines.append("- Discarded: {} ({:.1f}%)".format(
            discarded, discarded / len(void_plays) * 100 if void_plays else 0))
        lines.append("")

        # Trump by trick number
        trump_by_trick = defaultdict(lambda: {"total": 0, "trumped": 0})
        for r in void_plays:
            t = r["trick_number"]
            trump_by_trick[t]["total"] += 1
            if r["is_trump_play"]:
                trump_by_trick[t]["trumped"] += 1

        lines.append("### Trump Frequency by Trick Number")
        lines.append("")
        lines.append("| Trick | Void Situations | Trumped | Trump% |")
        lines.append("|:---|---:|---:|---:|")
        for t, data in sorted(trump_by_trick.items()):
            pct = data["trumped"] / data["total"] * 100 if data["total"] > 0 else 0
            lines.append("| {} | {} | {} | {:.1f}% |".format(
                t, data["total"], data["trumped"], pct))
        lines.append("")

    # Discard patterns
    discards = [r for r in human if r["is_discard"]]
    if discards:
        lines.append("## Discard Patterns (void in lead suit, not trumping)")
        lines.append("")
        lines.append("- Total discards: {}".format(len(discards)))
        discard_ranks = Counter(r["card_rank"] for r in discards)
        lines.append("")
        lines.append("| Rank Discarded | Count | % |")
        lines.append("|:---|---:|---:|")
        for rank, count in discard_ranks.most_common():
            lines.append("| {} | {} | {:.1f}% |".format(
                rank, count, count / len(discards) * 100))
        lines.append("")

    # Endgame play (tricks 6-8)
    endgame_plays = [r for r in human if r["trick_number"] >= 6]
    if endgame_plays:
        lines.append("## Endgame Play (Tricks 6-8)")
        lines.append("")
        lines.append("- Total endgame plays: {}".format(len(endgame_plays)))
        lines.append("- Average options: {:.1f}".format(
            sum(r["num_options"] for r in endgame_plays) / len(endgame_plays)))
        forced = sum(1 for r in endgame_plays if r["num_options"] == 1)
        lines.append("- Forced plays (1 option): {} ({:.1f}%)".format(
            forced, forced / len(endgame_plays) * 100))
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Mission 2: Professional Card Play Database")
    print("=" * 60)

    bot_moves = load_bot_moves()
    print("\n  BOT moves: {}".format(len(bot_moves)))

    print("Loading games...")
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

    print("\nExtracting card play decisions (with hand tracking)...")
    all_records, endgame_positions = extract_card_plays(games, bot_moves)
    human_records = [r for r in all_records if r["is_human"]]
    print("  Total card plays: {}".format(len(all_records)))
    print("  Human plays: {}".format(len(human_records)))
    print("  BOT plays excluded: {}".format(len(all_records) - len(human_records)))
    print("  Endgame positions: {}".format(len(endgame_positions)))

    print("\nBuilding lead frequency table...")
    lead_freq = build_lead_frequency(human_records)

    print("Generating report...")
    report = generate_report(human_records, lead_freq)

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    # Save card play database (HUMAN only)
    db_path = TRAINING_DIR / "pro_card_play_database.json"
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_plays": len(all_records),
                "human_plays": len(human_records),
                "bot_plays_excluded": len(all_records) - len(human_records),
                "games": len(games),
            },
            "records": human_records,
        }, f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(db_path))

    lead_path = TRAINING_DIR / "lead_frequency_table.json"
    with open(lead_path, "w", encoding="utf-8") as f:
        json.dump(lead_freq, f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(lead_path))

    report_path = TRAINING_DIR / "play_patterns_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("  ✅ {}".format(report_path))

    endgame_path = TRAINING_DIR / "endgame_positions.json"
    with open(endgame_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {"total_positions": len(endgame_positions)},
            "positions": endgame_positions,
        }, f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(endgame_path))

    # Quick summary
    print("\n--- Quick Summary ---")
    leaders = [r for r in human_records if r["is_leader"]]
    print("  Leads: {}".format(len(leaders)))
    print("  Follows: {}".format(len(human_records) - len(leaders)))
    rank_dist = Counter(r["card_rank"] for r in leaders)
    print("  Top lead ranks: {}".format(rank_dist.most_common(5)))


if __name__ == "__main__":
    main()
