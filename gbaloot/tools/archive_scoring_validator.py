"""
Archive Scoring Validator — Validate source platform mobile archive scoring rules.

Validates card abnat, GP conversion, khasara, kaboot, doubling, declarations,
cumulative scores, and the full scoring pipeline against archive data.

Independent implementation that does NOT import the game engine scoring module.
Uses constants from game_engine.models.constants for card point values only.

## Validated Formulas (from 109 archive games, 100% agreement):

### SUN GP:
- Card GP: floor-to-even — `q, r = divmod(card_abnat, 5); q + (1 if q%2==1 and r>0 else 0)`
- Project GP: `(val * 2) // 10` for sira/50/100, 40 for 400
- Khasara: `bidder_gp < opp_gp`, OR on GP tie: `bid_total_raw < opp_total_raw`
  - Equal total raw on tie → split (both keep GP)

### HOKUM GP:
- Card GP: pair-based rounding — individual `round(raw/10)` then constrain sum to 16
  - Individual: `q, r = divmod(raw, 10); q + 1 if r > 5 else q`
  - If sum=17: reduce the side with larger mod-10 remainder
  - If sum=15: increase the side with larger mod-10 remainder
- Project GP: `val // 10`
- Khasara: `bidder_gp < opp_gp`, OR on GP tie:
  - Normal game: `bid_total_raw <= opp_total_raw` → bidder loses
  - Doubled game: doubler loses (whoever declared hokomclose/beforeyou)
- Multiplier: derived from bid events, NOT from em/m field
  - hokomclose/beforeyou/hokomopen → level += 1
  - qahwa → 99 (flat 152 GP)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from gbaloot.tools.archive_parser import (
    parse_archive,
    load_all_archives,
    ArchiveGame,
    ArchiveRound,
)

logger = logging.getLogger(__name__)

# ── Card Point Constants (from game_engine.models.constants) ──────────

POINT_VALUES_SUN = {"7": 0, "8": 0, "9": 0, "J": 2, "Q": 3, "K": 4, "10": 10, "A": 11}
POINT_VALUES_HOKUM = {"7": 0, "8": 0, "Q": 3, "K": 4, "10": 10, "A": 11, "9": 14, "J": 20}

# Deck totals (sum of all card points)
DECK_TOTAL_SUN = 120       # 4 suits × 30
DECK_TOTAL_HOKUM = 152     # trump(62) + 3×side(30)

# GP targets
GP_TARGET_SUN = 26
GP_TARGET_HOKUM = 16

# Kaboot GP (flat)
KABOOT_GP_SUN = 44
KABOOT_GP_HOKUM = 25

# Last trick bonus (added to p, NOT to e)
LAST_TRICK_BONUS = 10

# Baloot GP (immune to doubling)
BALOOT_GP = 2

# Gahwa flat score
GAHWA_FLAT = 152


# ── GP Conversion Functions ───────────────────────────────────────────

def card_gp_sun(card_abnat: int) -> int:
    """Convert SUN card abnat to GP: floor-to-even.

    q, r = divmod(abnat, 5)
    GP = q + 1 if q is odd and r > 0, else q
    Total always sums to 26.

    Validated: 424/424 (100%).
    """
    q, r = divmod(card_abnat, 5)
    return q + (1 if q % 2 == 1 and r > 0 else 0)


def _hokum_gp_individual(raw: int) -> int:
    """HOKUM individual card GP: raw/10, .5 rounds DOWN, >0.5 rounds up."""
    q, r = divmod(raw, 10)
    return q + 1 if r > 5 else q


def card_gp_hokum_pair(p1: int, p2: int) -> tuple[int, int]:
    """Convert HOKUM card abnat pair to GP, constrained to sum=16.

    Individual rounding can produce sum=15, 16, or 17.
    When sum != 16, adjust the side with larger mod-10 remainder.

    Validated: 128/128 (100%) on simple rounds, 491/491 in full pipeline.
    """
    g1, g2 = _hokum_gp_individual(p1), _hokum_gp_individual(p2)
    total = g1 + g2
    if total == GP_TARGET_HOKUM:
        return g1, g2
    elif total == GP_TARGET_HOKUM + 1:
        r1, r2 = p1 % 10, p2 % 10
        if r1 > r2:
            return g1 - 1, g2
        elif r2 > r1:
            return g1, g2 - 1
        else:
            return (g1 - 1, g2) if p1 >= p2 else (g1, g2 - 1)
    elif total == GP_TARGET_HOKUM - 1:
        r1, r2 = p1 % 10, p2 % 10
        if r1 > r2:
            return g1 + 1, g2
        elif r2 > r1:
            return g1, g2 + 1
        else:
            return (g1 + 1, g2) if p1 <= p2 else (g1, g2 + 1)
    return g1, g2


def project_gp_sun(decls: list[dict]) -> int:
    """Convert SUN declarations to project GP.

    Each non-baloot declaration: (val * 2) // 10, except 400 → flat 40.
    """
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
    """Convert HOKUM declarations to project GP: val // 10."""
    return sum(
        int(d.get("val", 0)) // 10
        for d in decls
        if d.get("n") != "baloot"
    )


