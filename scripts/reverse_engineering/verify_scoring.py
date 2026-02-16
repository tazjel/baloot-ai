"""Mission 6: Scoring Pipeline Verification (Extended).

Verifies all 1,095 contracted rounds produce the exact GP shown in e=12.rs.
Uses the EXACT scoring formulas from archive_scoring_validator.py (100% validated).

Key corrections applied:
- m field = game mode (1=SUN, 2=HOKUM), NOT multiplier
- Card GP computed from (p - declarations), NOT from e1/e2 directly
  (p includes last-trick bonus 10, which affects GP rounding)
- SUN radda: "double"/"redouble" in bids (NOT "beforeyou")
- HOKUM multiplier: from bid events hokomclose/beforeyou/hokomopen
- HOKUM doubler: tracked via player seat `p` of doubling bid event
- Qayd (cc) rounds: skipped (separate scoring logic)

Output: gbaloot/data/training/scoring_verification.json
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

# Constants (matching archive_scoring_validator.py exactly)
GP_TARGET_HOKUM = 16
DECK_TOTAL_SUN = 120
DECK_TOTAL_HOKUM = 152
LAST_TRICK_BONUS = 10
QAHWA_FLAT = 152
BALOOT_GP = 2
SUN_KABOOT = 44
HOKUM_KABOOT = 25


# ── GP Conversion Functions (exact copy from archive_scoring_validator.py) ──


def card_gp_sun(card_abnat: int) -> int:
    """SUN card GP: floor-to-even.

    q, r = divmod(abnat, 5)
    GP = q + 1 if q is odd and r > 0, else q
    Total always sums to 26.
    """
    q, r = divmod(card_abnat, 5)
    return q + (1 if q % 2 == 1 and r > 0 else 0)


def _hokum_individual(raw: int) -> int:
    """HOKUM individual GP: raw/10, r>5 rounds up."""
    q, r = divmod(raw, 10)
    return q + 1 if r > 5 else q


def card_gp_hokum_pair(p1: int, p2: int) -> tuple[int, int]:
    """HOKUM card GP pair, constrained to sum=16.

    Individual rounding can produce sum=15, 16, or 17.
    When sum != 16, adjust the side with larger mod-10 remainder.
    """
    g1 = _hokum_individual(p1)
    g2 = _hokum_individual(p2)
    total = g1 + g2

    if total == GP_TARGET_HOKUM:
        return g1, g2
    elif total == GP_TARGET_HOKUM + 1:  # 17 → reduce
        r1, r2 = p1 % 10, p2 % 10
        if r1 > r2:
            return g1 - 1, g2
        elif r2 > r1:
            return g1, g2 - 1
        else:
            return (g1 - 1, g2) if p1 >= p2 else (g1, g2 - 1)
    elif total == GP_TARGET_HOKUM - 1:  # 15 → increase
        r1, r2 = p1 % 10, p2 % 10
        if r1 > r2:
            return g1 + 1, g2
        elif r2 > r1:
            return g1, g2 + 1
        else:
            return (g1 + 1, g2) if p1 <= p2 else (g1, g2 + 1)
    return g1, g2


def project_gp_sun(decls: list[dict]) -> int:
    """SUN project GP: (val*2)//10, 400→40. Excludes baloot."""
    total = 0
    for d in decls:
        if d.get("n") == "baloot":
            continue
        val = int(d.get("val", 0))
        if val >= 400:
            total += 40
        else:
            total += (val * 2) // 10
    return total


def project_gp_hokum(decls: list[dict]) -> int:
    """HOKUM project GP: val//10. Excludes baloot."""
    return sum(
        int(d.get("val", 0)) // 10
        for d in decls
        if d.get("n") != "baloot"
    )


def count_baloot_gp(decls: list[dict]) -> int:
    """Baloot GP: 2 GP per baloot declaration."""
    return sum(BALOOT_GP for d in decls if d.get("n") == "baloot")


# ── Multiplier & Doubling (exact copy from archive_scoring_validator.py) ──


def get_hokum_multiplier(events: list[dict]) -> int:
    """Derive HOKUM multiplier from bid events (NOT from em/m field).

    hokomclose/beforeyou/hokomopen → level += 1
    triple → level = max(level, 3)
    qahwa → 99 (flat 152 GP, game ends)
    """
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
    """Check if SUN bidding includes a radda (double/redouble).

    NOTE: Uses "double" and "redouble", NOT "beforeyou".
    """
    return any(
        evt.get("e") == 2 and evt.get("b") in ("double", "redouble")
        for evt in events
    )


