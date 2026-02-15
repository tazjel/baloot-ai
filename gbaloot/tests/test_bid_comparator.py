"""
Tests for bid_comparator — engine bidding heuristic comparison.
"""
import pytest
from game_engine.models.card import Card
from gbaloot.core.bid_comparator import (
    compute_sun_score,
    compute_hokum_score,
    evaluate_hand_for_bidding,
    compare_bid_sequence,
    compare_session_bids,
    BidComparison,
    SUN_THRESHOLD,
    HOKUM_THRESHOLD,
)
from gbaloot.core.bid_extractor import ExtractedBidSequence


# ── SUN Scoring ───────────────────────────────────────────────────────

class TestComputeSunScore:
    def test_empty_hand(self):
        assert compute_sun_score([]) == 0

    def test_aces_only(self):
        # 4 Aces = 4 * 11 = 44
        hand = [Card("♠", "A"), Card("♥", "A"), Card("♣", "A"), Card("♦", "A")]
        assert compute_sun_score(hand) == 44

    def test_tens_and_kings(self):
        # 10=10, K=4 => 14
        hand = [Card("♠", "10"), Card("♠", "K")]
        assert compute_sun_score(hand) == 14

    def test_low_cards_score_zero(self):
        hand = [Card("♠", "7"), Card("♠", "8"), Card("♠", "9")]
        assert compute_sun_score(hand) == 0

    def test_above_threshold(self):
        # A(11) + 10(10) + K(4) + Q(3) = 28 > 26
        hand = [Card("♠", "A"), Card("♠", "10"), Card("♠", "K"), Card("♠", "Q")]
        assert compute_sun_score(hand) >= SUN_THRESHOLD

    def test_below_threshold(self):
        # K(4) + Q(3) + J(2) = 9 < 26
        hand = [Card("♠", "K"), Card("♠", "Q"), Card("♠", "J")]
        assert compute_sun_score(hand) < SUN_THRESHOLD


# ── HOKUM Scoring ─────────────────────────────────────────────────────

class TestComputeHokumScore:
    def test_jack_of_trump_bonus(self):
        # J of trump = 20 + 10 (bonus) = 30
        hand = [Card("♠", "J")]
        score = compute_hokum_score(hand, "♠")
        assert score == 30

    def test_nine_of_trump(self):
        hand = [Card("♠", "9")]
        score = compute_hokum_score(hand, "♠")
        assert score == 14

    def test_side_suit_no_bonus(self):
        hand = [Card("♥", "J")]  # J as side suit = 2
        score = compute_hokum_score(hand, "♠")
        assert score == 2

    def test_strong_hokum_hand(self):
        # J(20+10) + 9(14) + A(11) = 55 > 45
        hand = [Card("♠", "J"), Card("♠", "9"), Card("♠", "A")]
        score = compute_hokum_score(hand, "♠")
        assert score >= HOKUM_THRESHOLD

    def test_weak_hokum_hand(self):
        hand = [Card("♠", "7"), Card("♠", "8"), Card("♥", "7")]
        score = compute_hokum_score(hand, "♠")
        assert score < HOKUM_THRESHOLD


# ── evaluate_hand_for_bidding ─────────────────────────────────────────

class TestEvaluateHand:
    def test_structure(self):
        hand = [Card("♠", "A"), Card("♥", "K")]
        result = evaluate_hand_for_bidding(hand)
        assert "sun_score" in result
        assert "would_bid_sun" in result
        assert "hokum_scores" in result
        assert "best_hokum_suit" in result
        assert "would_bid_hokum" in result

    def test_strong_sun_hand(self):
        hand = [Card("♠", "A"), Card("♥", "A"), Card("♣", "10"), Card("♦", "K")]
        # 11 + 11 + 10 + 4 = 36 > 26
        result = evaluate_hand_for_bidding(hand)
        assert result["would_bid_sun"] is True

    def test_weak_hand_no_bid(self):
        hand = [Card("♠", "7"), Card("♥", "8"), Card("♣", "9")]
        result = evaluate_hand_for_bidding(hand)
        assert result["would_bid_sun"] is False
        assert result["would_bid_hokum"] is False
        assert result["best_hokum_suit"] is None


# ── compare_bid_sequence ──────────────────────────────────────────────

class TestCompareBidSequence:
    def test_none_without_bitmask(self):
        seq = ExtractedBidSequence(round_index=0, final_mode="SUN")
        assert compare_bid_sequence(seq, None) is None

    def test_none_with_zero_bitmask(self):
        seq = ExtractedBidSequence(round_index=0, final_mode="SUN")
        assert compare_bid_sequence(seq, 0) is None

    def test_agreement_on_sun(self):
        # Build bitmask for A♠(12) + A♥(25) + 10♣(34) + K♦(50) = strong SUN
        pcs = (1 << 12) | (1 << 25) | (1 << 34) | (1 << 50)
        seq = ExtractedBidSequence(round_index=0, final_mode="SUN")
        result = compare_bid_sequence(seq, pcs)
        assert result is not None
        assert result.engine_sun_score >= SUN_THRESHOLD
        assert result.mode_agrees is True

    def test_disagreement_noted(self):
        # Weak hand: only 7♠(5) and 8♥(19) — SUN score ~ 0
        pcs = (1 << 5) | (1 << 19)
        seq = ExtractedBidSequence(round_index=0, final_mode="SUN")
        result = compare_bid_sequence(seq, pcs)
        assert result is not None
        assert result.mode_agrees is False
        assert result.notes != ""

    def test_all_pass_agreement(self):
        # Weak hand, source also passed
        pcs = (1 << 5)  # Just 7♠
        seq = ExtractedBidSequence(round_index=0, final_mode="")
        result = compare_bid_sequence(seq, pcs)
        assert result is not None
        assert result.mode_agrees is True


# ── compare_session_bids ──────────────────────────────────────────────

class TestCompareSessionBids:
    def test_empty_sequences(self):
        assert compare_session_bids([], {}) == []

    def test_skips_missing_bitmasks(self):
        seqs = [ExtractedBidSequence(round_index=0, final_mode="SUN")]
        result = compare_session_bids(seqs, {})
        assert len(result) == 0

    def test_matches_by_round_index(self):
        pcs = (1 << 12) | (1 << 25)  # A♠ + A♥
        seqs = [
            ExtractedBidSequence(round_index=0, final_mode="SUN"),
            ExtractedBidSequence(round_index=1, final_mode="HOKUM"),
        ]
        result = compare_session_bids(seqs, {0: pcs, 1: pcs})
        assert len(result) == 2
        assert result[0].round_index == 0
        assert result[1].round_index == 1