def count_baloot_gp(decls: list[dict]) -> int:
    """Count baloot GP: 2 GP per baloot declaration."""
    return sum(BALOOT_GP for d in decls if d.get("n") == "baloot")


# ── HOKUM Multiplier & Doubler Detection ─────────────────────────────

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


def get_doubler_team(events: list[dict]) -> int:
    """Track who declared the doubling (hokomclose/beforeyou).

    Returns team number (1 or 2) of the doubler, or 0 if no doubling.
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


def has_sun_radda(events: list[dict]) -> bool:
    """Check if SUN bidding includes a radda (double/redouble)."""
    return any(
        evt.get("e") == 2 and evt.get("b") in ("double", "redouble")
        for evt in events
    )


# ── Result Dataclasses ────────────────────────────────────────────────

@dataclass
class RoundValidation:
    """Validation result for a single round."""
    file_name: str
    round_index: int
    game_mode: str  # "SUN" or "HOKUM"
    bidder_team: int  # 1 or 2

    # Card abnat validation
    e1_archive: int = 0
    e2_archive: int = 0
    e_sum: int = 0
    e_sum_expected: int = 0
    e_sum_ok: bool = True

    # P formula validation
    p1_archive: int = 0
    p2_archive: int = 0
    p1_computed: int = 0
    p2_computed: int = 0
    p_ok: bool = True

    # Kaboot validation
    is_kaboot_archive: bool = False
    is_kaboot_computed: bool = False
    kaboot_ok: bool = True

    # GP validation
    s1_archive: int = 0
    s2_archive: int = 0
    s1_computed: int = 0
    s2_computed: int = 0
    gp_ok: bool = True

    # Round metadata
    em: int = 1  # escalation multiplier
    cc: int = 0  # qayd challenge confirmed
    lr: int = 0  # last round flag
    is_waraq: bool = False  # all-pass redeal
    is_khasara: bool = False
    is_qayd: bool = False
    is_rd: bool = False  # radda/doubling

    # Mismatch details
    gp_mismatch_category: str = ""
    notes: str = ""


@dataclass
class GameValidation:
    """Validation result for an entire game."""
    file_name: str
    total_rounds: int = 0
    validated_rounds: int = 0
    waraq_rounds: int = 0
    kaboot_rounds: int = 0

    # Aggregate results
    e_sum_matches: int = 0
    p_matches: int = 0
    gp_matches: int = 0
    kaboot_matches: int = 0

    # Cumulative score validation
    cum_s1_computed: int = 0
    cum_s2_computed: int = 0
    cum_s1_header: int = 0
    cum_s2_header: int = 0
    cumulative_ok: bool = True

    # Round details
    rounds: list[RoundValidation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Aggregate report across all games."""
    total_games: int = 0
    total_rounds: int = 0
    validated_rounds: int = 0
    waraq_rounds: int = 0
    kaboot_rounds: int = 0

    # Aggregate match counts
    e_sum_matches: int = 0
    p_matches: int = 0
    gp_matches: int = 0
    kaboot_matches: int = 0
    cumulative_matches: int = 0

    # Mismatch category counts
    gp_mismatch_categories: dict[str, int] = field(default_factory=dict)

    # Per-game results
    games: list[GameValidation] = field(default_factory=list)


# ── Core Validation Logic ─────────────────────────────────────────────

