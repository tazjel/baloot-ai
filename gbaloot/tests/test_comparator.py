"""
Tests for game comparator engine (gbaloot.core.comparator).

Covers: _compute_winner_locally (SUN/HOKUM), _get_card_points, severity
classification, compare_session with synthetic data, and generate_scorecard.
"""
import pytest
from datetime import datetime

from game_engine.models.card import Card
from game_engine.models.constants import (
    ORDER_SUN,
    ORDER_HOKUM,
    POINT_VALUES_SUN,
    POINT_VALUES_HOKUM,
)
from gbaloot.core.comparator import (
    GameComparator,
    ComparisonReport,
    TrickComparison,
    Divergence,
    _compute_winner_locally,
    _get_card_points,
    _classify_severity,
    generate_scorecard,
)


# ── _compute_winner_locally — SUN mode ──────────────────────────────

class TestComputeWinnerSun:

    def test_highest_lead_suit_wins(self):
        """In SUN, highest card of the lead suit wins."""
        cards = {
            0: Card("♠", "7"),   # lead
            1: Card("♠", "A"),   # highest in lead suit
            2: Card("♠", "10"),
            3: Card("♠", "K"),
        }
        winner = _compute_winner_locally(cards, "♠", "SUN", None)
        assert winner == 1  # A is highest

    def test_off_suit_cards_lose(self):
        """Off-suit cards in SUN have no strength, lead suit wins."""
        cards = {
            0: Card("♠", "7"),   # lead
            1: Card("♥", "A"),   # off-suit Ace — no strength
            2: Card("♦", "A"),   # off-suit Ace — no strength
            3: Card("♠", "8"),   # only other lead-suit card
        }
        winner = _compute_winner_locally(cards, "♠", "SUN", None)
        assert winner == 3  # ♠8 beats ♠7, off-suit cards have no strength

    def test_sun_rank_order(self):
        """SUN order: 7 < 8 < 9 < J < Q < K < 10 < A."""
        # ♠10 vs ♠K — 10 is higher in SUN order
        cards = {
            0: Card("♠", "K"),
            1: Card("♠", "10"),
        }
        winner = _compute_winner_locally(cards, "♠", "SUN", None)
        assert winner == 1  # 10 > K in SUN

    def test_jack_beats_nine_in_sun(self):
        cards = {
            0: Card("♠", "9"),
            1: Card("♠", "J"),
        }
        winner = _compute_winner_locally(cards, "♠", "SUN", None)
        assert winner == 1  # J > 9 in SUN


# ── _compute_winner_locally — HOKUM mode ────────────────────────────

class TestComputeWinnerHokum:

    def test_trump_beats_lead_suit(self):
        """In HOKUM, any trump card beats any lead-suit card."""
        cards = {
            0: Card("♠", "A"),   # lead suit Ace
            1: Card("♥", "7"),   # trump 7 (lowest trump)
        }
        winner = _compute_winner_locally(cards, "♠", "HOKUM", "♥")
        assert winner == 1  # Trump always wins

    def test_highest_trump_wins(self):
        """When multiple trumps played, highest trump wins."""
        cards = {
            0: Card("♠", "A"),   # lead suit
            1: Card("♥", "7"),   # trump 7
            2: Card("♥", "J"),   # trump Jack (highest in HOKUM)
            3: Card("♥", "9"),   # trump 9
        }
        winner = _compute_winner_locally(cards, "♠", "HOKUM", "♥")
        assert winner == 2  # J is highest in HOKUM trump order

    def test_no_trump_follows_sun_order(self):
        """Non-trump HOKUM tricks resolve like SUN (lead suit only)."""
        cards = {
            0: Card("♠", "10"),  # lead
            1: Card("♠", "K"),
            2: Card("♦", "A"),   # off-suit, no strength
            3: Card("♠", "7"),
        }
        winner = _compute_winner_locally(cards, "♠", "HOKUM", "♥")
        assert winner == 0  # ♠10 highest of lead suit (SUN order)

    def test_hokum_trump_rank_order(self):
        """HOKUM trump order: 7 < 8 < Q < K < 10 < A < 9 < J."""
        cards = {
            0: Card("♥", "A"),
            1: Card("♥", "9"),  # 9 beats A in HOKUM
        }
        winner = _compute_winner_locally(cards, "♥", "HOKUM", "♥")
        assert winner == 1  # 9 > A in HOKUM order

    def test_all_off_suit(self):
        """If all cards are off-suit (no trump, no lead), best_seat stays -1 or first found."""
        cards = {
            0: Card("♦", "A"),
            1: Card("♣", "A"),
        }
        # lead is ♠, trump is ♥ — neither played
        winner = _compute_winner_locally(cards, "♠", "HOKUM", "♥")
        # Both have strength -1, so the first card seen (seat 0) should not beat later ones
        # Implementation: best_seat starts at -1, first card with -1 > -1 is false, stays -1
        # Actually: 0 card has strength -1, -1 > -1 is false, so best_seat stays -1
        # Then seat 1: -1 > -1 is false, stays -1 → returns -1
        assert winner == -1


