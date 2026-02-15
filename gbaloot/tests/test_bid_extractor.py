"""
Tests for bid extractor and bid comparator (gbaloot.core.bid_extractor,
gbaloot.core.bid_comparator).

Covers: single pass bid, SUN bid, HOKUM bid with suit selection, multi-round
bidding, transition to playing, empty sessions, engine heuristic comparison.
"""
import pytest

from game_engine.models.card import Card
from gbaloot.core.bid_extractor import (
    extract_bids,
    ExtractedBid,
    ExtractedBidSequence,
    BidExtractionResult,
    BID_ACTION_MAP,
    _get_bidding_payload,
    _get_any_game_state_payload,
)
from gbaloot.core.bid_comparator import (
    compute_sun_score,
    compute_hokum_score,
    evaluate_hand_for_bidding,
    compare_bid_sequence,
    SUN_THRESHOLD,
    HOKUM_THRESHOLD,
)


# ── Helpers ─────────────────────────────────────────────────────────

def _make_bidding_event(
    bt: str,
    ap: int,
    gStg: int = 1,
    gm: str | None = None,
    ts: int | None = None,
    rb: int = 1,
    dealer: int = 1,
    pcs: int = 0,
    fc: int = -1,
    timestamp: float = 1000.0,
) -> dict:
    """Build a game_state event representing a bidding-phase state.

    @param bt: Bid type string (e.g. 'pass', 'sun', 'hokom').
    @param ap: Acting player (1-indexed).
    @param gStg: Game stage (1 = bidding).
    @param gm: Game mode string or None.
    @param ts: Trump suit index or None.
    @param rb: Bidding round number.
    @param dealer: Dealer seat (1-indexed).
    @param pcs: Card bitmask.
    @param fc: Face card index.
    @param timestamp: Event timestamp.
    """
    inner = {
        "gStg": gStg,
        "last_action": {"action": "a_bid", "bt": bt, "ap": ap},
        "b": [1],
        "bs": 3,
        "rb": rb,
        "dealer": dealer,
        "pcs": pcs,
        "fc": fc,
        "played_cards": [-1, -1, -1, -1],
        "pcsCount": [5, 5, 5, 5],
        "ss": [6, 6, 6, 6],
    }
    if gm is not None:
        inner["gm"] = gm
    if ts is not None:
        inner["ts"] = ts
    return {
        "timestamp": timestamp,
        "direction": "RECV",
        "action": "game_state",
        "fields": {"p": {"c": "game_state", "p": inner}},
        "raw_size": 100,
        "decode_errors": [],
    }


def _make_playing_event(
    gStg: int = 2,
    gm: str = "sun",
    ts: int | None = None,
    timestamp: float = 5000.0,
) -> dict:
    """Build a game_state event for the playing phase (gStg >= 2)."""
    inner = {
        "gStg": gStg,
        "last_action": {"action": "a_card_played"},
        "played_cards": [5, -1, -1, -1],
        "pcsCount": [8, 8, 8, 8],
        "gm": gm,
        "ss": [6, 6, 6, 6],
        "dealer": 1,
    }
    if ts is not None:
        inner["ts"] = ts
    return {
        "timestamp": timestamp,
        "direction": "RECV",
        "action": "game_state",
        "fields": {"p": {"c": "game_state", "p": inner}},
        "raw_size": 100,
        "decode_errors": [],
    }


# ── _get_bidding_payload / _get_any_game_state_payload ───────────────

class TestPayloadHelpers:

    def test_bidding_payload_returns_on_gStg1(self):
        event = _make_bidding_event("pass", 4)
        payload = _get_bidding_payload(event)
        assert payload is not None
        assert payload["gStg"] == 1

    def test_bidding_payload_returns_none_on_playing(self):
        event = _make_playing_event(gStg=2)
        assert _get_bidding_payload(event) is None

    def test_any_payload_returns_on_any_gStg(self):
        event = _make_playing_event(gStg=3)
        payload = _get_any_game_state_payload(event)
        assert payload is not None
        assert payload["gStg"] == 3

    def test_non_game_state_returns_none(self):
        event = {"timestamp": 1000, "direction": "RECV", "action": "chat",
                 "fields": {"msg": "hi"}, "raw_size": 0, "decode_errors": []}
        assert _get_any_game_state_payload(event) is None