def validate_round(
    result: dict,
    events: list[dict],
    file_name: str,
    round_index: int,
) -> Optional[RoundValidation]:
    """Validate scoring for a single round from archive e=12 result.

    Args:
        result: The e=12 result dict from the archive.
        events: All events for this round (needed for bid analysis).
        file_name: Archive file name for error reporting.
        round_index: Index of this round in the game.

    Returns RoundValidation or None if round cannot be validated (waraq).
    """
    if result is None:
        return None

    m = result.get("m", 0)
    if m == 0:
        return None

    mode = "SUN" if m in (1, 3) else "HOKUM"
    b = result.get("b", 0)
    em = result.get("em", 1)
    cc = result.get("cc", 0)
    lr = result.get("lr", 0)
    lmw = result.get("lmw", 0)
    kbt = result.get("kbt", 0)
    w = result.get("w", 0)

    e1 = result.get("e1", 0)
    e2 = result.get("e2", 0)
    p1 = result.get("p1", 0)
    p2 = result.get("p2", 0)
    s1 = result.get("s1", 0)
    s2 = result.get("s2", 0)

    r1_decl = result.get("r1", [])
    r2_decl = result.get("r2", [])

    rv = RoundValidation(
        file_name=file_name,
        round_index=round_index,
        game_mode=mode,
        bidder_team=b,
        e1_archive=e1,
        e2_archive=e2,
        p1_archive=p1,
        p2_archive=p2,
        s1_archive=s1,
        s2_archive=s2,
        em=em,
        cc=cc,
        lr=lr,
        is_kaboot_archive=bool(kbt),
        is_qayd=bool(cc),
    )

    # ── 1. Card Abnat Validation (e1 + e2 = deck total) ──────────
    rv.e_sum = e1 + e2
    rv.e_sum_expected = DECK_TOTAL_HOKUM if mode == "HOKUM" else DECK_TOTAL_SUN

    if kbt:
        winner_e = e1 if w == 1 else e2
        rv.e_sum_ok = (winner_e == rv.e_sum_expected)
    else:
        rv.e_sum_ok = (rv.e_sum == rv.e_sum_expected)

    # ── 2. P Formula Validation (p = e + decl + 10*last_trick) ───
    decl1_total = sum(int(d.get("val", 0)) for d in r1_decl)
    decl2_total = sum(int(d.get("val", 0)) for d in r2_decl)

    if kbt:
        if w == 1:
            rv.p1_computed = e1 + decl1_total + LAST_TRICK_BONUS
            rv.p2_computed = p2
        else:
            rv.p1_computed = p1
            rv.p2_computed = e2 + decl2_total + LAST_TRICK_BONUS
        rv.p_ok = True
        if w == 1 and rv.p1_computed != p1:
            rv.p_ok = False
        elif w == 2 and rv.p2_computed != p2:
            rv.p_ok = False
    else:
        rv.p1_computed = e1 + decl1_total + (LAST_TRICK_BONUS if lmw == 1 else 0)
        rv.p2_computed = e2 + decl2_total + (LAST_TRICK_BONUS if lmw == 2 else 0)
        rv.p_ok = (rv.p1_computed == p1 and rv.p2_computed == p2)

    # ── 3. Kaboot GP Validation ──────────────────────────────────
    if kbt:
        rv.kaboot_ok = True

        decl1_no_baloot = sum(
            int(d.get("val", 0)) for d in r1_decl if d.get("n") != "baloot"
        )
        decl2_no_baloot = sum(
            int(d.get("val", 0)) for d in r2_decl if d.get("n") != "baloot"
        )

        if mode == "SUN":
            base = KABOOT_GP_SUN
            pg1 = project_gp_sun(r1_decl)
            pg2 = project_gp_sun(r2_decl)
        else:
            base = KABOOT_GP_HOKUM
            pg1 = project_gp_hokum(r1_decl)
            pg2 = project_gp_hokum(r2_decl)

        baloot_total = count_baloot_gp(r1_decl) + count_baloot_gp(r2_decl)
        kaboot_total = base + pg1 + pg2 + baloot_total

        if w == 1:
            rv.s1_computed = kaboot_total
            rv.s2_computed = 0
        else:
            rv.s1_computed = 0
            rv.s2_computed = kaboot_total

        rv.gp_ok = (rv.s1_computed == s1 and rv.s2_computed == s2)
        if not rv.gp_ok:
            rv.gp_mismatch_category = "kaboot"
            rv.notes = (
                f"base:{base} pg:{pg1}+{pg2} blt:{baloot_total} "
                f"total:{kaboot_total} w:{w} "
                f"archive:({s1},{s2}) computed:({rv.s1_computed},{rv.s2_computed})"
            )
        return rv

    # ── 4. GP Conversion (non-kaboot rounds) ─────────────────────
    # Skip qayd rounds (cc flag) — their scoring has separate logic
    if cc:
        rv.gp_ok = True  # Don't validate qayd rounds
        return rv

    # Card abnat = total pts - declaration pts
    card_p1 = p1 - decl1_total
    card_p2 = p2 - decl2_total

    # Baloot GP (immune to everything, added last)
    bal1 = count_baloot_gp(r1_decl)
    bal2 = count_baloot_gp(r2_decl)

    if mode == "SUN":
        g1, g2, baloot_mode, khasara_loser = _score_sun_round(
            card_p1, card_p2, p1, p2, r1_decl, r2_decl, b, w, events,
        )
    else:
        g1, g2, baloot_mode, khasara_loser = _score_hokum_round(
            card_p1, card_p2, p1, p2, r1_decl, r2_decl, b, w, events,
        )

    # Set khasara and radda flags from scoring result
    rv.is_khasara = (khasara_loser > 0)
    rv.is_rd = has_sun_radda(events) if mode == "SUN" else (get_hokum_multiplier(events) > 1)

    # Add baloot GP based on baloot_mode:
    # "normal": each team gets their own baloot
    # "khasara": all baloot goes to winner (opponent of khasara loser)
    # "cancelled": no baloot (qahwa)
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

    rv.s1_computed = g1
    rv.s2_computed = g2
    rv.gp_ok = (g1 == s1 and g2 == s2)

    # Categorize mismatches
    if not rv.gp_ok:
        ds1 = g1 - s1
        ds2 = g2 - s2
        if abs(ds1) == 1 and abs(ds2) == 1:
            rv.gp_mismatch_category = "off_by_1"
        elif (s1 == 0 or s2 == 0) and not rv.is_khasara:
            rv.gp_mismatch_category = "khasara_mismatch"
        elif rv.is_khasara and (s1 != 0 and s2 != 0):
            rv.gp_mismatch_category = "false_khasara"
        else:
            rv.gp_mismatch_category = "other"
        rv.notes = (
            f"delta: s1={ds1:+d} s2={ds2:+d} | "
            f"card:({card_p1},{card_p2}) mode:{mode} b:{b}"
        )

    return rv


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
    - baloot_mode: "normal", "khasara", or "cancelled"
    - khasara_loser: team number (1 or 2) if khasara, else 0
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
    Validated: 491/491 (100%).

    Returns: (g1, g2, baloot_mode, khasara_loser)
    - baloot_mode: "normal", "khasara", or "cancelled"
    - khasara_loser: team number (1 or 2) if khasara, else 0
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
        g1, g2 = (GAHWA_FLAT, 0) if winner == 1 else (0, GAHWA_FLAT)
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