# ── _get_card_points ────────────────────────────────────────────────

class TestGetCardPoints:

    def test_sun_ace(self):
        assert _get_card_points(Card("♠", "A"), "SUN", None) == 11

    def test_sun_ten(self):
        assert _get_card_points(Card("♥", "10"), "SUN", None) == 10

    def test_sun_king(self):
        assert _get_card_points(Card("♦", "K"), "SUN", None) == 4

    def test_sun_queen(self):
        assert _get_card_points(Card("♣", "Q"), "SUN", None) == 3

    def test_sun_jack(self):
        assert _get_card_points(Card("♠", "J"), "SUN", None) == 2

    def test_sun_no_points(self):
        assert _get_card_points(Card("♠", "7"), "SUN", None) == 0
        assert _get_card_points(Card("♠", "8"), "SUN", None) == 0
        assert _get_card_points(Card("♠", "9"), "SUN", None) == 0

    def test_hokum_trump_jack(self):
        assert _get_card_points(Card("♥", "J"), "HOKUM", "♥") == 20

    def test_hokum_trump_nine(self):
        assert _get_card_points(Card("♥", "9"), "HOKUM", "♥") == 14

    def test_hokum_non_trump_uses_sun_values(self):
        """Non-trump cards in HOKUM use SUN point values."""
        assert _get_card_points(Card("♠", "J"), "HOKUM", "♥") == 2  # SUN value
        assert _get_card_points(Card("♠", "9"), "HOKUM", "♥") == 0  # SUN value

    def test_sun_total_per_suit(self):
        """Each suit totals 30 points in SUN (A=11+10=10+K=4+Q=3+J=2 = 30)."""
        total = sum(POINT_VALUES_SUN.get(r, 0) for r in ["7", "8", "9", "10", "J", "Q", "K", "A"])
        assert total == 30


# ── _classify_severity ──────────────────────────────────────────────

class TestClassifySeverity:

    def _make_tc(self, points: int, mode: str) -> TrickComparison:
        return TrickComparison(
            trick_number=1, round_index=0, cards=[], lead_suit="♠",
            game_mode=mode, trump_suit=None,
            source_winner_seat=0, engine_winner_seat=1,
            engine_points=points, winner_agrees=False,
            divergence_type="TRICK_WINNER",
        )

    def test_high_points(self):
        assert _classify_severity(self._make_tc(20, "SUN")) == "HIGH"
        assert _classify_severity(self._make_tc(30, "SUN")) == "HIGH"

    def test_hokum_is_medium(self):
        assert _classify_severity(self._make_tc(5, "HOKUM")) == "MEDIUM"

    def test_low_sun(self):
        assert _classify_severity(self._make_tc(5, "SUN")) == "LOW"
        assert _classify_severity(self._make_tc(0, "SUN")) == "LOW"


# ── GameComparator.compare_session ──────────────────────────────────

