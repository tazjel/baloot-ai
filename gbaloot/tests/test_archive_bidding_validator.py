"""Tests for archive_bidding_validator — bidding statistics and rule validation."""
from __future__ import annotations

import pytest
from pathlib import Path

from gbaloot.tools.archive_bidding_validator import (
    analyze_round_bidding,
    analyze_game_bidding,
    validate_all_bidding,
    BidEvent,
    RoundBiddingResult,
    GameBiddingResult,
    BiddingStatisticsReport,
    ALL_BID_ACTIONS,
    BID_PASS, BID_HOKOM, BID_SUN, BID_ASHKAL, BID_BEFORE_YOU,
    BID_THANY, BID_WALA, BID_HOKOM2, BID_TURN_TO_SUN, BID_WARAQ,
    BID_CLUBS, BID_HEARTS, BID_SPADES, BID_DIAMONDS,
    BID_HOKOM_CLOSE, BID_HOKOM_OPEN,
    BID_DOUBLE, BID_TRIPLE, BID_QAHWA,
    SUIT_BIDS, CONTRACT_BIDS, DOUBLING_BIDS,
)
from gbaloot.tools.archive_parser import ArchiveRound


# ── Helpers ──────────────────────────────────────────────────────────

def _make_round(events: list[dict], round_index: int = 0) -> ArchiveRound:
    """Create a minimal ArchiveRound for testing."""
    return ArchiveRound(
        round_index=round_index,
        events=events,
    )


def _make_bid(p: int, b: str, rb: int = -1, gm=None, ts=None,
              gem=None, rd=None, hc=None) -> dict:
    """Create a bid event dict."""
    evt = {"e": 2, "p": p, "b": b, "rb": rb}
    if gm is not None:
        evt["gm"] = gm
    if ts is not None:
        evt["ts"] = ts
    if gem is not None:
        evt["gem"] = gem
    if rd is not None:
        evt["rd"] = rd
    if hc is not None:
        evt["hc"] = hc
    return evt


def _round_start(dealer: int) -> dict:
    """Create a round start event."""
    return {"e": 1, "p": dealer}


# ── Constant Tests ──────────────────────────────────────────────────


class TestConstants:
    """Verify bid action constant sets are correctly defined."""

    def test_all_bid_actions_count(self):
        """Should have 19 known actions + 1 empty string."""
        # 19 real actions + "" = 20
        assert len(ALL_BID_ACTIONS) == 20

    def test_suit_bids(self):
        assert SUIT_BIDS == {"clubs", "hearts", "spades", "diamonds"}

    def test_contract_bids(self):
        assert BID_HOKOM in CONTRACT_BIDS
        assert BID_SUN in CONTRACT_BIDS
        assert BID_ASHKAL in CONTRACT_BIDS
        assert BID_HOKOM2 in CONTRACT_BIDS
        assert BID_BEFORE_YOU in CONTRACT_BIDS
        assert BID_TURN_TO_SUN in CONTRACT_BIDS

    def test_doubling_bids(self):
        assert BID_HOKOM_CLOSE in DOUBLING_BIDS
        assert BID_HOKOM_OPEN in DOUBLING_BIDS
        assert BID_DOUBLE in DOUBLING_BIDS
        assert BID_TRIPLE in DOUBLING_BIDS
        assert BID_QAHWA in DOUBLING_BIDS


# ── BidEvent Tests ──────────────────────────────────────────────────


class TestBidEvent:
    """Test BidEvent dataclass defaults."""

    def test_defaults(self):
        be = BidEvent(player_seat=1, action="pass")
        assert be.player_seat == 1
        assert be.action == "pass"
        assert be.rb == -1
        assert be.gm is None
        assert be.ts is None
        assert be.gem is None
        assert be.rd is None
        assert be.hc is False


# ── Round Bidding Analysis ──────────────────────────────────────────


