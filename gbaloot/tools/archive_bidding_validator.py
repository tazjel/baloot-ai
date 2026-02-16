"""
Archive Bidding Validator — Extract and validate bidding statistics from archives.

Walks all e=2 (bid) events across 109 Kammelna mobile game archives to:
1. Validate bidding rules (turn order, bid overrides, phase transitions)
2. Compute aggregate statistics (mode distribution, doubling, waraq rate, etc.)
3. Extract per-round bidding details for downstream strategy analysis.

Independent implementation — does NOT import the game engine bidding module.
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
    EVT_ROUND_START,
    EVT_BID,
)

logger = logging.getLogger(__name__)

# ── Bid action constants ────────────────────────────────────────────

# Phase 1 (Round 1) bids
BID_PASS = "pass"
BID_HOKOM = "hokom"
BID_SUN = "sun"
BID_ASHKAL = "ashkal"
BID_BEFORE_YOU = "beforeyou"

# Phase transition
BID_THANY = "thany"        # "Second" — dealer declares Round 2
BID_WALA = "wala"           # "Nor me" — pass in Round 2

# Phase 2 (Round 2) bids
BID_HOKOM2 = "hokom2"       # HOKUM bid in Round 2
BID_TURN_TO_SUN = "turntosun"  # Switch from HOKUM to SUN
BID_WARAQ = "waraq"         # All-pass → re-deal

# Suit selection
BID_CLUBS = "clubs"
BID_HEARTS = "hearts"
BID_SPADES = "spades"
BID_DIAMONDS = "diamonds"
SUIT_BIDS = {BID_CLUBS, BID_HEARTS, BID_SPADES, BID_DIAMONDS}

# HOKUM variants (doubling)
BID_HOKOM_CLOSE = "hokomclose"
BID_HOKOM_OPEN = "hokomopen"

# Doubling escalation
BID_DOUBLE = "double"
BID_TRIPLE = "triple"
BID_QAHWA = "qahwa"

# All known bid actions
ALL_BID_ACTIONS = {
    BID_PASS, BID_HOKOM, BID_SUN, BID_ASHKAL, BID_BEFORE_YOU,
    BID_THANY, BID_WALA, BID_HOKOM2, BID_TURN_TO_SUN, BID_WARAQ,
    BID_CLUBS, BID_HEARTS, BID_SPADES, BID_DIAMONDS,
    BID_HOKOM_CLOSE, BID_HOKOM_OPEN,
    BID_DOUBLE, BID_TRIPLE, BID_QAHWA,
    "",  # Empty bid action (data quality issue, 1 occurrence)
}

# Bids that establish/change the contract
CONTRACT_BIDS = {BID_HOKOM, BID_SUN, BID_ASHKAL, BID_BEFORE_YOU, BID_HOKOM2, BID_TURN_TO_SUN}

# Bids that represent doubling actions
DOUBLING_BIDS = {BID_HOKOM_CLOSE, BID_HOKOM_OPEN, BID_DOUBLE, BID_TRIPLE, BID_QAHWA}


# ── Dataclasses ─────────────────────────────────────────────────────

@dataclass
class BidEvent:
    """Single parsed bid event from the archive."""
    player_seat: int        # 1-indexed seat
    action: str             # bid action string
    rb: int = -1            # reigning bidder (-1 = no bid yet)
    gm: Optional[int] = None   # game mode (1=SUN, 2=HOKUM, 3=ASHKAL)
    ts: Optional[int] = None   # trump suit
    gem: Optional[int] = None  # doubling level (1-4)
    rd: Optional[int] = None   # radda (doubler) seat
    hc: bool = False            # hokum closed flag


@dataclass
class RoundBiddingResult:
    """Bidding analysis for one round."""
    file_name: str
    round_index: int
    dealer_seat: int            # 1-indexed
    bid_events: list[BidEvent] = field(default_factory=list)

    # Outcome
    is_waraq: bool = False          # All-pass re-deal
    went_to_round2: bool = False    # Bidding went to Round 2
    game_mode: Optional[str] = None  # "SUN", "HOKUM", or None (waraq)
    is_ashkal: bool = False         # Ashkal variant of SUN
    bidder_seat: int = -1           # 1-indexed winner of the bid

    # Doubling
    doubling_level: int = 0         # 0=normal, 1=double, 2=triple, 3=4x, 4=gahwa
    is_hokum_closed: bool = False   # Closed HOKUM variant
    radda_seat: int = -1            # Who doubled (1-indexed)

    # Bid counts
    total_bids: int = 0             # Total bid events
    r1_bid_type: Optional[str] = None  # First contract bid ("hokom", "sun", "ashkal")
    had_before_you: bool = False    # SUN counter-bid occurred
    had_turn_to_sun: bool = False   # HOKUM→SUN switch occurred

    # Position info
    bidder_position: int = -1       # Bidder's clockwise position from dealer (1-4)

    # Validation
    issues: list[str] = field(default_factory=list)


@dataclass
class GameBiddingResult:
    """Bidding analysis for one game (archive file)."""
    file_name: str
    total_rounds: int = 0
    rounds: list[RoundBiddingResult] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@dataclass
class BiddingStatisticsReport:
    """Aggregate bidding statistics across all archives."""
    total_archives: int = 0
    total_rounds: int = 0

    # Mode distribution
    hokum_count: int = 0
    sun_count: int = 0
    ashkal_count: int = 0
    waraq_count: int = 0

    # Bidding phase
    round1_resolved: int = 0    # Bid won in Round 1
    round2_resolved: int = 0    # Bid won in Round 2
    went_to_round2: int = 0     # Total that went to R2 (resolved + waraq)

    # Doubling distribution
    doubling_dist: dict[int, int] = field(default_factory=lambda: {
        0: 0, 1: 0, 2: 0, 3: 0, 4: 0
    })

    # HOKUM variants
    hokum_open: int = 0
    hokum_closed: int = 0

    # Special bids
    before_you_count: int = 0
    turn_to_sun_count: int = 0

    # Bidder position distribution (1-4, relative to dealer)
    bidder_position_dist: dict[int, int] = field(default_factory=lambda: {
        1: 0, 2: 0, 3: 0, 4: 0
    })

    # Bid action frequency
    bid_action_counts: dict[str, int] = field(default_factory=dict)

    # Per-game results
    games: list[GameBiddingResult] = field(default_factory=list)

    # Validation
    total_issues: int = 0
    unknown_bid_actions: set[str] = field(default_factory=set)

    @property
    def played_rounds(self) -> int:
        """Rounds that were actually played (not waraq)."""
        return self.total_rounds - self.waraq_count

    @property
    def hokum_pct(self) -> float:
        """Percentage of played rounds that were HOKUM."""
        return 100 * self.hokum_count / self.played_rounds if self.played_rounds else 0

    @property
    def sun_pct(self) -> float:
        """Percentage of played rounds that were SUN (including ashkal)."""
        return 100 * (self.sun_count + self.ashkal_count) / self.played_rounds if self.played_rounds else 0

    @property
    def waraq_pct(self) -> float:
        """Percentage of total rounds that were waraq (all-pass re-deal)."""
        return 100 * self.waraq_count / self.total_rounds if self.total_rounds else 0

    @property
    def round2_pct(self) -> float:
        """Percentage of total rounds that went to Round 2."""
        return 100 * self.went_to_round2 / self.total_rounds if self.total_rounds else 0

    @property
    def doubling_pct(self) -> float:
        """Percentage of played rounds with any doubling."""
        doubled = sum(v for k, v in self.doubling_dist.items() if k > 0)
        return 100 * doubled / self.played_rounds if self.played_rounds else 0

    @property
    def avg_bidder_position(self) -> float:
        """Average bidder position relative to dealer (1-4)."""
        total = sum(pos * cnt for pos, cnt in self.bidder_position_dist.items())
        count = sum(self.bidder_position_dist.values())
        return total / count if count else 0

    def summary(self) -> str:
        """Human-readable summary of bidding statistics."""
        lines = [
            "=" * 70,
            "BIDDING STATISTICS REPORT",
            "=" * 70,
            f"Archives analyzed:    {self.total_archives}",
            f"Total rounds:         {self.total_rounds}",
            f"Played rounds:        {self.played_rounds}",
            "",
            "── Mode Distribution ──────────────────────────────────────────",
            f"  HOKUM:              {self.hokum_count:>5} ({self.hokum_pct:.1f}% of played)",
            f"  SUN:                {self.sun_count:>5} ({100*self.sun_count/self.played_rounds:.1f}% of played)" if self.played_rounds else "",
            f"  Ashkal:             {self.ashkal_count:>5} ({100*self.ashkal_count/self.played_rounds:.1f}% of played)" if self.played_rounds else "",
            f"  Waraq (re-deal):    {self.waraq_count:>5} ({self.waraq_pct:.1f}% of total)",
            "",
            "── Bidding Phase ──────────────────────────────────────────────",
            f"  Resolved in R1:     {self.round1_resolved:>5} ({100*self.round1_resolved/self.total_rounds:.1f}%)" if self.total_rounds else "",
            f"  Went to R2:         {self.went_to_round2:>5} ({self.round2_pct:.1f}%)",
            f"  Resolved in R2:     {self.round2_resolved:>5} ({100*self.round2_resolved/self.went_to_round2:.1f}% of R2)" if self.went_to_round2 else "",
            "",
            "── Doubling Distribution ──────────────────────────────────────",
            f"  Normal (×1):        {self.doubling_dist[0]:>5}",
            f"  Double (×2):        {self.doubling_dist[1]:>5}",
            f"  Triple (×3):        {self.doubling_dist[2]:>5}",
            f"  Four (×4):          {self.doubling_dist[3]:>5}",
            f"  Gahwa (max):        {self.doubling_dist[4]:>5}",
            f"  Any doubling:       {self.doubling_pct:.1f}% of played rounds",
            "",
            "── HOKUM Variants ─────────────────────────────────────────────",
            f"  Open:               {self.hokum_open:>5}",
            f"  Closed:             {self.hokum_closed:>5}",
            "",
            "── Special Bids ───────────────────────────────────────────────",
            f"  Before-you (SUN counter): {self.before_you_count:>3}",
            f"  Turn-to-SUN (switch):     {self.turn_to_sun_count:>3}",
            "",
            "── Bidder Position (from dealer) ──────────────────────────────",
        ]
        for pos in range(1, 5):
            cnt = self.bidder_position_dist[pos]
            pct = 100 * cnt / self.played_rounds if self.played_rounds else 0
            lines.append(f"  Position {pos}:         {cnt:>5} ({pct:.1f}%)")
        lines.append(f"  Average:            {self.avg_bidder_position:.2f}")

        lines.extend([
            "",
            "── Bid Action Frequency ───────────────────────────────────────",
        ])
        for action, count in sorted(self.bid_action_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {action:<20s} {count:>5}")

        if self.unknown_bid_actions:
            lines.extend([
                "",
                f"⚠ Unknown bid actions: {self.unknown_bid_actions}",
            ])

        lines.extend([
            "",
            f"Total validation issues: {self.total_issues}",
            "=" * 70,
        ])
        return "\n".join(lines)


# ── Round Bidding Analysis ──────────────────────────────────────────

def analyze_round_bidding(
    rnd: ArchiveRound,
    file_name: str,
) -> Optional[RoundBiddingResult]:
    """Analyze bidding for one round.

    Extracts the full bidding sequence, determines outcome,
    and validates bidding rules.

    Returns None if no bid events found (shouldn't happen in valid data).
    """
    events = rnd.events

    # Find dealer from e=1 event
    dealer_seat = -1
    for evt in events:
        if evt.get("e") == EVT_ROUND_START:
            dealer_seat = evt.get("p", -1)
            break

    result = RoundBiddingResult(
        file_name=file_name,
        round_index=rnd.round_index,
        dealer_seat=dealer_seat,
    )

    # Extract all bid events
    bid_events = []
    for evt in events:
        if evt.get("e") != EVT_BID:
            continue
        be = BidEvent(
            player_seat=evt.get("p", -1),
            action=evt.get("b", ""),
            rb=evt.get("rb", -1),
            gm=evt.get("gm"),
            ts=evt.get("ts"),
            gem=evt.get("gem"),
            rd=evt.get("rd"),
            hc=bool(evt.get("hc")),
        )
        bid_events.append(be)

    if not bid_events:
        return None

    result.bid_events = bid_events
    result.total_bids = len(bid_events)

    # Analyze the bidding sequence
    _analyze_sequence(result, bid_events)

    # Validate bidding rules
    _validate_rules(result, bid_events)

    return result


def _analyze_sequence(result: RoundBiddingResult, bids: list[BidEvent]) -> None:
    """Determine outcome from bid sequence."""
    last_gm = None
    last_rb = -1
    max_gem = 0
    last_rd = -1
    is_closed = False

    for be in bids:
        action = be.action

        # Track waraq
        if action == BID_WARAQ:
            result.is_waraq = True
            return

        # Track Round 2 transition
        if action == BID_THANY:
            result.went_to_round2 = True

        # Track contract bids
        if action in {BID_HOKOM, BID_SUN, BID_ASHKAL, BID_BEFORE_YOU, BID_HOKOM2, BID_TURN_TO_SUN}:
            if result.r1_bid_type is None and action in {BID_HOKOM, BID_SUN, BID_ASHKAL}:
                result.r1_bid_type = action

        # Track special bids
        if action == BID_BEFORE_YOU:
            result.had_before_you = True
        if action == BID_TURN_TO_SUN:
            result.had_turn_to_sun = True

        # Track game mode
        if be.gm is not None:
            last_gm = be.gm

        # Track reigning bidder
        if be.rb > 0:
            last_rb = be.rb

        # Track doubling
        if be.gem is not None and be.gem > max_gem:
            max_gem = be.gem
        if be.rd is not None and be.rd > 0:
            last_rd = be.rd

        # Track HOKUM closed
        if be.hc:
            is_closed = True

    # Set game mode
    if last_gm is not None:
        mode_map = {1: "SUN", 2: "HOKUM", 3: "SUN"}
        result.game_mode = mode_map.get(last_gm)
        result.is_ashkal = (last_gm == 3)

    # Set bidder
    result.bidder_seat = last_rb

    # Set doubling level
    result.doubling_level = max_gem
    result.radda_seat = last_rd
    result.is_hokum_closed = is_closed

    # Compute bidder position relative to dealer
    if last_rb > 0 and result.dealer_seat > 0:
        # Position = how many seats clockwise from dealer
        # Dealer is seat D, bidding starts at D+1 (position 1)
        pos = (last_rb - result.dealer_seat) % 4
        if pos == 0:
            pos = 4  # Dealer is position 4 (last to bid)
        result.bidder_position = pos


def _validate_rules(result: RoundBiddingResult, bids: list[BidEvent]) -> None:
    """Validate bidding rules against the sequence."""
    if result.is_waraq:
        return  # No rules to validate for waraq

    # Rule: Check for unknown bid actions
    for be in bids:
        if be.action not in ALL_BID_ACTIONS:
            result.issues.append(f"Unknown bid action: {be.action}")

    # Rule: Bidder seat should be set
    if result.bidder_seat <= 0 and not result.is_waraq:
        result.issues.append("No bidder seat resolved")

    # Rule: Game mode should be set
    if result.game_mode is None and not result.is_waraq:
        result.issues.append("No game mode resolved")

    # Rule: SUN overrides HOKUM (check gm transitions)
    gm_sequence = []
    for be in bids:
        if be.gm is not None and (not gm_sequence or gm_sequence[-1] != be.gm):
            gm_sequence.append(be.gm)

    # Valid transitions: 2→1 (HOKUM→SUN override), 2→3 (HOKUM→ASHKAL override)
    for i in range(1, len(gm_sequence)):
        prev, curr = gm_sequence[i - 1], gm_sequence[i]
        if prev == 1 and curr == 2:
            # SUN→HOKUM — invalid (HOKUM can't override SUN)
            result.issues.append(f"Invalid gm transition: SUN→HOKUM")

    # Rule: R1 bidding — first 4 bids should be from dealer+1 clockwise
    if result.dealer_seat > 0:
        r1_bids = []
        for be in bids:
            if be.action in {BID_THANY, BID_WALA, BID_WARAQ}:
                break
            r1_bids.append(be)

        if len(r1_bids) >= 4:
            expected_first = (result.dealer_seat % 4) + 1
            actual_first = r1_bids[0].player_seat
            if actual_first != expected_first:
                result.issues.append(
                    f"R1 first bidder: expected seat {expected_first}, got {actual_first}"
                )


# ── Game-Level Analysis ─────────────────────────────────────────────

def analyze_game_bidding(game: ArchiveGame) -> GameBiddingResult:
    """Analyze bidding for all rounds in a game."""
    file_name = Path(game.file_path).name
    result = GameBiddingResult(
        file_name=file_name,
        total_rounds=len(game.rounds),
    )

    for rnd in game.rounds:
        rb = analyze_round_bidding(rnd, file_name)
        if rb is not None:
            result.rounds.append(rb)
            result.issues.extend(rb.issues)

    return result


# ── Full Pipeline ───────────────────────────────────────────────────

def validate_all_bidding(archive_dir: Path) -> BiddingStatisticsReport:
    """Run bidding analysis across all archive files.

    Computes aggregate statistics, validates bidding rules, and
    returns a full report.

    Args:
        archive_dir: Path to savedGames directory.

    Returns:
        BiddingStatisticsReport with all stats and per-game details.
    """
    games = load_all_archives(archive_dir)
    report = BiddingStatisticsReport(total_archives=len(games))

    for game in games:
        gr = analyze_game_bidding(game)
        report.games.append(gr)
        report.total_issues += len(gr.issues)

        for rb in gr.rounds:
            report.total_rounds += 1

            # Count bid actions
            for be in rb.bid_events:
                action = be.action
                report.bid_action_counts[action] = report.bid_action_counts.get(action, 0) + 1
                if action not in ALL_BID_ACTIONS:
                    report.unknown_bid_actions.add(action)

            # Mode distribution
            if rb.is_waraq:
                report.waraq_count += 1
            elif rb.game_mode == "HOKUM":
                report.hokum_count += 1
            elif rb.game_mode == "SUN":
                if rb.is_ashkal:
                    report.ashkal_count += 1
                else:
                    report.sun_count += 1

            # Round 2 tracking
            if rb.went_to_round2:
                report.went_to_round2 += 1
                if not rb.is_waraq:
                    report.round2_resolved += 1
            elif not rb.is_waraq:
                report.round1_resolved += 1

            # Doubling
            if not rb.is_waraq:
                report.doubling_dist[rb.doubling_level] = \
                    report.doubling_dist.get(rb.doubling_level, 0) + 1

            # HOKUM variants
            if rb.is_hokum_closed:
                report.hokum_closed += 1
            elif rb.game_mode == "HOKUM" and rb.doubling_level > 0:
                # Only HOKUM with doubling and NOT closed = open
                report.hokum_open += 1

            # Special bids
            if rb.had_before_you:
                report.before_you_count += 1
            if rb.had_turn_to_sun:
                report.turn_to_sun_count += 1

            # Bidder position
            if not rb.is_waraq and rb.bidder_position > 0:
                report.bidder_position_dist[rb.bidder_position] = \
                    report.bidder_position_dist.get(rb.bidder_position, 0) + 1

    return report


# ── CLI Entry Point ─────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    archive_dir = Path(
        "gbaloot/data/archive_captures/kammelna_export/savedGames"
    )
    if len(sys.argv) > 1:
        archive_dir = Path(sys.argv[1])

    report = validate_all_bidding(archive_dir)
    print(report.summary())