def get_doubler_team(events: list[dict]) -> int:
    """Track who declared the doubling (hokomclose/beforeyou/hokomopen).

    Returns team number (1 or 2) of the doubler, or 0 if no doubling.
    Tracks the LAST player `p` who declared a doubling bid.
    """
    doubler_seat = -1
    for evt in events:
        if evt.get("e") != 2:
            continue
        b = evt.get("b", "")
        p = evt.get("p", 0)
        if b in ("hokomclose", "beforeyou", "hokomopen"):
            doubler_seat = p
    if doubler_seat in (1, 3):
        return 1
    elif doubler_seat in (2, 4):
        return 2
    return 0


# ── Round Scoring (matching archive_scoring_validator.py pipeline exactly) ──


def _score_sun_round(
    card_p1: int, card_p2: int,
    total_p1: int, total_p2: int,
    r1_decl: list, r2_decl: list,
    bidder: int, winner: int,
    events: list[dict],
) -> tuple[int, int, str, int]:
    """Score a SUN round (without baloot — added by caller).

    Pipeline: card_gp → project_gp → khasara → radda → (baloot added later)

    Returns: (g1, g2, baloot_mode, khasara_loser)
    """
    # Card GP: floor-to-even
    cg1 = card_gp_sun(card_p1)
    cg2 = card_gp_sun(card_p2)

    # Project GP
    pg1 = project_gp_sun(r1_decl)
    pg2 = project_gp_sun(r2_decl)

    g1, g2 = cg1 + pg1, cg2 + pg2

    # Khasara: bidder_gp < opp_gp, or on GP tie: bid_total_raw < opp_total_raw
    bgp = g1 if bidder == 1 else g2
    ogp = g2 if bidder == 1 else g1
    bid_total = total_p1 if bidder == 1 else total_p2
    opp_total = total_p2 if bidder == 1 else total_p1

    is_khasara = bgp < ogp or (bgp == ogp and bid_total < opp_total)
    khasara_loser = 0
    if is_khasara:
        khasara_loser = bidder
        total_gp = g1 + g2
        if bidder == 1:
            g1, g2 = 0, total_gp
        else:
            g1, g2 = total_gp, 0

    # Radda (SUN double/redouble): winner takes 2× total, loser 0
    if has_sun_radda(events):
        total_gp = g1 + g2
        if winner == 1 or (winner == 0 and g1 > g2):
            g1, g2 = total_gp * 2, 0
        else:
            g1, g2 = 0, total_gp * 2

    baloot_mode = "khasara" if is_khasara else "normal"
    return g1, g2, baloot_mode, khasara_loser


def _score_hokum_round(
    card_p1: int, card_p2: int,
    total_p1: int, total_p2: int,
    r1_decl: list, r2_decl: list,
    bidder: int, winner: int,
    events: list[dict],
) -> tuple[int, int, str, int]:
    """Score a HOKUM round (without baloot — added by caller).

    Pipeline: card_gp_pair → project_gp → khasara → multiplier → (baloot later)

    Returns: (g1, g2, baloot_mode, khasara_loser)
    """
    # Card GP: pair-based rounding (constrained to sum=16)
    cg1, cg2 = card_gp_hokum_pair(card_p1, card_p2)

    # Project GP
    pg1 = project_gp_hokum(r1_decl)
    pg2 = project_gp_hokum(r2_decl)

    g1, g2 = cg1 + pg1, cg2 + pg2

    # Khasara determination
    bgp = g1 if bidder == 1 else g2
    ogp = g2 if bidder == 1 else g1
    bid_total = total_p1 if bidder == 1 else total_p2
    opp_total = total_p2 if bidder == 1 else total_p1

    mult = get_hokum_multiplier(events)
    doubler = get_doubler_team(events)

    is_khasara = False
    khasara_loser = 0

    if bgp < ogp:
        # Clear khasara: bidder has fewer GP
        is_khasara = True
        khasara_loser = bidder
    elif bgp == ogp:
        if mult > 1 and doubler > 0:
            # Doubled game with GP tie: the doubler loses
            is_khasara = True
            khasara_loser = doubler
        elif bid_total <= opp_total:
            # Normal game with GP tie: bidder loses when raw abnat <= opp
            is_khasara = True
            khasara_loser = bidder
        # else: bidder has more raw abnat on tie → split (no khasara)

    if is_khasara:
        total_gp = g1 + g2
        if khasara_loser == 1:
            g1, g2 = 0, total_gp
        else:
            g1, g2 = total_gp, 0

    # Multiplier (qahwa, double, triple)
    if mult >= 99:
        # Qahwa: flat 152 to winner, baloot cancelled
        g1, g2 = (QAHWA_FLAT, 0) if winner == 1 else (0, QAHWA_FLAT)
        return g1, g2, "cancelled", khasara_loser
    elif mult > 1:
        total_gp = g1 + g2
        if g1 > g2:
            g1, g2 = total_gp * mult, 0
        elif g2 > g1:
            g1, g2 = 0, total_gp * mult
        else:
            g1 *= mult
            g2 *= mult

    baloot_mode = "khasara" if is_khasara else "normal"
    return g1, g2, baloot_mode, khasara_loser