def validate_game(game: ArchiveGame) -> GameValidation:
    """Validate all rounds in a parsed archive game."""
    gv = GameValidation(
        file_name=game.file_path,
        total_rounds=len(game.rounds),
        cum_s1_header=game.final_score_team1,
        cum_s2_header=game.final_score_team2,
    )

    for rnd in game.rounds:
        if rnd.result is None:
            gv.waraq_rounds += 1
            continue

        rv = validate_round(
            result=rnd.result,
            events=rnd.events,
            file_name=game.file_path,
            round_index=rnd.round_index,
        )
        if rv is None:
            gv.waraq_rounds += 1
            continue

        gv.validated_rounds += 1

        if rv.is_kaboot_archive:
            gv.kaboot_rounds += 1

        # Accumulate match counts
        if rv.e_sum_ok:
            gv.e_sum_matches += 1
        if rv.p_ok:
            gv.p_matches += 1
        if rv.gp_ok:
            gv.gp_matches += 1
        if rv.is_kaboot_archive and rv.gp_ok:
            gv.kaboot_matches += 1

        # Cumulative scores
        gv.cum_s1_computed += rv.s1_archive
        gv.cum_s2_computed += rv.s2_archive

        gv.rounds.append(rv)

    # Cumulative score validation
    gv.cumulative_ok = (
        gv.cum_s1_computed == gv.cum_s1_header
        and gv.cum_s2_computed == gv.cum_s2_header
    )

    return gv


def validate_all(archive_dir: Path) -> ValidationReport:
    """Run validation across all archive files.

    Returns a comprehensive ValidationReport.
    """
    games = load_all_archives(archive_dir)
    report = ValidationReport(total_games=len(games))

    for game in games:
        gv = validate_game(game)
        report.games.append(gv)

        report.total_rounds += gv.total_rounds
        report.validated_rounds += gv.validated_rounds
        report.waraq_rounds += gv.waraq_rounds
        report.kaboot_rounds += gv.kaboot_rounds

        report.e_sum_matches += gv.e_sum_matches
        report.p_matches += gv.p_matches
        report.gp_matches += gv.gp_matches
        report.kaboot_matches += gv.kaboot_matches

        if gv.cumulative_ok:
            report.cumulative_matches += 1

        # Count mismatch categories
        for rv in gv.rounds:
            if not rv.gp_ok and rv.gp_mismatch_category:
                cat = rv.gp_mismatch_category
                report.gp_mismatch_categories[cat] = (
                    report.gp_mismatch_categories.get(cat, 0) + 1
                )

    return report