# ── extract_bids ─────────────────────────────────────────────────────

class TestExtractBids:

    def test_empty_events(self):
        result = extract_bids([], "empty")
        assert result.total_bids == 0
        assert result.sequences == []

    def test_single_pass_bid(self):
        """A single pass bid should produce one sequence with one bid."""
        events = [
            _make_bidding_event("pass", ap=4, dealer=3, fc=9),
            _make_playing_event(gStg=2, gm="sun"),
        ]
        result = extract_bids(events, "single_pass")
        assert len(result.sequences) == 1
        seq = result.sequences[0]
        assert len(seq.bids) == 1
        assert seq.bids[0].action == "PASS"
        assert seq.bids[0].seat == 3  # ap=4 → seat 3
        assert seq.dealer_seat == 2  # dealer=3 → seat 2
        assert seq.final_mode == "SUN"

    def test_sun_bid_sequence(self):
        """Multiple passes then SUN bid."""
        events = [
            _make_bidding_event("pass", ap=4, dealer=3, timestamp=1000),
            _make_bidding_event("pass", ap=1, dealer=3, timestamp=2000),
            _make_bidding_event("sun", ap=2, dealer=3, gm="sun", timestamp=3000),
            _make_playing_event(gStg=2, gm="sun", timestamp=4000),
        ]
        result = extract_bids(events, "sun_bid")
        assert len(result.sequences) == 1
        seq = result.sequences[0]
        assert len(seq.bids) == 3
        assert seq.bids[2].action == "SUN"
        assert seq.caller_seat == 1  # ap=2 → seat 1
        assert seq.final_mode == "SUN"

    def test_hokum_bid_with_suit(self):
        """HOKUM bid followed by suit selection (clubs)."""
        events = [
            _make_bidding_event("hokom", ap=2, dealer=1, gm="hokom", timestamp=1000),
            _make_bidding_event("clubs", ap=2, dealer=1, gm="hokom", ts=2, timestamp=2000),
            _make_playing_event(gStg=2, gm="hokom", ts=2, timestamp=3000),
        ]
        result = extract_bids(events, "hokum_clubs")
        assert len(result.sequences) == 1
        seq = result.sequences[0]
        assert seq.final_mode == "HOKUM"
        assert seq.final_trump_idx == 2  # clubs
        assert seq.caller_seat == 1  # ap=2 → seat 1
        # Check the suit bid was captured
        assert any(b.action == "CLUBS" for b in seq.bids)

    def test_multi_round_bidding(self):
        """Two separate bidding sequences (two rounds)."""
        events = [
            # Round 1: pass then sun
            _make_bidding_event("pass", ap=4, dealer=3, timestamp=1000),
            _make_bidding_event("sun", ap=1, gm="sun", dealer=3, timestamp=2000),
            _make_playing_event(gStg=2, gm="sun", timestamp=3000),
            # Round 2: hokum
            _make_bidding_event("hokom", ap=2, dealer=4, gm="hokom", timestamp=10000),
            _make_playing_event(gStg=2, gm="hokom", ts=1, timestamp=11000),
        ]
        result = extract_bids(events, "two_rounds")
        assert len(result.sequences) == 2
        assert result.sequences[0].final_mode == "SUN"
        assert result.sequences[1].final_mode == "HOKUM"

    def test_dedup_same_bid(self):
        """Same bid appearing twice (same ap, bt, timestamp) is deduplicated."""
        events = [
            _make_bidding_event("pass", ap=4, dealer=3, timestamp=1000),
            _make_bidding_event("pass", ap=4, dealer=3, timestamp=1000),  # duplicate
            _make_playing_event(gStg=2, gm="sun", timestamp=2000),
        ]
        result = extract_bids(events)
        assert result.sequences[0].bids.__len__() == 1

    def test_face_card_captured(self):
        events = [
            _make_bidding_event("pass", ap=1, fc=22, dealer=4),
            _make_playing_event(),
        ]
        result = extract_bids(events)
        assert result.sequences[0].face_card_idx == 22