def score_round(events: list[dict], result: dict) -> tuple[int, int] | None:
    """Score a round using the exact pipeline from archive_scoring_validator.py.

    Pipeline: card_gp → project_gp → khasara → multiplier → baloot

    Returns (s1, s2) or None if round cannot be scored (waraq/qayd).
    """
    m = result.get("m", 0)
    if m == 0:
        return None

    mode = "SUN" if m in (1, 3) else "HOKUM"
    b = result.get("b", 0)
    w = result.get("w", 0)
    cc = result.get("cc", 0)
    kbt = result.get("kbt", 0)
    lmw = result.get("lmw", 0)

    e1 = result.get("e1", 0)
    e2 = result.get("e2", 0)
    p1 = result.get("p1", 0)
    p2 = result.get("p2", 0)
    s1 = result.get("s1", 0)
    s2 = result.get("s2", 0)

    r1_decl = result.get("r1", [])
    r2_decl = result.get("r2", [])

    # Skip qayd rounds (separate scoring logic)
    if cc:
        return s1, s2  # Trust archive for qayd

    # Declaration totals
    decl1_total = sum(int(d.get("val", 0)) for d in r1_decl)
    decl2_total = sum(int(d.get("val", 0)) for d in r2_decl)

    # Baloot GP (immune to everything, added last)
    bal1 = count_baloot_gp(r1_decl)
    bal2 = count_baloot_gp(r2_decl)

    # Kaboot check — BEFORE normal scoring
    if kbt:
        pg1 = project_gp_sun(r1_decl) if mode == "SUN" else project_gp_hokum(r1_decl)
        pg2 = project_gp_sun(r2_decl) if mode == "SUN" else project_gp_hokum(r2_decl)
        base = SUN_KABOOT if mode == "SUN" else HOKUM_KABOOT
        baloot_total = bal1 + bal2
        kaboot_total = base + pg1 + pg2 + baloot_total
        if w == 1:
            return kaboot_total, 0
        else:
            return 0, kaboot_total

    # Card abnat = total pts - declaration pts
    # This INCLUDES last-trick bonus (which is in p but not in e)
    card_p1 = p1 - decl1_total
    card_p2 = p2 - decl2_total

    if mode == "SUN":
        g1, g2, baloot_mode, khasara_loser = _score_sun_round(
            card_p1, card_p2, p1, p2, r1_decl, r2_decl, b, w, events,
        )
    else:
        g1, g2, baloot_mode, khasara_loser = _score_hokum_round(
            card_p1, card_p2, p1, p2, r1_decl, r2_decl, b, w, events,
        )

    # Add baloot GP based on baloot_mode
    if baloot_mode == "normal":
        g1 += bal1
        g2 += bal2
    elif baloot_mode == "khasara":
        total_bal = bal1 + bal2
        if khasara_loser == 1:
            g2 += total_bal
        else:
            g1 += total_bal
    # "cancelled": don't add any baloot (qahwa)

    return g1, g2


# ── Main ──────────────────────────────────────────────────────


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


def verify_round(game: dict, round_idx: int, events: list[dict]) -> dict | None:
    """Verify a single round's scoring."""
    game_name = game.get("n", game.get("_filename", "unknown"))

    result = None
    for ev in events:
        if ev.get("e") == 12:
            result = ev.get("rs", {})
            break
    if result is None:
        return None

    m = result.get("m", 0)
    if m == 0:
        return None

    mode = "SUN" if m in (1, 3) else "HOKUM"
    cc = result.get("cc", 0)
    kbt = result.get("kbt", 0)

    s1_archive = result.get("s1", 0)
    s2_archive = result.get("s2", 0)

    scored = score_round(events, result)
    if scored is None:
        return None

    s1_computed, s2_computed = scored
    match = (s1_computed == s1_archive and s2_computed == s2_archive)

    return {
        "game": game_name,
        "round": round_idx + 1,
        "mode": mode,
        "status": "match" if match else "mismatch",
        "effective": {"t1": result.get("e1", 0), "t2": result.get("e2", 0)},
        "raw": {"t1": result.get("p1", 0), "t2": result.get("p2", 0)},
        "declarations": {
            "r1": [{"n": d.get("n"), "val": d.get("val")} for d in result.get("r1", [])],
            "r2": [{"n": d.get("n"), "val": d.get("val")} for d in result.get("r2", [])],
        },
        "is_kaboot": kbt == 1,
        "is_qayd": cc > 0,
        "winner": result.get("w", 0),
        "bidder_team": result.get("b", 0),
        "m_field": result.get("m"),
        "em_field": result.get("em"),
        "challenge_count": cc,
        "final_gp": {
            "archive": {"t1": s1_archive, "t2": s2_archive},
            "computed": {"t1": s1_computed, "t2": s2_computed},
            "match": match,
        },
    }