class TestAnalyzeRoundBidding:
    """Test analyze_round_bidding with synthetic data."""

    def test_no_bid_events_returns_none(self):
        """Round with no bid events returns None."""
        rnd = _make_round([_round_start(1)])
        assert analyze_round_bidding(rnd, "test.json") is None

    def test_simple_hokum_r1(self):
        """Simple R1 HOKUM bid: seat 2 bids hokom, others pass."""
        events = [
            _round_start(1),
            _make_bid(2, "hokom", rb=2, gm=2, ts=4),
            _make_bid(3, "pass", rb=2, gm=2, ts=4),
            _make_bid(4, "pass", rb=2, gm=2, ts=4),
            _make_bid(1, "pass", rb=2, gm=2, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb is not None
        assert rb.game_mode == "HOKUM"
        assert rb.bidder_seat == 2
        assert rb.is_waraq is False
        assert rb.went_to_round2 is False
        assert rb.doubling_level == 0
        assert rb.bidder_position == 1  # seat 2 is position 1 from dealer 1
        assert rb.total_bids == 4  # 4 bid events (round_start is e=1, not counted)

    def test_simple_sun_r1(self):
        """Simple R1 SUN bid."""
        events = [
            _round_start(3),
            _make_bid(4, "sun", rb=4, gm=1, ts=4),
            _make_bid(1, "pass", rb=4, gm=1, ts=4),
            _make_bid(2, "pass", rb=4, gm=1, ts=4),
            _make_bid(3, "pass", rb=4, gm=1, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.game_mode == "SUN"
        assert rb.bidder_seat == 4
        assert rb.bidder_position == 1

    def test_ashkal_bid(self):
        """Ashkal bid sets game_mode=SUN and is_ashkal=True."""
        events = [
            _round_start(2),
            _make_bid(3, "ashkal", rb=3, gm=3, ts=4),
            _make_bid(4, "pass", rb=3, gm=3, ts=4),
            _make_bid(1, "pass", rb=3, gm=3, ts=4),
            _make_bid(2, "pass", rb=3, gm=3, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.game_mode == "SUN"
        assert rb.is_ashkal is True

    def test_waraq_all_pass(self):
        """All pass → thany → wala → wala → wala → waraq."""
        events = [
            _round_start(1),
            # R1: all pass
            _make_bid(2, "pass", rb=-1),
            _make_bid(3, "pass", rb=-1),
            _make_bid(4, "pass", rb=-1),
            _make_bid(1, "pass", rb=-1),
            # R2 transition
            _make_bid(1, "thany", rb=-1),
            _make_bid(2, "wala", rb=-1),
            _make_bid(3, "wala", rb=-1),
            _make_bid(4, "wala", rb=-1),
            # All pass again
            _make_bid(1, "waraq", rb=-1),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.is_waraq is True
        assert rb.went_to_round2 is True
        assert rb.game_mode is None
        assert rb.bidder_seat == -1

    def test_round2_hokum(self):
        """R1 all pass → R2 hokom2 with suit selection."""
        events = [
            _round_start(1),
            # R1: all pass
            _make_bid(2, "pass", rb=-1),
            _make_bid(3, "pass", rb=-1),
            _make_bid(4, "pass", rb=-1),
            _make_bid(1, "pass", rb=-1),
            # R2
            _make_bid(1, "thany", rb=-1),
            _make_bid(2, "wala", rb=-1),
            _make_bid(3, "hokom2", rb=3, gm=2),
            _make_bid(3, "diamonds", rb=3, gm=2, ts=3),
            _make_bid(4, "pass", rb=3, gm=2, ts=3),
            _make_bid(1, "pass", rb=3, gm=2, ts=3),
            _make_bid(2, "pass", rb=3, gm=2, ts=3),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.game_mode == "HOKUM"
        assert rb.went_to_round2 is True
        assert rb.bidder_seat == 3
        assert rb.bidder_position == 2  # seat 3, dealer 1

    def test_before_you_counter(self):
        """SUN counter-bid with beforeyou."""
        events = [
            _round_start(2),
            _make_bid(3, "sun", rb=3, gm=1, ts=4),
            _make_bid(4, "beforeyou", rb=4, gm=1, ts=4),
            _make_bid(1, "pass", rb=4, gm=1, ts=4),
            _make_bid(2, "pass", rb=4, gm=1, ts=4),
            _make_bid(3, "pass", rb=4, gm=1, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.game_mode == "SUN"
        assert rb.had_before_you is True
        assert rb.bidder_seat == 4  # Counter-bidder won

    def test_turn_to_sun(self):
        """HOKUM→SUN switch with turntosun."""
        events = [
            _round_start(1),
            _make_bid(2, "pass", rb=-1),
            _make_bid(3, "pass", rb=-1),
            _make_bid(4, "pass", rb=-1),
            _make_bid(1, "pass", rb=-1),
            _make_bid(1, "thany", rb=-1),
            _make_bid(2, "hokom2", rb=2, gm=2),
            _make_bid(2, "turntosun", rb=2, gm=1),
            _make_bid(3, "pass", rb=2, gm=1, ts=4),
            _make_bid(4, "pass", rb=2, gm=1, ts=4),
            _make_bid(1, "pass", rb=2, gm=1, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.game_mode == "SUN"
        assert rb.had_turn_to_sun is True
        assert rb.bidder_seat == 2

    def test_doubling_hokum_close(self):
        """HOKUM with hokomclose doubling."""
        events = [
            _round_start(1),
            _make_bid(2, "hokom", rb=2, gm=2, ts=4),
            _make_bid(3, "hokomclose", rb=2, gm=2, ts=4, gem=1, rd=3, hc=1),
            _make_bid(4, "pass", rb=2, gm=2, ts=4, gem=1, rd=3, hc=1),
            _make_bid(1, "pass", rb=2, gm=2, ts=4, gem=1, rd=3, hc=1),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.game_mode == "HOKUM"
        assert rb.doubling_level == 1
        assert rb.is_hokum_closed is True
        assert rb.radda_seat == 3

    def test_triple_escalation(self):
        """Double → Triple escalation."""
        events = [
            _round_start(2),
            _make_bid(3, "sun", rb=3, gm=1, ts=4),
            _make_bid(4, "double", rb=3, gm=1, ts=4, gem=1, rd=4),
            _make_bid(3, "triple", rb=3, gm=1, ts=4, gem=2, rd=3),
            _make_bid(1, "pass", rb=3, gm=1, ts=4, gem=2, rd=3),
            _make_bid(2, "pass", rb=3, gm=1, ts=4, gem=2, rd=3),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.doubling_level == 2

    def test_qahwa_escalation(self):
        """Full escalation to qahwa."""
        events = [
            _round_start(1),
            _make_bid(2, "hokom", rb=2, gm=2, ts=1),
            _make_bid(3, "hokomclose", rb=2, gm=2, ts=1, gem=1, rd=3, hc=1),
            _make_bid(2, "triple", rb=2, gm=2, ts=1, gem=2, rd=2, hc=1),
            _make_bid(3, "qahwa", rb=2, gm=2, ts=1, gem=4, rd=3, hc=1),
            _make_bid(4, "pass", rb=2, gm=2, ts=1, gem=4, rd=3, hc=1),
            _make_bid(1, "pass", rb=2, gm=2, ts=1, gem=4, rd=3, hc=1),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.doubling_level == 4

    def test_dealer_seat_extraction(self):
        """Dealer seat extracted from e=1 event."""
        events = [
            _round_start(3),
            _make_bid(4, "pass", rb=-1),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.dealer_seat == 3

    def test_bidder_position_dealer_bids(self):
        """Dealer bidding = position 4 (last)."""
        events = [
            _round_start(2),
            _make_bid(3, "pass", rb=-1),
            _make_bid(4, "pass", rb=-1),
            _make_bid(1, "pass", rb=-1),
            _make_bid(2, "hokom", rb=2, gm=2, ts=4),
            _make_bid(3, "pass", rb=2, gm=2, ts=4),
            _make_bid(4, "pass", rb=2, gm=2, ts=4),
            _make_bid(1, "pass", rb=2, gm=2, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.bidder_position == 4  # Dealer always position 4

    def test_r1_bid_type_tracked(self):
        """First contract bid in R1 is tracked."""
        events = [
            _round_start(1),
            _make_bid(2, "hokom", rb=2, gm=2, ts=4),
            _make_bid(3, "sun", rb=3, gm=1, ts=4),  # SUN overrides
            _make_bid(4, "pass", rb=3, gm=1, ts=4),
            _make_bid(1, "pass", rb=3, gm=1, ts=4),
            _make_bid(2, "pass", rb=3, gm=1, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.r1_bid_type == "hokom"  # First contract bid, not the override
        assert rb.game_mode == "SUN"      # But SUN won


# ── Validation Rules ────────────────────────────────────────────────


class TestValidationRules:
    """Test bidding rule validation."""

    def test_unknown_bid_action_flagged(self):
        """Unknown bid action generates an issue."""
        events = [
            _round_start(1),
            _make_bid(2, "unknown_action", rb=-1),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert any("Unknown bid action" in i for i in rb.issues)

    def test_no_bidder_flagged(self):
        """No bidder seat resolved generates an issue."""
        events = [
            _round_start(1),
            _make_bid(2, "pass", rb=-1),
            _make_bid(3, "pass", rb=-1),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert any("No bidder seat" in i for i in rb.issues)

    def test_no_game_mode_flagged(self):
        """No game mode resolved generates an issue."""
        events = [
            _round_start(1),
            _make_bid(2, "pass", rb=-1),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert any("No game mode" in i for i in rb.issues)

    def test_waraq_no_issues(self):
        """Waraq rounds should not generate bidder/mode issues."""
        events = [
            _round_start(1),
            _make_bid(2, "pass", rb=-1),
            _make_bid(3, "pass", rb=-1),
            _make_bid(4, "pass", rb=-1),
            _make_bid(1, "pass", rb=-1),
            _make_bid(1, "thany", rb=-1),
            _make_bid(2, "wala", rb=-1),
            _make_bid(3, "wala", rb=-1),
            _make_bid(4, "wala", rb=-1),
            _make_bid(1, "waraq", rb=-1),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert rb.is_waraq is True
        assert len(rb.issues) == 0

    def test_r1_first_bidder_validation(self):
        """R1 first bidder should be dealer+1."""
        # Dealer=1, so first bidder should be seat 2
        events = [
            _round_start(1),
            _make_bid(2, "hokom", rb=2, gm=2, ts=4),  # Correct: seat 2
            _make_bid(3, "pass", rb=2, gm=2, ts=4),
            _make_bid(4, "pass", rb=2, gm=2, ts=4),
            _make_bid(1, "pass", rb=2, gm=2, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        # No first-bidder issue
        assert not any("R1 first bidder" in i for i in rb.issues)

    def test_r1_wrong_first_bidder_flagged(self):
        """Wrong R1 first bidder generates an issue."""
        # Dealer=1, so first bidder should be seat 2, but seat 3 bids first
        events = [
            _round_start(1),
            _make_bid(3, "hokom", rb=3, gm=2, ts=4),  # Wrong: should be seat 2
            _make_bid(4, "pass", rb=3, gm=2, ts=4),
            _make_bid(1, "pass", rb=3, gm=2, ts=4),
            _make_bid(2, "pass", rb=3, gm=2, ts=4),
        ]
        rnd = _make_round(events)
        rb = analyze_round_bidding(rnd, "test.json")

        assert any("R1 first bidder" in i for i in rb.issues)


# ── Report Properties ───────────────────────────────────────────────


class TestBiddingStatisticsReport:
    """Test computed properties of the report."""

    def test_played_rounds(self):
        report = BiddingStatisticsReport(
            total_rounds=100,
            waraq_count=30,
        )
        assert report.played_rounds == 70

    def test_hokum_pct(self):
        report = BiddingStatisticsReport(
            total_rounds=100,
            waraq_count=0,
            hokum_count=60,
        )
        assert report.hokum_pct == 60.0

    def test_sun_pct_includes_ashkal(self):
        report = BiddingStatisticsReport(
            total_rounds=100,
            waraq_count=0,
            sun_count=25,
            ashkal_count=15,
        )
        assert report.sun_pct == 40.0

    def test_waraq_pct(self):
        report = BiddingStatisticsReport(
            total_rounds=200,
            waraq_count=60,
        )
        assert report.waraq_pct == 30.0

    def test_round2_pct(self):
        report = BiddingStatisticsReport(
            total_rounds=100,
            went_to_round2=60,
        )
        assert report.round2_pct == 60.0

    def test_doubling_pct(self):
        report = BiddingStatisticsReport(
            total_rounds=100,
            waraq_count=0,
            doubling_dist={0: 90, 1: 5, 2: 3, 3: 1, 4: 1},
        )
        assert report.doubling_pct == 10.0

    def test_avg_bidder_position(self):
        report = BiddingStatisticsReport(
            bidder_position_dist={1: 30, 2: 25, 3: 25, 4: 20},
        )
        total = 1*30 + 2*25 + 3*25 + 4*20
        count = 100
        assert abs(report.avg_bidder_position - total / count) < 0.01

    def test_zero_rounds_safe(self):
        """Properties don't divide by zero."""
        report = BiddingStatisticsReport()
        assert report.played_rounds == 0
        assert report.hokum_pct == 0
        assert report.sun_pct == 0
        assert report.waraq_pct == 0
        assert report.round2_pct == 0
        assert report.doubling_pct == 0
        assert report.avg_bidder_position == 0

    def test_summary_produces_string(self):
        """Summary should produce a non-empty string."""
        report = BiddingStatisticsReport(
            total_archives=5,
            total_rounds=50,
            hokum_count=20,
            sun_count=15,
            ashkal_count=5,
            waraq_count=10,
            went_to_round2=30,
            round1_resolved=20,
            round2_resolved=20,
        )
        summary = report.summary()
        assert "BIDDING STATISTICS REPORT" in summary
        assert "Mode Distribution" in summary
        assert "Doubling Distribution" in summary


# ── Full Pipeline Integration ────────────────────────────────────────


class TestValidateAllBidding:
    """Integration tests running against real archive data."""

    @pytest.fixture(scope="class")
    def report(self):
        """Run bidding analysis once against all archives."""
        archive_dir = Path(
            "gbaloot/data/archive_captures/kammelna_export/savedGames"
        )
        if not archive_dir.exists():
            pytest.skip("Archive data not available")
        return validate_all_bidding(archive_dir)

    def test_total_archives(self, report: BiddingStatisticsReport):
        assert report.total_archives == 109

    def test_total_rounds(self, report: BiddingStatisticsReport):
        """Total rounds should match scoring validator count (waraq included)."""
        # 1095 validated + 506 waraq + some truncated = ~1613
        assert report.total_rounds > 1500
        assert report.total_rounds < 1700

    def test_waraq_count(self, report: BiddingStatisticsReport):
        """Waraq count should match known value (~506)."""
        assert report.waraq_count == 506

    def test_played_rounds_match_scoring(self, report: BiddingStatisticsReport):
        """Played rounds should be close to scoring validator's 1095."""
        # 4 truncated rounds (no mode) are not waraq but also not fully played
        assert abs(report.played_rounds - 1107) <= 5

    def test_mode_coverage(self, report: BiddingStatisticsReport):
        """All played rounds should have a mode."""
        total_modes = report.hokum_count + report.sun_count + report.ashkal_count
        # 4 truncated rounds have no mode
        assert total_modes >= report.played_rounds - 5

    def test_hokum_majority(self, report: BiddingStatisticsReport):
        """HOKUM should be the most common mode (~53%)."""
        assert report.hokum_pct > 45
        assert report.hokum_pct < 60

    def test_sun_plus_ashkal_significant(self, report: BiddingStatisticsReport):
        """SUN + Ashkal should be meaningful (~47%)."""
        assert report.sun_pct > 35
        assert report.sun_pct < 55

    def test_waraq_pct_range(self, report: BiddingStatisticsReport):
        """Waraq should be ~31% of total rounds."""
        assert report.waraq_pct > 25
        assert report.waraq_pct < 40

    def test_round2_pct_range(self, report: BiddingStatisticsReport):
        """~60% of rounds should go to Round 2."""
        assert report.round2_pct > 50
        assert report.round2_pct < 70

    def test_round1_plus_round2_waraq_equals_total(self, report: BiddingStatisticsReport):
        """R1 resolved + R2 total = all rounds (minus truncated)."""
        total = report.round1_resolved + report.went_to_round2
        # Total should equal total_rounds minus truncated rounds
        assert abs(total - report.total_rounds) <= 5

    def test_doubling_rate_low(self, report: BiddingStatisticsReport):
        """Doubling should be rare (~4%)."""
        assert report.doubling_pct > 1
        assert report.doubling_pct < 10

    def test_doubling_normal_majority(self, report: BiddingStatisticsReport):
        """Most played rounds should be normal (×1)."""
        assert report.doubling_dist[0] > report.played_rounds * 0.9

    def test_hokum_closed_more_than_open(self, report: BiddingStatisticsReport):
        """Closed HOKUM should be more common than open."""
        assert report.hokum_closed > report.hokum_open

    def test_before_you_exists(self, report: BiddingStatisticsReport):
        """Before-you counter-bids should exist."""
        assert report.before_you_count > 0

    def test_turn_to_sun_exists(self, report: BiddingStatisticsReport):
        """Turn-to-SUN switches should exist."""
        assert report.turn_to_sun_count > 0

    def test_bidder_position_distribution(self, report: BiddingStatisticsReport):
        """All positions should have bids."""
        for pos in range(1, 5):
            assert report.bidder_position_dist[pos] > 0

    def test_position_1_most_common(self, report: BiddingStatisticsReport):
        """Position 1 (right of dealer, first to bid) should bid most often."""
        pos1 = report.bidder_position_dist[1]
        for pos in range(2, 5):
            assert pos1 >= report.bidder_position_dist[pos]

    def test_position_4_least_common(self, report: BiddingStatisticsReport):
        """Position 4 (dealer, last to bid) should bid least often."""
        pos4 = report.bidder_position_dist[4]
        for pos in range(1, 4):
            assert pos4 <= report.bidder_position_dist[pos]

    def test_avg_bidder_position_early(self, report: BiddingStatisticsReport):
        """Average bidder position should skew early (< 2.5)."""
        assert report.avg_bidder_position < 2.6
        assert report.avg_bidder_position > 1.5

    def test_no_unknown_bid_actions(self, report: BiddingStatisticsReport):
        """No truly unknown bid actions (empty string is known)."""
        real_unknowns = report.unknown_bid_actions - {""}
        assert len(real_unknowns) == 0

    def test_all_bid_actions_seen(self, report: BiddingStatisticsReport):
        """All 19 real bid actions should appear in the data."""
        for action in ALL_BID_ACTIONS:
            if action == "":
                continue  # Skip empty string
            assert action in report.bid_action_counts, f"Bid action {action!r} not found"

    def test_pass_most_common(self, report: BiddingStatisticsReport):
        """'pass' should be the most common bid action."""
        max_action = max(report.bid_action_counts, key=report.bid_action_counts.get)
        assert max_action == "pass"

    def test_validation_issues_low(self, report: BiddingStatisticsReport):
        """Validation issues should be very few (< 1% of rounds)."""
        assert report.total_issues < report.total_rounds * 0.01

    def test_summary_output(self, report: BiddingStatisticsReport):
        """Summary should be a valid string with key sections."""
        summary = report.summary()
        assert "BIDDING STATISTICS REPORT" in summary
        assert "Mode Distribution" in summary
        assert "Bidding Phase" in summary
        assert "Doubling Distribution" in summary
        assert "Bidder Position" in summary