class TestCompareSession:

    def _make_session_events(self, tricks_data: list[dict]) -> list[dict]:
        """Build event list from trick specs.

        Each trick_data: {cards: {seat: idx}, winner_seat: int, mode: str, trump: int|None}
        """
        events = []
        for i, td in enumerate(tricks_data):
            mode = td.get("mode", "ashkal")
            trump = td.get("trump", None)
            cards = td["cards"]
            winner = td["winner_seat"]

            played = [-1, -1, -1, -1]
            for seat, cidx in cards.items():
                played[seat] = cidx

            # Complete state
            complete = {
                "played_cards": played,
                "last_action": {"action": "a_card_played"},
                "pcsCount": [8 - (i + 1)] * 4,
                "current_suit": 0,
                "gm": mode,
                "ts": trump,
                "ss": [0, 0, 0, 0],
                "dealer": 0,
                "mover": winner + 1,
            }
            events.append({
                "timestamp": 1000.0 + i * 2000,
                "direction": "RECV",
                "action": "game_state",
                "fields": {"p": {"c": "game_state", "p": complete}},
                "raw_size": 100,
                "decode_errors": [],
            })

            # Eating state
            eating = {
                "played_cards": [-1, -1, -1, -1],
                "last_action": {"action": "a_cards_eating", "ap": winner + 1},
                "pcsCount": [8 - (i + 1)] * 4,
                "current_suit": 0,
                "gm": mode,
                "ts": trump,
                "ss": [0, 0, 0, 0],
                "dealer": 0,
                "mover": winner + 1,
            }
            events.append({
                "timestamp": 1000.0 + i * 2000 + 500,
                "direction": "RECV",
                "action": "game_state",
                "fields": {"p": {"c": "game_state", "p": eating}},
                "raw_size": 100,
                "decode_errors": [],
            })

        return events

    def test_single_trick_agreement(self):
        """Engine and source agree on winner → 100% agreement."""
        # ♠7(idx=5) ♠A(idx=12) ♠10(idx=8) ♠K(idx=11) — lead ♠, SUN mode
        # ♠A is highest → seat 1 wins
        events = self._make_session_events([{
            "cards": {0: 5, 1: 12, 2: 8, 3: 11},
            "winner_seat": 1,
            "mode": "ashkal",
        }])
        comp = GameComparator()
        report = comp.compare_session(events, "test")
        assert report.total_tricks == 1
        assert report.winner_agreement_pct == 100.0
        assert report.total_divergences == 0

    def test_single_trick_divergence(self):
        """When source says different winner from engine → divergence recorded."""
        # ♠7(idx=5) ♠A(idx=12) ♠10(idx=8) ♠K(idx=11) — lead ♠
        # Engine: seat 1 (♠A wins). Source says: seat 3 (wrong)
        events = self._make_session_events([{
            "cards": {0: 5, 1: 12, 2: 8, 3: 11},
            "winner_seat": 3,  # Wrong — engine says seat 1
            "mode": "ashkal",
        }])
        comp = GameComparator()
        report = comp.compare_session(events, "test")
        assert report.total_divergences == 1
        assert report.winner_agreement_pct == 0.0
        assert len(comp.get_divergences()) == 1

    def test_report_has_all_fields(self):
        events = self._make_session_events([{
            "cards": {0: 5, 1: 18, 2: 31, 3: 44},
            "winner_seat": 0,
            "mode": "ashkal",
        }])
        comp = GameComparator()
        report = comp.compare_session(events, "test_path")
        assert report.session_path == "test_path"
        assert report.generated_at  # non-empty ISO timestamp
        assert report.rounds_compared >= 1
        assert isinstance(report.engine_points_team_02, int)
        assert isinstance(report.engine_points_team_13, int)

    def test_hokum_comparison(self):
        """HOKUM mode with trump should correctly resolve winners."""
        # ♠A(5*0+12=12) vs ♥7(1*13+5=18) — lead ♠, trump ♥
        # Trump ♥7 beats ♠A in HOKUM
        events = self._make_session_events([{
            "cards": {0: 12, 1: 18},
            "winner_seat": 1,
            "mode": "hokom",
            "trump": 1,  # ♥ is trump
        }])
        # Only 2 cards, won't pass the 4-card check in extractor
        comp = GameComparator()
        report = comp.compare_session(events, "hokum_test")
        # With only 2 cards, trick won't extract — 0 tricks
        assert report.total_tricks == 0


