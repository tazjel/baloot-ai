"""
Extract and analyze bidding patterns from Kammelna mobile archives.

Analyzes all bidding events (e=2) to answer key questions about:
1. Bidding order and dealer rotation
2. Round 1 vs Round 2 transitions
3. Pass mechanics (thany/wala/waraq)
4. Hokm vs Sun flow
5. Ashkal rules
6. Beforeyou (doubling) mechanics
7. Waraq (all-pass redeal) behavior
8. Face-up card (ts field) usage
9. Trump suit selection in Round 2
10. Doubling chain (hokomclose/hokomopen/triple/qahwa)

Usage:
    python scripts/tools/extract_bidding_patterns.py [archive_dir]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


# ─── Config ───────────────────────────────────────────────────────────
DEFAULT_ARCHIVE = "gbaloot/data/sync/2026-02-16/kammelna_export/savedGames"

# Bid type classifications
ROUND1_BIDS = {"pass", "hokom", "sun", "ashkal"}
ROUND2_TRANSITION = {"thany"}       # Dealer says "second round"
ROUND2_PASS = {"wala"}              # Pass in Round 2
ROUND2_BID_HOKUM = {"hokom2"}       # Intent to bid Hokum in R2
SUIT_BIDS = {"clubs", "diamonds", "hearts", "spades"}  # Explicit trump suit
SPECIAL_BIDS = {"ashkal", "turntosun", "waraq"}
DOUBLING_BIDS = {"hokomclose", "hokomopen", "double", "triple", "qahwa", "beforeyou"}
ALL_BID_TYPES = (
    ROUND1_BIDS | ROUND2_TRANSITION | ROUND2_PASS | ROUND2_BID_HOKUM
    | SUIT_BIDS | SPECIAL_BIDS | DOUBLING_BIDS
)

# Archive suit mapping: 1=spade, 2=clubs, 3=diamonds, 4=hearts
SUIT_NAMES = {1: "spades", 2: "clubs", 3: "diamonds", 4: "hearts"}


def load_sessions(archive_dir: Path) -> list[dict]:
    """Load all archive JSON files."""
    sessions = []
    for f in sorted(archive_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return sessions


def extract_bid_events(rnd: dict) -> list[dict]:
    """Extract bid events (e=2) from a round."""
    return [evt for evt in rnd.get("r", []) if evt.get("e") == 2]


def get_result(rnd: dict) -> dict | None:
    """Get the result event (e=12) from a round."""
    for evt in rnd.get("r", []):
        if evt.get("e") == 12:
            return evt.get("rs", {})
    return None


def classify_round(bid_events: list[dict]) -> dict:
    """Classify a bidding sequence into phases and extract key info."""
    info = {
        "r1_bids": [],         # Round 1 events
        "r2_transition": None, # thany event
        "r2_passes": [],       # wala events
        "r2_bids": [],         # hokom2 / suit bid events
        "contract_bid": None,  # The winning bid
        "doubling": [],        # hokomclose/hokomopen/double/triple/qahwa
        "ashkal": None,        # ashkal event
        "turntosun": None,     # turntosun event
        "is_waraq": False,     # All-pass redeal
        "has_sun_hijack": False,  # SUN bid overriding earlier HOKUM
        "beforeyou_events": [],  # beforeyou events
        "all_bids": bid_events,
    }

    phase = "R1"  # Start in Round 1
    hokum_bid_seen = False

    for evt in bid_events:
        b = evt.get("b", "")

        if b == "thany":
            phase = "R2_TRANSITION"
            info["r2_transition"] = evt
            continue

        if b == "wala":
            info["r2_passes"].append(evt)
            continue

        if b == "waraq":
            info["is_waraq"] = True
            continue

        if b == "hokom2":
            phase = "R2"
            info["r2_bids"].append(evt)
            continue

        if b in SUIT_BIDS:
            info["r2_bids"].append(evt)
            info["contract_bid"] = evt
            continue

        if b == "turntosun":
            info["turntosun"] = evt
            info["contract_bid"] = evt
            continue

        if b == "ashkal":
            info["ashkal"] = evt
            info["contract_bid"] = evt
            continue

        if b in DOUBLING_BIDS:
            info["doubling"].append(evt)
            if b == "beforeyou":
                info["beforeyou_events"].append(evt)
            continue

        # Regular Round 1 bids
        if phase == "R1":
            info["r1_bids"].append(evt)
            if b == "hokom":
                hokum_bid_seen = True
            if b == "sun":
                if hokum_bid_seen:
                    info["has_sun_hijack"] = True
                info["contract_bid"] = evt

        # Could be pass after contract in doubling phase
        if b == "pass" and phase != "R1":
            # Pass in doubling or post-contract
            pass

    # If no contract_bid set yet, check R1 for hokom
    if info["contract_bid"] is None:
        for evt in info["r1_bids"]:
            if evt.get("b") == "hokom":
                info["contract_bid"] = evt
                break

    return info


def analyze_bidding_order(sessions: list[dict]) -> dict:
    """Q1: Analyze bidding order and dealer rotation."""
    stats = {
        "total_rounds": 0,
        "r1_first_bidder_positions": Counter(),  # Position of first bidder in R1
        "r1_bid_count_per_round": Counter(),  # How many bids in R1
        "dealer_rotation": [],  # Track dealer across rounds
    }

    for session in sessions:
        rounds = session.get("rs", [])
        prev_dealer = None
        for ri, rnd in enumerate(rounds):
            bids = extract_bid_events(rnd)
            if not bids:
                continue
            stats["total_rounds"] += 1

            # First bidder
            first_p = bids[0].get("p")
            stats["r1_first_bidder_positions"][first_p] += 1

            # Count R1 bids (before thany)
            r1_count = 0
            for evt in bids:
                if evt.get("b") == "thany":
                    break
                r1_count += 1
            stats["r1_bid_count_per_round"][r1_count] += 1

            # Track dealer: the last person to bid in R1 (position 4 = dealer)
            # Actually we need to infer dealer from the bidding order
            # The player who says "thany" is the DEALER (they trigger round 2)
            for evt in bids:
                if evt.get("b") == "thany":
                    dealer = evt.get("p")
                    if prev_dealer is not None:
                        stats["dealer_rotation"].append((prev_dealer, dealer))
                    prev_dealer = dealer
                    break

    return stats


def analyze_round_transitions(sessions: list[dict]) -> dict:
    """Q2: Analyze Round 1 → Round 2 transitions."""
    stats = {
        "total_rounds": 0,
        "r1_only": 0,        # Contract won in R1
        "r1_to_r2": 0,       # Went to R2
        "waraq_rounds": 0,   # All-pass redeals
        "r2_outcomes": Counter(),  # What happened in R2
        "r1_contract_types": Counter(),
        "r2_contract_types": Counter(),
    }

    for session in sessions:
        for rnd in session.get("rs", []):
            bids = extract_bid_events(rnd)
            if not bids:
                continue
            stats["total_rounds"] += 1

            info = classify_round(bids)

            if info["is_waraq"]:
                stats["waraq_rounds"] += 1
                stats["r1_to_r2"] += 1
                stats["r2_outcomes"]["waraq"] += 1
                continue

            if info["r2_transition"] is not None:
                stats["r1_to_r2"] += 1
                # What happened in R2?
                if info["contract_bid"]:
                    b = info["contract_bid"].get("b", "")
                    if b in SUIT_BIDS:
                        stats["r2_outcomes"]["hokum_suit"] += 1
                        stats["r2_contract_types"][b] += 1
                    elif b == "sun":
                        stats["r2_outcomes"]["sun"] += 1
                        stats["r2_contract_types"]["sun"] += 1
                    elif b == "turntosun":
                        stats["r2_outcomes"]["turntosun"] += 1
                        stats["r2_contract_types"]["turntosun"] += 1
                    elif b == "hokom2":
                        stats["r2_outcomes"]["hokom2_only"] += 1
                    else:
                        stats["r2_outcomes"]["other"] += 1
                else:
                    stats["r2_outcomes"]["no_contract"] += 1
            else:
                stats["r1_only"] += 1
                if info["contract_bid"]:
                    b = info["contract_bid"].get("b", "")
                    stats["r1_contract_types"][b] += 1

    return stats


def analyze_pass_mechanics(sessions: list[dict]) -> dict:
    """Q3: Analyze pass mechanics (thany/wala/waraq)."""
    stats = {
        "thany_count": 0,
        "thany_by_player": Counter(),  # Which seat says thany
        "wala_count": 0,
        "wala_patterns": Counter(),  # Number of walas before bid/waraq
        "waraq_count": 0,
        "waraq_wala_counts": [],  # How many walas preceded each waraq
        "r1_all_pass_count": 0,
        "r2_all_pass_count": 0,
    }

    for session in sessions:
        for rnd in session.get("rs", []):
            bids = extract_bid_events(rnd)
            info = classify_round(bids)

            if info["r2_transition"]:
                stats["thany_count"] += 1
                stats["thany_by_player"][info["r2_transition"].get("p")] += 1

            wala_count = len(info["r2_passes"])
            stats["wala_count"] += wala_count

            if info["is_waraq"]:
                stats["waraq_count"] += 1
                stats["waraq_wala_counts"].append(wala_count)

            if wala_count > 0:
                stats["wala_patterns"][wala_count] += 1

            # Check if R1 was all passes
            r1_passes = sum(1 for e in info["r1_bids"] if e.get("b") == "pass")
            if r1_passes == 4 and info["r2_transition"]:
                stats["r1_all_pass_count"] += 1

    return stats


def analyze_hokum_sun_flow(sessions: list[dict]) -> dict:
    """Q4: Analyze Hokum vs Sun bidding flow."""
    stats = {
        "total_contracted": 0,
        "hokum_r1": 0,     # Hokum won in R1
        "sun_r1": 0,       # Sun won in R1
        "ashkal_r1": 0,    # Ashkal in R1
        "hokum_r2": 0,     # Hokum won in R2 (with suit)
        "sun_r2": 0,       # Sun won in R2
        "turntosun": 0,    # Hokum bidder switches to Sun
        "sun_hijack": 0,   # Sun overrides Hokum bid
        "r1_hokum_then_sun": 0,  # Hokum bid then Sun in same R1
        "bidder_positions": Counter(),  # Position of winning bidder
        "mode_distribution": Counter(),
    }

    for session in sessions:
        for rnd in session.get("rs", []):
            bids = extract_bid_events(rnd)
            result = get_result(rnd)
            if not bids or not result:
                continue

            info = classify_round(bids)
            if info["is_waraq"]:
                continue

            if info["contract_bid"] is None:
                continue

            stats["total_contracted"] += 1
            cb = info["contract_bid"]
            b = cb.get("b", "")
            mode = result.get("m", 0)
            stats["mode_distribution"][mode] += 1
            stats["bidder_positions"][cb.get("p")] += 1

            has_r2 = info["r2_transition"] is not None

            if b == "hokom" and not has_r2:
                stats["hokum_r1"] += 1
            elif b == "sun" and not has_r2:
                stats["sun_r1"] += 1
                if info["has_sun_hijack"]:
                    stats["sun_hijack"] += 1
            elif b == "ashkal":
                stats["ashkal_r1"] += 1
            elif b in SUIT_BIDS:
                stats["hokum_r2"] += 1
            elif b == "sun" and has_r2:
                stats["sun_r2"] += 1
            elif b == "turntosun":
                stats["turntosun"] += 1

            if info["has_sun_hijack"]:
                stats["r1_hokum_then_sun"] += 1

    return stats


def analyze_ashkal(sessions: list[dict]) -> dict:
    """Q5: Analyze Ashkal rules."""
    stats = {
        "total_ashkal": 0,
        "ashkal_by_player": Counter(),
        "ashkal_after_hokum": 0,
        "ashkal_after_pass": 0,
        "ashkal_rb_values": Counter(),  # rb field = who becomes bidder
        "ashkal_original_hokum_player": [],  # Who bid hokom before ashkal
        "ashkal_ts_values": Counter(),
    }

    for session in sessions:
        for rnd in session.get("rs", []):
            bids = extract_bid_events(rnd)
            info = classify_round(bids)

            if info["ashkal"] is None:
                continue

            stats["total_ashkal"] += 1
            a = info["ashkal"]
            stats["ashkal_by_player"][a.get("p")] += 1
            stats["ashkal_rb_values"][a.get("rb")] += 1
            stats["ashkal_ts_values"][a.get("ts")] += 1

            # Check what preceded ashkal
            hokum_before = False
            hokum_player = None
            for evt in bids:
                if evt is a:
                    break
                if evt.get("b") == "hokom":
                    hokum_before = True
                    hokum_player = evt.get("p")

            if hokum_before:
                stats["ashkal_after_hokum"] += 1
                stats["ashkal_original_hokum_player"].append(hokum_player)
            else:
                stats["ashkal_after_pass"] += 1

    return stats


def analyze_doubling(sessions: list[dict]) -> dict:
    """Q6: Analyze doubling chain (hokomclose/hokomopen/double/beforeyou/triple/qahwa)."""
    stats = {
        "total_doubled_rounds": 0,
        "doubling_types": Counter(),
        "doubling_chains": Counter(),  # The sequence of doubling bids
        "hokomclose_by_player": Counter(),
        "hokomopen_by_player": Counter(),
        "double_by_player": Counter(),
        "beforeyou_by_player": Counter(),
        "triple_by_player": Counter(),
        "qahwa_by_player": Counter(),
        "beforeyou_after": Counter(),  # What preceded beforeyou
        "max_chain_length": 0,
        "hokomclose_team_relation": Counter(),  # opponent vs partner of bidder
        "hokomopen_team_relation": Counter(),
        "double_context": Counter(),  # sun_double vs hokum_double vs ashkal_double
    }

    for session in sessions:
        for rnd in session.get("rs", []):
            bids = extract_bid_events(rnd)
            info = classify_round(bids)

            if not info["doubling"]:
                continue

            stats["total_doubled_rounds"] += 1
            chain = tuple(e.get("b") for e in info["doubling"])
            stats["doubling_chains"][chain] += 1
            stats["max_chain_length"] = max(stats["max_chain_length"], len(chain))

            # Find the contract bidder for team analysis
            contract_bidder = None
            if info["contract_bid"]:
                contract_bidder = info["contract_bid"].get("rb")

            # Determine game mode for context
            result = get_result(rnd)
            mode = result.get("m", 0) if result else 0

            for evt in info["doubling"]:
                db = evt.get("b", "")
                dp = evt.get("p")
                stats["doubling_types"][db] += 1

                if db == "hokomclose":
                    stats["hokomclose_by_player"][dp] += 1
                    if contract_bidder:
                        same_team = (dp % 2) == (contract_bidder % 2)
                        stats["hokomclose_team_relation"]["same_team" if same_team else "opponent"] += 1
                elif db == "hokomopen":
                    stats["hokomopen_by_player"][dp] += 1
                    if contract_bidder:
                        same_team = (dp % 2) == (contract_bidder % 2)
                        stats["hokomopen_team_relation"]["same_team" if same_team else "opponent"] += 1
                elif db == "double":
                    stats["double_by_player"][dp] += 1
                    if mode == 1:
                        stats["double_context"]["sun"] += 1
                    elif mode == 3:
                        stats["double_context"]["ashkal"] += 1
                    else:
                        stats["double_context"]["hokum"] += 1
                elif db == "beforeyou":
                    stats["beforeyou_by_player"][dp] += 1
                elif db == "triple":
                    stats["triple_by_player"][dp] += 1
                elif db == "qahwa":
                    stats["qahwa_by_player"][dp] += 1

            # beforeyou context: what was the previous bid?
            for evt in info["beforeyou_events"]:
                idx = bids.index(evt)
                if idx > 0:
                    prev = bids[idx - 1].get("b", "")
                    stats["beforeyou_after"][prev] += 1

    return stats


def analyze_waraq_faceup(sessions: list[dict]) -> dict:
    """Q7-8: Analyze waraq (all-pass) and face-up card patterns."""
    stats = {
        "total_waraq": 0,
        "waraq_ts_values": Counter(),  # ts field in waraq rounds
        "total_rounds": 0,
        "ts_always_4": 0,  # How many rounds have ts=4
        "ts_changes_after_suit_bid": 0,
        "ts_values_in_r1": Counter(),
        "ts_values_after_suit": Counter(),
        "fc_field_rounds": 0,  # Rounds with fc (first card) field
    }

    for session in sessions:
        for rnd in session.get("rs", []):
            bids = extract_bid_events(rnd)
            if not bids:
                continue
            stats["total_rounds"] += 1

            info = classify_round(bids)

            # Track ts field values
            first_ts = bids[0].get("ts") if bids else None
            stats["ts_values_in_r1"][first_ts] += 1
            if first_ts == 4:
                stats["ts_always_4"] += 1

            # Track ts changes after suit bids
            for evt in bids:
                if evt.get("b") in SUIT_BIDS:
                    stats["ts_values_after_suit"][evt.get("ts")] += 1
                    if evt.get("ts") != first_ts:
                        stats["ts_changes_after_suit_bid"] += 1

            if info["is_waraq"]:
                stats["total_waraq"] += 1
                stats["waraq_ts_values"][first_ts] += 1

            # Check for fc field in any event
            for evt in rnd.get("r", []):
                if "fc" in evt:
                    stats["fc_field_rounds"] += 1
                    break

    return stats


def analyze_trump_selection(sessions: list[dict]) -> dict:
    """Q9: Analyze trump suit selection in R2."""
    stats = {
        "r2_suit_bids": Counter(),  # Which suits are chosen
        "r2_suit_after_hokom2": Counter(),  # Suit chosen by hokom2 bidder
        "turntosun_count": 0,
        "turntosun_after_hokom2": 0,
        "hokom2_without_suit": 0,  # hokom2 bid but no suit follow-up
        "hokom2_bidder_same_as_suit": 0,
        "hokom2_bidder_diff_from_suit": 0,
    }

    for session in sessions:
        for rnd in session.get("rs", []):
            bids = extract_bid_events(rnd)
            info = classify_round(bids)

            if not info["r2_transition"]:
                continue

            # Track hokom2 and subsequent suit bid
            hokom2_player = None
            for evt in bids:
                if evt.get("b") == "hokom2":
                    hokom2_player = evt.get("p")
                elif evt.get("b") in SUIT_BIDS:
                    stats["r2_suit_bids"][evt.get("b")] += 1
                    if hokom2_player:
                        suit_bidder = evt.get("p")
                        if suit_bidder == hokom2_player:
                            stats["hokom2_bidder_same_as_suit"] += 1
                        else:
                            stats["hokom2_bidder_diff_from_suit"] += 1
                elif evt.get("b") == "turntosun":
                    stats["turntosun_count"] += 1
                    if hokom2_player:
                        stats["turntosun_after_hokom2"] += 1

            # hokom2 without suit bid
            if hokom2_player:
                has_suit = any(e.get("b") in SUIT_BIDS for e in bids)
                has_turntosun = any(e.get("b") == "turntosun" for e in bids)
                if not has_suit and not has_turntosun:
                    stats["hokom2_without_suit"] += 1

    return stats


def analyze_dealer_rotation(sessions: list[dict]) -> dict:
    """Q10: Analyze dealer rotation patterns."""
    stats = {
        "sessions_analyzed": 0,
        "consistent_rotation": 0,  # Sessions where dealer rotates +1 each round
        "rotation_deltas": Counter(),  # Delta between consecutive dealers
        "thany_player_is_dealer_count": 0,
        "first_bidder_is_dealer_plus_1": 0,
        "total_transitions": 0,
    }

    for session in sessions:
        rounds = session.get("rs", [])
        if len(rounds) < 2:
            continue
        stats["sessions_analyzed"] += 1

        dealers = []
        first_bidders = []

        for rnd in rounds:
            bids = extract_bid_events(rnd)
            if not bids:
                continue

            # First bidder
            first_bidders.append(bids[0].get("p"))

            # Dealer = thany player (if R2 reached)
            dealer = None
            for evt in bids:
                if evt.get("b") == "thany":
                    dealer = evt.get("p")
                    break
            dealers.append(dealer)

        # Analyze rotation
        consistent = True
        for i in range(1, len(dealers)):
            if dealers[i] is not None and dealers[i - 1] is not None:
                d1, d2 = dealers[i - 1], dealers[i]
                delta = ((d2 - d1) % 4)
                if delta == 0:
                    delta = 4
                stats["rotation_deltas"][delta] += 1
                stats["total_transitions"] += 1
                if delta != 1:
                    consistent = False

        # Check first bidder vs dealer
        for i in range(len(dealers)):
            if dealers[i] is not None and i < len(first_bidders):
                fb = first_bidders[i]
                d = dealers[i]
                expected_first = (d % 4) + 1
                if expected_first > 4:
                    expected_first = 1
                if fb == expected_first:
                    stats["first_bidder_is_dealer_plus_1"] += 1
                stats["thany_player_is_dealer_count"] += 1

        if consistent and len(dealers) > 2:
            stats["consistent_rotation"] += 1

    return stats


def analyze_bid_field_semantics(sessions: list[dict]) -> dict:
    """Analyze all field values across bid events for documentation."""
    stats = {
        "all_bid_types": Counter(),
        "gm_values": Counter(),
        "ts_values": Counter(),
        "rb_values": Counter(),
        "rd_values": Counter(),
        "unknown_fields": Counter(),
        "events_with_gm": 0,
        "events_without_gm": 0,
        "rb_minus1_count": 0,
        "rd_field_present": 0,
        "total_bid_events": 0,
    }
    known_fields = {"e", "p", "b", "gm", "ts", "rb", "rd"}

    for session in sessions:
        for rnd in session.get("rs", []):
            for evt in rnd.get("r", []):
                if evt.get("e") != 2:
                    continue
                stats["total_bid_events"] += 1
                stats["all_bid_types"][evt.get("b", "")] += 1

                if "gm" in evt:
                    stats["events_with_gm"] += 1
                    stats["gm_values"][evt.get("gm")] += 1
                else:
                    stats["events_without_gm"] += 1

                stats["ts_values"][evt.get("ts")] += 1
                rb = evt.get("rb")
                stats["rb_values"][rb] += 1
                if rb == -1:
                    stats["rb_minus1_count"] += 1

                if "rd" in evt and evt.get("rd"):
                    stats["rd_field_present"] += 1
                    stats["rd_values"][evt.get("rd")] += 1

                # Track unknown fields
                for k in evt:
                    if k not in known_fields:
                        stats["unknown_fields"][k] += 1

    return stats


def analyze_hokomclose_vs_opponent(sessions: list[dict]) -> dict:
    """Deep-dive: who can hokomclose/hokomopen — opponent only or also taker team?"""
    results = {
        "hokomclose_cases": [],
        "hokomopen_cases": [],
        "double_cases": [],
    }

    for session in sessions:
        name = session.get("n", "")
        for ri, rnd in enumerate(session.get("rs", [])):
            bids = extract_bid_events(rnd)
            result = get_result(rnd)
            if not result:
                continue

            bidder_rb = result.get("b", 0)  # 1 or 2 (team)
            for evt in bids:
                b = evt.get("b", "")
                if b in ("hokomclose", "hokomopen", "double"):
                    p = evt.get("p", 0)
                    # Teams: P1+P3 = team 1, P2+P4 = team 2
                    doubler_team = 1 if p in (1, 3) else 2
                    is_opponent = doubler_team != bidder_rb
                    results[f"{b}_cases"].append({
                        "session": name, "round": ri,
                        "doubler": p, "doubler_team": doubler_team,
                        "bidder_team": bidder_rb, "is_opponent": is_opponent,
                    })

    return results


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def main():
    archive_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_ARCHIVE)
    if not archive_dir.exists():
        print(f"ERROR: Archive directory not found: {archive_dir}")
        sys.exit(1)

    sessions = load_sessions(archive_dir)
    print(f"Loaded {len(sessions)} sessions from {archive_dir}")

    total_rounds = sum(len(s.get("rs", [])) for s in sessions)
    print(f"Total rounds: {total_rounds}")

    # ─── Field Semantics ──────────────────────────────────────────
    print_section("FIELD SEMANTICS (all bid events)")
    fields = analyze_bid_field_semantics(sessions)
    print(f"Total bid events: {fields['total_bid_events']}")
    print(f"\nBid types (b field):")
    for bt, count in fields["all_bid_types"].most_common():
        pct = 100 * count / fields["total_bid_events"]
        print(f"  {bt:15s} {count:5d} ({pct:5.1f}%)")
    print(f"\ngm field values:")
    for gm, count in fields["gm_values"].most_common():
        print(f"  gm={gm}: {count}")
    print(f"  (no gm): {fields['events_without_gm']}")
    print(f"\nts field values: {dict(fields['ts_values'].most_common())}")
    print(f"rb=-1 count: {fields['rb_minus1_count']} (= no bidder yet)")
    print(f"rd field present: {fields['rd_field_present']}")
    if fields["rd_values"]:
        print(f"rd values: {dict(fields['rd_values'].most_common())}")
    if fields["unknown_fields"]:
        print(f"Unknown fields: {dict(fields['unknown_fields'])}")

    # ─── Q1: Bidding Order ────────────────────────────────────────
    print_section("Q1: BIDDING ORDER & FIRST BIDDER")
    order = analyze_bidding_order(sessions)
    print(f"Total rounds analyzed: {order['total_rounds']}")
    print(f"\nFirst bidder position (P1-P4):")
    for p in sorted(order["r1_first_bidder_positions"]):
        count = order["r1_first_bidder_positions"][p]
        pct = 100 * count / order["total_rounds"]
        print(f"  P{p}: {count} ({pct:.1f}%)")

    # ─── Q2: Round Transitions ────────────────────────────────────
    print_section("Q2: ROUND 1 → ROUND 2 TRANSITIONS")
    trans = analyze_round_transitions(sessions)
    print(f"Total rounds: {trans['total_rounds']}")
    print(f"R1 only (contract won): {trans['r1_only']} ({100*trans['r1_only']/trans['total_rounds']:.1f}%)")
    print(f"Went to R2: {trans['r1_to_r2']} ({100*trans['r1_to_r2']/trans['total_rounds']:.1f}%)")
    print(f"Waraq (all-pass): {trans['waraq_rounds']} ({100*trans['waraq_rounds']/trans['total_rounds']:.1f}%)")
    print(f"\nR1 contract types: {dict(trans['r1_contract_types'].most_common())}")
    print(f"R2 outcomes: {dict(trans['r2_outcomes'].most_common())}")
    print(f"R2 contract types: {dict(trans['r2_contract_types'].most_common())}")

    # ─── Q3: Pass Mechanics ───────────────────────────────────────
    print_section("Q3: PASS MECHANICS (thany/wala/waraq)")
    pm = analyze_pass_mechanics(sessions)
    print(f"thany (R2 trigger) count: {pm['thany_count']}")
    print(f"thany by player: {dict(pm['thany_by_player'].most_common())}")
    print(f"wala (R2 pass) count: {pm['wala_count']}")
    print(f"wala count patterns: {dict(pm['wala_patterns'].most_common())}")
    print(f"waraq (all-pass redeal) count: {pm['waraq_count']}")
    if pm["waraq_wala_counts"]:
        print(f"walas before waraq: {Counter(pm['waraq_wala_counts']).most_common()}")
    print(f"R1 all-pass (went to R2): {pm['r1_all_pass_count']}")

    # ─── Q4: Hokum vs Sun ────────────────────────────────────────
    print_section("Q4: HOKUM vs SUN FLOW")
    flow = analyze_hokum_sun_flow(sessions)
    print(f"Total contracted rounds: {flow['total_contracted']}")
    print(f"\n  Hokum R1:    {flow['hokum_r1']:4d}")
    print(f"  Sun R1:      {flow['sun_r1']:4d}")
    print(f"  Ashkal:      {flow['ashkal_r1']:4d}")
    print(f"  Hokum R2:    {flow['hokum_r2']:4d}")
    print(f"  Sun R2:      {flow['sun_r2']:4d}")
    print(f"  TurnToSun:   {flow['turntosun']:4d}")
    print(f"\n  Sun hijacks: {flow['sun_hijack']}")
    print(f"  Mode dist:   {dict(flow['mode_distribution'].most_common())}")
    print(f"  Bidder positions: {dict(flow['bidder_positions'].most_common())}")

    # ─── Q5: Ashkal ───────────────────────────────────────────────
    print_section("Q5: ASHKAL RULES")
    ash = analyze_ashkal(sessions)
    print(f"Total ashkal bids: {ash['total_ashkal']}")
    print(f"Ashkal by player: {dict(ash['ashkal_by_player'].most_common())}")
    print(f"Ashkal rb (bidder): {dict(ash['ashkal_rb_values'].most_common())}")
    print(f"After hokum: {ash['ashkal_after_hokum']}, after pass only: {ash['ashkal_after_pass']}")
    if ash["ashkal_original_hokum_player"]:
        print(f"Original hokom players before ashkal: {Counter(ash['ashkal_original_hokum_player']).most_common()}")

    # ─── Q6: Doubling ────────────────────────────────────────────
    print_section("Q6: DOUBLING CHAIN")
    dbl = analyze_doubling(sessions)
    print(f"Total doubled rounds: {dbl['total_doubled_rounds']}")
    print(f"Doubling types: {dict(dbl['doubling_types'].most_common())}")
    print(f"\nDoubling chains (sequences):")
    for chain, count in dbl["doubling_chains"].most_common(15):
        print(f"  {' → '.join(chain)}: {count}")
    print(f"\nMax chain length: {dbl['max_chain_length']}")
    print(f"\nhokomclose team relation: {dict(dbl['hokomclose_team_relation'])}")
    print(f"hokomopen team relation: {dict(dbl['hokomopen_team_relation'])}")
    print(f"double context: {dict(dbl['double_context'])}")
    print(f"beforeyou after: {dict(dbl['beforeyou_after'])}")

    # ─── Q7-8: Waraq & Face-up Card ──────────────────────────────
    print_section("Q7-8: WARAQ & FACE-UP CARD")
    wf = analyze_waraq_faceup(sessions)
    print(f"Total waraq: {wf['total_waraq']}")
    print(f"ts=4 (hearts) in R1: {wf['ts_always_4']} / {wf['total_rounds']}")
    print(f"ts values in R1: {dict(wf['ts_values_in_r1'].most_common())}")
    print(f"ts values after suit bid: {dict(wf['ts_values_after_suit'].most_common())}")
    print(f"ts changes after suit bid: {wf['ts_changes_after_suit_bid']}")
    print(f"Rounds with fc field: {wf['fc_field_rounds']}")

    # ─── Q9: Trump Selection ─────────────────────────────────────
    print_section("Q9: TRUMP SUIT SELECTION (R2)")
    ts = analyze_trump_selection(sessions)
    print(f"R2 suit bids: {dict(ts['r2_suit_bids'].most_common())}")
    print(f"TurnToSun in R2: {ts['turntosun_count']}")
    print(f"hokom2 bidder = suit bidder: {ts['hokom2_bidder_same_as_suit']}")
    print(f"hokom2 bidder ≠ suit bidder: {ts['hokom2_bidder_diff_from_suit']}")
    print(f"hokom2 without follow-up: {ts['hokom2_without_suit']}")

    # ─── Q10: Dealer Rotation ────────────────────────────────────
    print_section("Q10: DEALER ROTATION")
    dr = analyze_dealer_rotation(sessions)
    print(f"Sessions analyzed: {dr['sessions_analyzed']}")
    print(f"Consistently rotating +1: {dr['consistent_rotation']}")
    print(f"Rotation deltas: {dict(dr['rotation_deltas'].most_common())}")
    print(f"Total transitions: {dr['total_transitions']}")
    print(f"First bidder = dealer+1: {dr['first_bidder_is_dealer_plus_1']} / {dr['thany_player_is_dealer_count']}")

    # ─── Deep-dive: Doubler team analysis ─────────────────────────
    print_section("DEEP-DIVE: DOUBLER TEAM ANALYSIS")
    dt = analyze_hokomclose_vs_opponent(sessions)
    for bid_type in ("hokomclose", "hokomopen", "double"):
        cases = dt[f"{bid_type}_cases"]
        if not cases:
            continue
        opp = sum(1 for c in cases if c["is_opponent"])
        same = sum(1 for c in cases if not c["is_opponent"])
        print(f"\n{bid_type}: {len(cases)} total")
        print(f"  By opponent: {opp}")
        print(f"  By same team: {same}")

    print(f"\n{'=' * 70}")
    print(f"  ANALYSIS COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