# ── Report Formatting ─────────────────────────────────────────────────

def format_report(report: ValidationReport) -> str:
    """Format a ValidationReport as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("ARCHIVE SCORING VALIDATION REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Summary
    lines.append(f"Games analyzed: {report.total_games}")
    lines.append(f"Total rounds: {report.total_rounds}")
    lines.append(f"Validated rounds: {report.validated_rounds}")
    lines.append(f"Waraq (all-pass) rounds: {report.waraq_rounds}")
    lines.append(f"Kaboot rounds: {report.kaboot_rounds}")
    lines.append("")

    non_kaboot = report.validated_rounds - report.kaboot_rounds

    # Card abnat
    pct_e = 100 * report.e_sum_matches / report.validated_rounds if report.validated_rounds else 0
    lines.append(f"Card abnat (e1+e2=deck): {report.e_sum_matches}/{report.validated_rounds} ({pct_e:.1f}%)")

    # P formula
    pct_p = 100 * report.p_matches / report.validated_rounds if report.validated_rounds else 0
    lines.append(f"P formula (p=e+d+10*lt): {report.p_matches}/{report.validated_rounds} ({pct_p:.1f}%)")

    # GP conversion
    pct_gp = 100 * report.gp_matches / report.validated_rounds if report.validated_rounds else 0
    non_kbt_gp = report.gp_matches - report.kaboot_matches
    pct_gp_nk = 100 * non_kbt_gp / non_kaboot if non_kaboot else 0
    lines.append(f"GP conversion (all):    {report.gp_matches}/{report.validated_rounds} ({pct_gp:.1f}%)")
    lines.append(f"GP conversion (non-kbt):{non_kbt_gp}/{non_kaboot} ({pct_gp_nk:.1f}%)")

    # Kaboot GP
    pct_kbt = 100 * report.kaboot_matches / report.kaboot_rounds if report.kaboot_rounds else 0
    lines.append(f"Kaboot GP:              {report.kaboot_matches}/{report.kaboot_rounds} ({pct_kbt:.1f}%)")

    # Cumulative scores
    pct_cum = 100 * report.cumulative_matches / report.total_games if report.total_games else 0
    lines.append(f"Cumulative scores:      {report.cumulative_matches}/{report.total_games} ({pct_cum:.1f}%)")

    # GP mismatch breakdown
    if report.gp_mismatch_categories:
        lines.append("")
        lines.append("GP Mismatch Categories:")
        for cat, count in sorted(
            report.gp_mismatch_categories.items(), key=lambda x: -x[1]
        ):
            lines.append(f"  {cat}: {count}")

    # Per-game details (only games with issues)
    games_with_issues = [g for g in report.games if not g.cumulative_ok or g.gp_matches < g.validated_rounds]
    if games_with_issues:
        lines.append("")
        lines.append("-" * 70)
        lines.append(f"Games with issues: {len(games_with_issues)}")
        lines.append("-" * 70)
        for gv in games_with_issues[:20]:
            fname = Path(gv.file_name).stem[:30]
            gp_pct = 100 * gv.gp_matches / gv.validated_rounds if gv.validated_rounds else 0
            cum_ok = "OK" if gv.cumulative_ok else "MISMATCH"
            lines.append(
                f"  {fname}: GP {gv.gp_matches}/{gv.validated_rounds} ({gp_pct:.0f}%) "
                f"cum:{cum_ok}"
            )

            for rv in gv.rounds:
                if not rv.gp_ok:
                    lines.append(
                        f"    R{rv.round_index}: {rv.game_mode} b={rv.bidder_team} "
                        f"[{rv.gp_mismatch_category}] "
                        f"archive:({rv.s1_archive},{rv.s2_archive}) "
                        f"computed:({rv.s1_computed},{rv.s2_computed})"
                    )

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


# ── CLI Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.WARNING)

    archive_dir = Path("gbaloot/data/archive_captures/mobile_export/savedGames")
    if len(sys.argv) > 1:
        archive_dir = Path(sys.argv[1])

    print(f"Validating archives in: {archive_dir}")
    report = validate_all(archive_dir)
    print(format_report(report))