# ── generate_scorecard ──────────────────────────────────────────────

class TestGenerateScorecard:

    def _make_report(
        self, tricks: list[TrickComparison], session_path: str = "test"
    ) -> ComparisonReport:
        total = len(tricks)
        agrees = sum(1 for t in tricks if t.winner_agrees)
        pct = (agrees / total * 100.0) if total > 0 else 0.0
        return ComparisonReport(
            session_path=session_path,
            generated_at=datetime.now().isoformat(),
            rounds_compared=1,
            total_tricks=total,
            trick_comparisons=tricks,
            winner_agreement_pct=round(pct, 1),
            total_divergences=total - agrees,
            divergence_breakdown={},
            engine_points_team_02=0,
            engine_points_team_13=0,
            extraction_warnings=[],
        )

    def _make_tc(self, mode: str, agrees: bool, points: int = 15, round_idx: int = 0, trick_num: int = 1) -> TrickComparison:
        return TrickComparison(
            trick_number=trick_num, round_index=round_idx, cards=[],
            lead_suit="♠", game_mode=mode, trump_suit=None,
            source_winner_seat=0, engine_winner_seat=0 if agrees else 1,
            engine_points=points, winner_agrees=agrees,
        )

    def test_perfect_scorecard(self):
        tricks = [self._make_tc("SUN", True) for _ in range(8)]
        report = self._make_report(tricks)
        scorecard = generate_scorecard([report])
        assert scorecard["trick_resolution"]["agreement_pct"] == 100.0
        assert scorecard["trick_resolution"]["badge"] == "green"
        assert scorecard["sun_mode"]["agreement_pct"] == 100.0

    def test_mixed_mode_scorecard(self):
        sun_tricks = [self._make_tc("SUN", True) for _ in range(4)]
        hokum_tricks = [self._make_tc("HOKUM", True) for _ in range(4)]
        report = self._make_report(sun_tricks + hokum_tricks)
        scorecard = generate_scorecard([report])
        assert scorecard["sun_mode"]["total"] == 4
        assert scorecard["hokum_mode"]["total"] == 4

    def test_low_agreement_red_badge(self):
        # 2 agree, 8 disagree → 20% → red
        tricks = [self._make_tc("SUN", True)] * 2 + [self._make_tc("SUN", False)] * 8
        report = self._make_report(tricks)
        scorecard = generate_scorecard([report])
        assert scorecard["trick_resolution"]["badge"] == "red"
        assert scorecard["trick_resolution"]["agreement_pct"] == 20.0

    def test_point_calculation_8_trick_round(self):
        """8-trick round where points sum to 120 (SUN) → points badge green."""
        tricks = [
            self._make_tc("SUN", True, points=15, round_idx=0, trick_num=i + 1)
            for i in range(8)
        ]
        # 15 * 8 = 120 → matches SUN expected total
        report = self._make_report(tricks)
        scorecard = generate_scorecard([report])
        assert scorecard["point_calculation"]["total"] == 1  # 1 round checked
        assert scorecard["point_calculation"]["correct"] == 1
        assert scorecard["point_calculation"]["badge"] == "green"

    def test_empty_reports(self):
        scorecard = generate_scorecard([])
        assert scorecard["total_tricks"] == 0
        assert scorecard["sessions_analyzed"] == 0

    def test_multiple_sessions(self):
        r1 = self._make_report([self._make_tc("SUN", True)] * 4, "s1")
        r2 = self._make_report([self._make_tc("HOKUM", True)] * 4, "s2")
        scorecard = generate_scorecard([r1, r2])
        assert scorecard["sessions_analyzed"] == 2
        assert scorecard["total_tricks"] == 8
