"""
Archive Scoring Validator — Validate Kammelna mobile archive scoring rules.

Validates card abnat, GP conversion, khasara, kaboot, doubling, declarations,
cumulative scores, and the full scoring pipeline against archive data.

Independent implementation that does NOT import the game engine scoring module.
Uses constants from game_engine.models.constants for card point values only.
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
    """Convert SUN card abnat to GP: floor(abnat / 5).

    NOTE: Kammelna uses floor division (truncation), NOT rounding.
    This differs from our game engine which uses (val*2)/10 with >=0.5 rounding.
    """
    return card_abnat // 5


def card_gp_hokum(card_abnat: int) -> int:
    """Convert HOKUM card abnat to GP: floor(abnat / 10), with >0.5 rounding up.

    HOKUM uses asymmetric rounding: strictly greater than 0.5 rounds up.
    e.g., 15/10=1.5 → 1 (not rounded up), but 16/10=1.6 → 2 (rounded up).
    """
    val = card_abnat / 10.0
    dec = val % 1
    if dec > 0.5:
        return int(val) + 1
    return int(val)


def project_gp_sun(project_abnat: int) -> int:
    """Convert SUN project abnat to GP: floor(abnat * 2 / 10)."""
    return (project_abnat * 2) // 10


def project_gp_hokum(project_abnat: int) -> int:
    """Convert HOKUM project abnat to GP: floor(abnat / 10)."""
    return project_abnat // 10


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
    is_kaboot_computed: bool = False  # Not validated here (needs trick data)
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
    is_rd: bool = False  # radda (counter-bid) → 2× GP

    # Mismatch details
    gp_mismatch_category: str = ""  # "off_by_1", "khasara", "doubled", "qayd", etc.
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
    file_name: str,
    round_index: int,
    has_rd: bool = False,
) -> Optional[RoundValidation]:
    """Validate scoring for a single round from archive e=12 result.

    Args:
        result: The e=12 result dict from the archive.
        file_name: Archive file name for error reporting.
        round_index: Index of this round in the game.
        has_rd: Whether the bidding included a 'radda' (counter-challenge).
                When True, the round GP is doubled (winner takes all × 2).

    Returns RoundValidation or None if round cannot be validated (waraq).
    """
    if result is None:
        return None  # Waraq round

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
        is_rd=has_rd,
    )

    # ── 1. Card Abnat Validation (e1 + e2 = deck total) ──────────
    rv.e_sum = e1 + e2
    rv.e_sum_expected = DECK_TOTAL_HOKUM if mode == "HOKUM" else DECK_TOTAL_SUN

    if kbt:
        # Kaboot: winner has all card points. Loser e may be 0 or missing.
        # Valid if winner's e equals deck total (loser's e is 0 or absent).
        winner_e = e1 if w == 1 else e2
        rv.e_sum_ok = (winner_e == rv.e_sum_expected)
    else:
        rv.e_sum_ok = (rv.e_sum == rv.e_sum_expected)

    # ── 2. P Formula Validation (p = e + decl + 10*last_trick) ───
    decl1_total = sum(int(d.get("val", 0)) for d in r1_decl)
    decl2_total = sum(int(d.get("val", 0)) for d in r2_decl)

    if kbt:
        # Kaboot: winner gets all card points + decl + last trick bonus.
        # Loser p may be 0 or just their declarations (varies by archive).
        # Winner always gets the last trick in a kaboot.
        if w == 1:
            rv.p1_computed = e1 + decl1_total + LAST_TRICK_BONUS
            rv.p2_computed = p2  # Accept archive value for loser
        else:
            rv.p1_computed = p1  # Accept archive value for loser
            rv.p2_computed = e2 + decl2_total + LAST_TRICK_BONUS
        rv.p_ok = True  # Kaboot p is validated via winner only
        # Check winner p matches
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

        # Non-baloot declarations from BOTH teams
        decl1_no_baloot = sum(
            int(d.get("val", 0)) for d in r1_decl if d.get("n") != "baloot"
        )
        decl2_no_baloot = sum(
            int(d.get("val", 0)) for d in r2_decl if d.get("n") != "baloot"
        )
        baloot1 = sum(1 for d in r1_decl if d.get("n") == "baloot")
        baloot2 = sum(1 for d in r2_decl if d.get("n") == "baloot")

        # Project GP from both teams (separate computation)
        if mode == "SUN":
            base = KABOOT_GP_SUN
            pg1 = project_gp_sun(decl1_no_baloot)
            pg2 = project_gp_sun(decl2_no_baloot)
        else:
            base = KABOOT_GP_HOKUM
            pg1 = project_gp_hokum(decl1_no_baloot)
            pg2 = project_gp_hokum(decl2_no_baloot)

        # Baloot GP (both teams, immune to all modifiers)
        baloot_gp = (baloot1 + baloot2) * BALOOT_GP

        # Kaboot GP = base + all project GP + all baloot GP → goes to winner
        kaboot_total = base + pg1 + pg2 + baloot_gp

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
                f"base:{base} pg:{pg1}+{pg2} blt:{baloot1}+{baloot2} "
                f"total:{kaboot_total} w:{w} "
                f"archive:({s1},{s2}) computed:({rv.s1_computed},{rv.s2_computed})"
            )
        return rv

    # ── 4. GP Conversion (non-kaboot rounds) ─────────────────────

    # Non-baloot declarations only (baloot is added separately)
    decl1_no_baloot = sum(
        int(d.get("val", 0)) for d in r1_decl if d.get("n") != "baloot"
    )
    decl2_no_baloot = sum(
        int(d.get("val", 0)) for d in r2_decl if d.get("n") != "baloot"
    )
    baloot1 = sum(1 for d in r1_decl if d.get("n") == "baloot")
    baloot2 = sum(1 for d in r2_decl if d.get("n") == "baloot")

    # Card abnat (e + last trick bonus)
    ca1 = e1 + (LAST_TRICK_BONUS if lmw == 1 else 0)
    ca2 = e2 + (LAST_TRICK_BONUS if lmw == 2 else 0)

    # Card GP (mode-specific rounding)
    if mode == "SUN":
        cg1 = card_gp_sun(ca1)
        cg2 = card_gp_sun(ca2)
        target = GP_TARGET_SUN
        pg1 = project_gp_sun(decl1_no_baloot)
        pg2 = project_gp_sun(decl2_no_baloot)
    else:
        cg1 = card_gp_hokum(ca1)
        cg2 = card_gp_hokum(ca2)
        target = GP_TARGET_HOKUM
        pg1 = project_gp_hokum(decl1_no_baloot)
        pg2 = project_gp_hokum(decl2_no_baloot)

    # Tiebreak: remainder goes to bidder team
    total_cg = cg1 + cg2
    if total_cg != target:
        diff = target - total_cg
        if b == 1:
            cg1 += diff
        else:
            cg2 += diff

    # Total GP (card + project)
    g1 = cg1 + pg1
    g2 = cg2 + pg2

    # Khasara: bidder GP <= opponent GP → all to opponent, bidder gets 0
    # Tie handling is ambiguous: most tie rounds show khasara (33 cases)
    # but 17 tie rounds show both teams keeping GP. Using <= as best fit.
    if b == 1 and g1 <= g2:
        rv.is_khasara = True
        pot = g1 + g2
        g1 = 0
        g2 = pot
    elif b == 2 and g2 <= g1:
        rv.is_khasara = True
        pot = g1 + g2
        g2 = 0
        g1 = pot

    # Radda (counter-bid) doubling: winner takes all × 2
    # When rd is set in bidding, the round is a "radda" — GP is doubled
    # and the winner takes the entire pot (loser gets 0).
    if has_rd:
        total = g1 + g2
        if w == 1:
            g1 = total * 2
            g2 = 0
        else:
            g1 = 0
            g2 = total * 2

    # Doubling (em = escalation multiplier from bidding)
    # em is applied ON TOP of radda
    if em >= 4:
        # Gahwa: flat 152 to winner
        if g1 >= g2:
            g1 = GAHWA_FLAT
            g2 = 0
        else:
            g2 = GAHWA_FLAT
            g1 = 0
    elif em > 1:
        g1 *= em
        g2 *= em

    # Baloot (immune to doubling, added after)
    g1 += baloot1 * BALOOT_GP
    g2 += baloot2 * BALOOT_GP

    rv.s1_computed = g1
    rv.s2_computed = g2
    rv.gp_ok = (g1 == s1 and g2 == s2)

    # Categorize mismatches
    if not rv.gp_ok:
        ds1 = g1 - s1
        ds2 = g2 - s2
        if cc:
            rv.gp_mismatch_category = "qayd"
        elif em > 1:
            rv.gp_mismatch_category = "doubled"
        elif (s1 == 0 or s2 == 0) and not rv.is_khasara:
            rv.gp_mismatch_category = "non_bidder_khasara"
        elif rv.is_khasara and (s1 != 0 and s2 != 0):
            rv.gp_mismatch_category = "false_khasara"
        elif g1 == g2 and (s1 != s2):
            rv.gp_mismatch_category = "tie_mismatch"
        elif abs(ds1) == 1 and abs(ds2) == 1:
            rv.gp_mismatch_category = "off_by_1"
        elif abs(ds1) <= 2 and abs(ds2) <= 2:
            rv.gp_mismatch_category = "off_by_2"
        else:
            rv.gp_mismatch_category = "other"
        rv.notes = (
            f"delta: s1={ds1:+d} s2={ds2:+d} | "
            f"ca:{ca1},{ca2} cg:{cg1},{cg2} pg:{pg1},{pg2} "
            f"kh:{rv.is_khasara} em:{em}"
        )

    return rv


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

        # Check if bidding included a 'radda' (rd field in e=2 events)
        has_rd = any(
            ev.get("e") == 2 and ev.get("rd")
            for ev in rnd.events
        )

        rv = validate_round(
            result=rnd.result,
            file_name=game.file_path,
            round_index=rnd.round_index,
            has_rd=has_rd,
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

    # Card abnat (non-kaboot only — kaboot rounds have one team with all cards)
    non_kbt_e = report.e_sum_matches - report.kaboot_rounds  # All kaboot pass
    pct_e_nk = 100 * non_kbt_e / non_kaboot if non_kaboot else 0
    pct_e = 100 * report.e_sum_matches / report.validated_rounds if report.validated_rounds else 0
    lines.append(f"Card abnat (e1+e2=deck): {report.e_sum_matches}/{report.validated_rounds} ({pct_e:.1f}%)")

    # P formula
    pct_p = 100 * report.p_matches / report.validated_rounds if report.validated_rounds else 0
    lines.append(f"P formula (p=e+d+10*lt): {report.p_matches}/{report.validated_rounds} ({pct_p:.1f}%)")

    # GP conversion — overall and non-kaboot
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
        for gv in games_with_issues[:20]:  # Limit output
            fname = Path(gv.file_name).stem[:30]
            gp_pct = 100 * gv.gp_matches / gv.validated_rounds if gv.validated_rounds else 0
            cum_ok = "OK" if gv.cumulative_ok else "MISMATCH"
            lines.append(
                f"  {fname}: GP {gv.gp_matches}/{gv.validated_rounds} ({gp_pct:.0f}%) "
                f"cum:{cum_ok}"
            )

            # Show round-level mismatches
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

    archive_dir = Path("gbaloot/data/archive_captures/kammelna_export/savedGames")
    if len(sys.argv) > 1:
        archive_dir = Path(sys.argv[1])

    print(f"Validating archives in: {archive_dir}")
    report = validate_all(archive_dir)
    print(format_report(report))
