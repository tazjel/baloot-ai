"""Mission 4: Partnership Signaling Extraction.

Discovers if professional players use systematic signaling through
lead cards, discards, and count signals.

Produces:
  - lead_signals.json: Lead signal patterns
  - discard_signals.json: Discard signal patterns
  - signaling_analysis_report.md: Signal reliability analysis
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
RANK_ORDER = ["7", "8", "9", "J", "Q", "K", "10", "A"]

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


def player_team(seat: int) -> int:
    return 1 if seat in (1, 3) else 2


def partner_seat_fn(seat: int) -> int:
    return {1: 3, 2: 4, 3: 1, 4: 2}.get(seat, 0)


def compute_trick_winner(plays: list[tuple[int, int]], mode: str,
                         trump_suit: str | None) -> int:
    if not plays: return 0
    lead_suit = card_suit(plays[0][1])
    best_seat = plays[0][0]
    best_strength = -1
    for seat, cidx in plays:
        c_suit = card_suit(cidx)
        c_rank = card_rank(cidx)
        strength = -1
        if mode == "HOKUM" and trump_suit and c_suit == trump_suit:
            strength = 100 + (ORDER_HOKUM.index(c_rank) if c_rank in ORDER_HOKUM else 0)
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


def extract_signals(games: list[dict], bot_moves: set) -> tuple[list[dict], list[dict]]:
    """Extract lead signals and discard signals."""
    lead_signals = []
    discard_signals = []

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

            # Track state
            current_hands = {s: set(h) for s, h in initial_hands.items()}
            trick_plays = []
            trick_number = 0

            card_events = []
            for ev_idx, ev in enumerate(events):
                if ev.get("e") == 4:
                    card_events.append((ev_idx, ev))
                elif ev.get("e") == 6:
                    # Process completed trick
                    if len(trick_plays) == 4:
                        trick_number += 1
                        winner_seat = compute_trick_winner(
                            trick_plays, game_mode, trump_suit)
                        winner_team = player_team(winner_seat)

                        # Extract lead signal (position 1 = leader)
                        leader_seat = trick_plays[0][0]
                        lead_card = trick_plays[0][1]
                        lead_suit_played = card_suit(lead_card)
                        lead_rank_played = card_rank(lead_card)

                        # Leader's hand at the time of leading
                        # We need the hand BEFORE this trick, which we tracked
                        leader_hand_before = sorted(
                            current_hands.get(leader_seat, set()) | {lead_card})

                        # Cards of the led suit in leader's hand
                        leader_suit_cards = [c for c in leader_hand_before
                                             if card_suit(c) == lead_suit_played]
                        leader_suit_length = len(leader_suit_cards)
                        leader_has_ace = any(card_rank(c) == "A"
                                             for c in leader_suit_cards)

                        # Partner's response
                        ps = partner_seat_fn(leader_seat)
                        partner_card = None
                        partner_had_suit = False
                        for s, c in trick_plays:
                            if s == ps:
                                partner_card = c
                                # Check if partner had the led suit
                                partner_hand = current_hands.get(ps, set()) | {c}
                                partner_had_suit = any(
                                    card_suit(pc) == lead_suit_played
                                    for pc in partner_hand)
                                break

                        is_bot = any(
                            (game_name, round_idx + 1, eidx) in bot_moves
                            for eidx, _ in [(ce[0], ce[1]) for ce in card_events
                                             if ce[1].get("p") == leader_seat]
                        )

                        if not is_bot:
                            lead_signal = {
                                "game_id": game_name,
                                "round_idx": round_idx + 1,
                                "trick_number": trick_number,
                                "leader_seat": leader_seat,
                                "lead_card": lead_card,
                                "lead_card_name": card_name(lead_card),
                                "lead_card_rank": lead_rank_played,
                                "lead_card_suit": lead_suit_played,
                                "leader_hand": leader_hand_before,
                                "leader_suit_length": leader_suit_length,
                                "leader_has_ace": leader_has_ace,
                                "partner_response": partner_card,
                                "partner_response_name": card_name(partner_card) if partner_card else None,
                                "partner_had_suit": partner_had_suit,
                                "trick_won_by_team": winner_team == player_team(leader_seat),
                                "game_mode": game_mode,
                                "trump_suit": trump_suit,
                                "is_trump_lead": lead_suit_played == trump_suit if trump_suit else False,
                            }
                            lead_signals.append(lead_signal)

                        # Extract discard signals (followers who couldn't follow suit)
                        if len(trick_plays) >= 2:
                            lead_suit = card_suit(trick_plays[0][1])
                            for pos_idx, (s, c) in enumerate(trick_plays[1:], 2):
                                c_suit = card_suit(c)
                                if c_suit == lead_suit:
                                    continue  # Followed suit, no signal

                                # This is a discard/trump play
                                is_trump = (c_suit == trump_suit) if trump_suit else False
                                if is_trump:
                                    continue  # Trump play, not a discard signal

                                # Discard signal: void in lead suit
                                player_hand = sorted(
                                    current_hands.get(s, set()) | {c})

                                suits_in_hand = defaultdict(int)
                                for h_card in player_hand:
                                    suits_in_hand[card_suit(h_card)] += 1

                                # Check if discard is from shortest suit
                                c_suit_length = suits_in_hand.get(c_suit, 0)
                                min_suit_len = min(suits_in_hand.values()) if suits_in_hand else 0
                                discarded_from_shortest = c_suit_length == min_suit_len

                                # Check if discarded highest in that suit
                                same_suit_cards = [
                                    h for h in player_hand if card_suit(h) == c_suit]
                                if same_suit_cards:
                                    rank_indices = [
                                        ORDER_SUN.index(card_rank(h))
                                        for h in same_suit_cards
                                        if card_rank(h) in ORDER_SUN]
                                    my_rank_idx = ORDER_SUN.index(card_rank(c)) if card_rank(c) in ORDER_SUN else -1
                                    discarded_highest = my_rank_idx == max(rank_indices) if rank_indices else False
                                else:
                                    discarded_highest = True

                                is_bot2 = (game_name, round_idx + 1,
                                           card_events[pos_idx - 1][0] if pos_idx - 1 < len(card_events) else -1) in bot_moves

                                if not is_bot2:
                                    discard_signal = {
                                        "game_id": game_name,
                                        "round_idx": round_idx + 1,
                                        "trick_number": trick_number,
                                        "player_seat": s,
                                        "discarded_card": c,
                                        "discarded_card_name": card_name(c),
                                        "discarded_suit": c_suit,
                                        "discarded_rank": card_rank(c),
                                        "player_hand": player_hand,
                                        "suits_in_hand": dict(suits_in_hand),
                                        "led_suit": lead_suit,
                                        "game_mode": game_mode,
                                        "discarded_from_shortest_suit": discarded_from_shortest,
                                        "discarded_highest_in_suit": discarded_highest,
                                    }
                                    discard_signals.append(discard_signal)

                    # Reset trick
                    for s, c in trick_plays:
                        current_hands[s].discard(c)
                    trick_plays = []
                    card_events = []
                    continue

                if ev.get("e") == 4:
                    seat = ev.get("p", 0)
                    cidx = ev.get("c", -1)
                    if seat > 0 and cidx >= 0:
                        trick_plays.append((seat, cidx))

    return lead_signals, discard_signals


def analyze_lead_conventions(leads: list[dict]) -> dict:
    """Analyze lead conventions."""
    results = {}

    # When pros lead Ace, do they have A+K?
    ace_leads = [l for l in leads if l["lead_card_rank"] == "A"]
    if ace_leads:
        has_king = 0
        for l in ace_leads:
            lead_s = l["lead_card_suit"]
            hand_ranks = [card_rank(c) for c in l["leader_hand"]
                          if card_suit(c) == lead_s]
            if "K" in hand_ranks:
                has_king += 1
        results["ace_lead_has_king"] = {
            "total_ace_leads": len(ace_leads),
            "has_king": has_king,
            "pct": round(has_king / len(ace_leads) * 100, 1),
            "signal_reliable": has_king / len(ace_leads) > 0.6 if ace_leads else False,
        }

    # When pros lead low (7/8), are they from length?
    low_leads = [l for l in leads if l["lead_card_rank"] in ("7", "8")]
    if low_leads:
        from_length = sum(1 for l in low_leads if l["leader_suit_length"] >= 3)
        results["low_lead_from_length"] = {
            "total_low_leads": len(low_leads),
            "from_3_plus_length": from_length,
            "pct": round(from_length / len(low_leads) * 100, 1),
            "signal_reliable": from_length / len(low_leads) > 0.6 if low_leads else False,
        }

    # Lead rank by suit length
    length_lead = defaultdict(lambda: Counter())
    for l in leads:
        length_lead[l["leader_suit_length"]][l["lead_card_rank"]] += 1

    results["lead_rank_by_suit_length"] = {}
    for length, ranks in sorted(length_lead.items()):
        total = sum(ranks.values())
        results["lead_rank_by_suit_length"][str(length)] = {
            r: {"count": c, "pct": round(c / total * 100, 1)}
            for r, c in ranks.most_common(3)
        }

    # Trick win rate by lead rank
    win_by_rank = defaultdict(lambda: {"total": 0, "wins": 0})
    for l in leads:
        win_by_rank[l["lead_card_rank"]]["total"] += 1
        if l["trick_won_by_team"]:
            win_by_rank[l["lead_card_rank"]]["wins"] += 1

    results["win_rate_by_lead_rank"] = {}
    for rank, data in sorted(win_by_rank.items(), key=lambda x: -x[1]["total"]):
        pct = data["wins"] / data["total"] * 100 if data["total"] > 0 else 0
        results["win_rate_by_lead_rank"][rank] = {
            "total": data["total"],
            "wins": data["wins"],
            "win_pct": round(pct, 1),
        }

    return results


def analyze_discard_patterns(discards: list[dict]) -> dict:
    """Analyze discard signaling patterns."""
    results = {}

    if not discards:
        return results

    # Do discards signal suit preference?
    # High discard = strength? Or shedding?
    high_rank_discards = [d for d in discards
                          if d["discarded_rank"] in ("A", "K", "10")]
    low_rank_discards = [d for d in discards
                          if d["discarded_rank"] in ("7", "8", "9")]

    results["discard_rank_distribution"] = {
        "high_discards": len(high_rank_discards),
        "low_discards": len(low_rank_discards),
        "total": len(discards),
        "high_pct": round(len(high_rank_discards) / len(discards) * 100, 1),
        "low_pct": round(len(low_rank_discards) / len(discards) * 100, 1),
    }

    # Shortest suit preference
    from_shortest = sum(1 for d in discards if d["discarded_from_shortest_suit"])
    results["discard_from_shortest_suit"] = {
        "count": from_shortest,
        "total": len(discards),
        "pct": round(from_shortest / len(discards) * 100, 1),
        "signal_reliable": from_shortest / len(discards) > 0.6,
    }

    # Highest in suit preference
    highest = sum(1 for d in discards if d["discarded_highest_in_suit"])
    results["discard_highest_in_suit"] = {
        "count": highest,
        "total": len(discards),
        "pct": round(highest / len(discards) * 100, 1),
        "signal_reliable": highest / len(discards) > 0.6,
    }

    # Discard suit distribution
    suit_discards = Counter(d["discarded_suit"] for d in discards)
    results["discard_by_suit"] = {
        s: {"count": c, "pct": round(c / len(discards) * 100, 1)}
        for s, c in suit_discards.most_common()
    }

    return results


def generate_report(leads: list[dict], discards: list[dict],
                    lead_analysis: dict, discard_analysis: dict) -> str:
    """Generate signaling analysis report."""
    lines = [
        "# Partnership Signaling Analysis Report",
        "",
        "## Summary",
        "",
        "- **Lead signals analyzed**: N={}".format(len(leads)),
        "- **Discard signals analyzed**: N={}".format(len(discards)),
        "- **Signal threshold**: P > 60% = real signal (actionable)",
        "",
    ]

    # Lead conventions
    lines.append("## Lead Conventions")
    lines.append("")

    ak = lead_analysis.get("ace_lead_has_king", {})
    if ak:
        reliable = "✅ YES" if ak.get("signal_reliable") else "❌ NO"
        lines.append("### Ace Lead = A+K Signal?")
        lines.append("")
        lines.append("- When pros lead an Ace, they have K in same suit: **{}%** (N={})".format(
            ak["pct"], ak["total_ace_leads"]))
        lines.append("- Signal reliable (>60%): **{}**".format(reliable))
        lines.append("")

    low = lead_analysis.get("low_lead_from_length", {})
    if low:
        reliable = "✅ YES" if low.get("signal_reliable") else "❌ NO"
        lines.append("### Low Lead (7/8) = Length Signal?")
        lines.append("")
        lines.append("- When pros lead 7/8, they have 3+ of that suit: **{}%** (N={})".format(
            low["pct"], low["total_low_leads"]))
        lines.append("- Signal reliable (>60%): **{}**".format(reliable))
        lines.append("")

    # Win rate by lead rank
    wr = lead_analysis.get("win_rate_by_lead_rank", {})
    if wr:
        lines.append("### Win Rate by Lead Rank")
        lines.append("")
        lines.append("| Rank | Leads | Wins | Win% |")
        lines.append("|:---|---:|---:|---:|")
        for rank, data in sorted(wr.items(), key=lambda x: -x[1]["total"]):
            lines.append("| {} | {} | {} | {}% |".format(
                rank, data["total"], data["wins"], data["win_pct"]))
        lines.append("")

    # Lead by suit length
    lbl = lead_analysis.get("lead_rank_by_suit_length", {})
    if lbl:
        lines.append("### Lead Rank by Suit Length")
        lines.append("")
        for length, ranks in sorted(lbl.items()):
            top = list(ranks.items())[:2]
            top_str = ", ".join("{}: {}%".format(r, d["pct"]) for r, d in top)
            lines.append("- Length {}: {}".format(length, top_str))
        lines.append("")

    # Discard patterns
    lines.append("## Discard Patterns")
    lines.append("")

    dr = discard_analysis.get("discard_rank_distribution", {})
    if dr:
        lines.append("### Discard Rank Distribution")
        lines.append("")
        lines.append("- High discards (A/K/10): **{}%** (N={})".format(
            dr["high_pct"], dr["high_discards"]))
        lines.append("- Low discards (7/8/9): **{}%** (N={})".format(
            dr["low_pct"], dr["low_discards"]))
        lines.append("")

    shortest = discard_analysis.get("discard_from_shortest_suit", {})
    if shortest:
        reliable = "✅ YES" if shortest.get("signal_reliable") else "❌ NO"
        lines.append("### Discard from Shortest Suit?")
        lines.append("")
        lines.append("- Discarded from shortest suit: **{}%** (N={})".format(
            shortest["pct"], shortest["total"]))
        lines.append("- Signal reliable (>60%): **{}**".format(reliable))
        lines.append("")

    highest = discard_analysis.get("discard_highest_in_suit", {})
    if highest:
        reliable = "✅ YES" if highest.get("signal_reliable") else "❌ NO"
        lines.append("### Discard Highest in Suit?")
        lines.append("")
        lines.append("- Discarded highest card of suit: **{}%** (N={})".format(
            highest["pct"], highest["total"]))
        lines.append("- Signal reliable (>60%): **{}**".format(reliable))
        lines.append("")

    # Signal reliability summary
    lines.append("## Signal Reliability Summary")
    lines.append("")
    lines.append("| Signal | Reliability | Actionable? |")
    lines.append("|:---|---:|:---:|")

    if ak:
        lines.append("| Ace lead → has King | {}% | {} |".format(
            ak["pct"], "✅" if ak.get("signal_reliable") else "❌"))
    if low:
        lines.append("| Low lead → 3+ length | {}% | {} |".format(
            low["pct"], "✅" if low.get("signal_reliable") else "❌"))
    if shortest:
        lines.append("| Discard from shortest | {}% | {} |".format(
            shortest["pct"], "✅" if shortest.get("signal_reliable") else "❌"))
    if highest:
        lines.append("| Discard highest in suit | {}% | {} |".format(
            highest["pct"], "✅" if highest.get("signal_reliable") else "❌"))
    lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Mission 4: Partnership Signaling Extraction")
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

    print("\nExtracting signals...")
    lead_signals, discard_signals = extract_signals(games, bot_moves)
    print("  Lead signals: {}".format(len(lead_signals)))
    print("  Discard signals: {}".format(len(discard_signals)))

    print("\nAnalyzing lead conventions...")
    lead_analysis = analyze_lead_conventions(lead_signals)

    print("Analyzing discard patterns...")
    discard_analysis = analyze_discard_patterns(discard_signals)

    print("Generating report...")
    report = generate_report(lead_signals, discard_signals,
                             lead_analysis, discard_analysis)

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    lead_path = TRAINING_DIR / "lead_signals.json"
    with open(lead_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {"total": len(lead_signals)},
            "analysis": lead_analysis,
            "signals": lead_signals[:500],  # Sample to keep file size reasonable
        }, f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(lead_path))

    discard_path = TRAINING_DIR / "discard_signals.json"
    with open(discard_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {"total": len(discard_signals)},
            "analysis": discard_analysis,
            "signals": discard_signals[:500],
        }, f, indent=2, ensure_ascii=False)
    print("  ✅ {}".format(discard_path))

    report_path = TRAINING_DIR / "signaling_analysis_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("  ✅ {}".format(report_path))

    # Quick findings
    print("\n--- Key Findings ---")
    ak = lead_analysis.get("ace_lead_has_king", {})
    if ak:
        print("  Ace lead → has King: {}% (N={})".format(ak["pct"], ak["total_ace_leads"]))
    low = lead_analysis.get("low_lead_from_length", {})
    if low:
        print("  Low lead → 3+ length: {}% (N={})".format(low["pct"], low["total_low_leads"]))
    shortest = discard_analysis.get("discard_from_shortest_suit", {})
    if shortest:
        print("  Discard from shortest: {}% (N={})".format(shortest["pct"], shortest["total"]))


if __name__ == "__main__":
    main()