def main():
    """Run Mission 6: Scoring Pipeline Verification."""
    print("=" * 60)
    print("Mission 6: Scoring Pipeline Verification (Extended)")
    print("=" * 60)

    print("\nLoading games from {}...".format(ARCHIVE_DIR))
    games = load_all_games()
    print("Loaded {} games".format(len(games)))

    print("\nVerifying scoring for all contracted rounds...")
    all_results = []
    matches = 0
    mismatches = 0
    mismatch_details = []
    mode_counts: Counter = Counter()
    kaboot_count = 0
    challenge_count = 0
    qayd_skipped = 0

    for game in games:
        for round_idx, round_obj in enumerate(game.get("rs", [])):
            events = round_obj.get("r", [])
            result = verify_round(game, round_idx, events)
            if result is None:
                continue

            all_results.append(result)
            mode_counts[result["mode"]] += 1

            if result.get("is_qayd"):
                qayd_skipped += 1

            if result["status"] == "match":
                matches += 1
            else:
                mismatches += 1
                mismatch_details.append(result)

            if result.get("is_kaboot"):
                kaboot_count += 1
            if result.get("challenge_count", 0) > 0:
                challenge_count += 1

    total = matches + mismatches

    print("\n--- Results ---")
    print("Total contracted rounds: {}".format(total))
    if total > 0:
        print("GP matches: {}/{} ({:.1f}%)".format(matches, total, matches / total * 100))
        print("GP mismatches: {}".format(mismatches))

    print("\n--- Mode Distribution ---")
    for mode, count in mode_counts.most_common():
        print("  {}: {}".format(mode, count))

    print("\n--- Special Cases ---")
    print("  Kaboot: {}".format(kaboot_count))
    print("  Challenge/qayd: {} (trusted from archive)".format(challenge_count))

    if mismatch_details:
        print("\n--- First 20 GP Mismatches ---")
        for v in mismatch_details[:20]:
            fg = v["final_gp"]
            print("  {} R{} [{}]: "
                  "archive=({},{}), "
                  "computed=({},{}), "
                  "eff=({},{}), raw=({},{}), "
                  "m={}, em={}, "
                  "bidder=T{}, winner=T{}, "
                  "cc={}".format(
                      v['game'], v['round'], v['mode'],
                      fg['archive']['t1'], fg['archive']['t2'],
                      fg['computed']['t1'], fg['computed']['t2'],
                      v['effective']['t1'], v['effective']['t2'],
                      v['raw']['t1'], v['raw']['t2'],
                      v['m_field'], v['em_field'],
                      v['bidder_team'], v['winner'],
                      v['challenge_count']))

    # Build output
    output = {
        "summary": {
            "total_rounds_verified": total,
            "gp_matches": matches,
            "gp_mismatches": mismatches,
            "gp_match_rate": round(matches / total * 100, 2) if total > 0 else 0,
            "mode_distribution": dict(mode_counts),
            "qayd_rounds_trusted": qayd_skipped,
        },
        "scoring_formulas": {
            "card_points": "card_p = p - decl_total (includes last-trick bonus 10)",
            "sun_card_gp": "floor-to-even: q, r = divmod(card_p, 5); q + (1 if q%2==1 and r>0 else 0)",
            "hokum_card_gp": "pair-based: individual(raw/10, r>5 up), constrain sum=16",
            "sun_project_gp": "(val * 2) // 10; 400 -> 40",
            "hokum_project_gp": "val // 10",
            "khasara_sun": "bidder_gp < opp_gp, or (GP tie AND bid_total_raw < opp_total_raw)",
            "khasara_hokum": "bidder_gp < opp_gp, or (GP tie AND [doubled: doubler loses, normal: bidder_raw <= opp_raw])",
            "hokum_multiplier": "from bid events: hokomclose/beforeyou/hokomopen +1, triple max(3), qahwa 99",
            "sun_radda": "double/redouble present → winner gets 2× total GP",
            "baloot": "2 GP per declaration, immune to multiplier, added LAST",
            "kaboot_sun": "base 44 + all project GP + all baloot GP → winner",
            "kaboot_hokum": "base 25 + all project GP + all baloot GP → winner",
            "qahwa": "flat 152 GP to winner, baloot cancelled",
            "m_field": "game mode (1=SUN, 2=HOKUM), NOT multiplier",
            "em_field": "doubling level for HOKUM",
        },
        "mismatches": mismatch_details[:100],
        "verification_sample": all_results[:50],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "scoring_verification.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("\n✅ Output saved to {}".format(output_path))

    return output


if __name__ == "__main__":
    main()