# ── Bid Comparator Heuristics ────────────────────────────────────────

class TestBidComparatorHeuristics:

    def test_sun_score_high_hand(self):
        """Hand with A+10+K in multiple suits scores high for SUN."""
        hand = [
            Card("♠", "A"), Card("♠", "10"),  # 11+10 = 21
            Card("♥", "A"),                    # 11 → total 32
        ]
        score = compute_sun_score(hand)
        assert score == 32
        assert score >= SUN_THRESHOLD

    def test_sun_score_low_hand(self):
        """Hand with all 7s and 8s scores 0 for SUN."""
        hand = [Card("♠", "7"), Card("♥", "8"), Card("♦", "7")]
        score = compute_sun_score(hand)
        assert score == 0
        assert score < SUN_THRESHOLD

    def test_hokum_score_with_jack(self):
        """Trump J gets 20 base + 10 bonus = 30 points."""
        hand = [Card("♥", "J")]  # J=20 + bonus=10 = 30
        score = compute_hokum_score(hand, "♥")
        assert score == 30

    def test_hokum_score_without_trump(self):
        """Non-trump cards use SUN point values."""
        hand = [Card("♠", "A"), Card("♠", "10")]  # 11 + 10 = 21
        score = compute_hokum_score(hand, "♥")  # ♥ is trump, ♠ is side
        assert score == 21

    def test_evaluate_hand_comprehensive(self):
        """Full hand evaluation returns all expected fields."""
        hand = [
            Card("♠", "A"), Card("♠", "10"), Card("♠", "K"),  # SUN: 25
            Card("♥", "J"), Card("♥", "9"),  # HOKUM ♥: J=20+bonus10 + 9=14 = 44 + sides
        ]
        result = evaluate_hand_for_bidding(hand)
        assert "sun_score" in result
        assert "hokum_scores" in result
        assert "would_bid_sun" in result
        assert "would_bid_hokum" in result
        assert "♠" in result["hokum_scores"]
        assert "♥" in result["hokum_scores"]


class TestBidComparatorComparison:

    def test_compare_with_hand_bitmask(self):
        """compare_bid_sequence returns result when hand data available."""
        seq = ExtractedBidSequence(
            round_index=0,
            final_mode="SUN",
            caller_seat=1,
        )
        # ♠A (idx 12) + ♠10 (idx 8) + ♠K (idx 11) = bitmask
        bitmask = (1 << 12) | (1 << 8) | (1 << 11)
        comp = compare_bid_sequence(seq, bitmask)
        assert comp is not None
        assert comp.round_index == 0
        assert comp.source_mode == "SUN"
        assert isinstance(comp.engine_sun_score, float)

    def test_compare_with_no_hand(self):
        """compare_bid_sequence returns None when no hand data."""
        seq = ExtractedBidSequence(round_index=0, final_mode="SUN")
        assert compare_bid_sequence(seq, None) is None
        assert compare_bid_sequence(seq, 0) is None

    def test_mode_agreement_sun(self):
        """Engine agrees on SUN when hand has high sun_score."""
        seq = ExtractedBidSequence(round_index=0, final_mode="SUN", caller_seat=0)
        # ♠A(12) + ♥A(25) + ♦A(51) = 11+11+11 = 33 SUN score → would bid SUN
        bitmask = (1 << 12) | (1 << 25) | (1 << 51)
        comp = compare_bid_sequence(seq, bitmask)
        assert comp is not None
        assert comp.engine_would_bid_sun is True
        assert comp.mode_agrees is True
