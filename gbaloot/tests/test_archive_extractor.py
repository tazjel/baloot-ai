"""Tests for the Kammelna mobile archive trick extractor."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from gbaloot.core.card_mapping import index_to_card, SUIT_SYMBOL_TO_IDX
from gbaloot.core.trick_extractor import ExtractedTrick, ExtractedRound, ExtractionResult
from gbaloot.tools.archive_parser import parse_archive
from gbaloot.tools.archive_trick_extractor import (
    extract_tricks_from_archive,
    extract_tricks_from_game,
    _compute_winner,
    _resolve_trump,
    _mode_to_raw,
    _find_dealer,
    BID_SUIT_MAP,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _write_archive(data, tmp_path, name="test.json"):
    fpath = tmp_path / name
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return fpath


def _make_archive(rounds):
    return {
        "v": 1, "n": "Test", "ps": [1, 2, 3, 4],
        "psN": ["A", "B", "C", "D"],
        "psRP": [0, 0, 0, 0], "psRN": [0, 0, 0, 0],
        "psCb": [0, 0, 0, 0], "psV": [0, 0, 0, 0],
        "psSb": [0, 0, 0, 0],
        "rL": len(rounds), "Id": 1, "t": 1, "chA": 1, "gT": 1,
        "pT": 0, "s1": 0, "s2": 0,
        "rs": rounds,
    }


def _sun_round_events():
    """A SUN round with 2 tricks — all same suit for easy verification."""
    return [
        {"e": 15, "bhr": [0, 0, 0, 0], "fhr": [0, 0, 0, 0]},
        {"p": 1, "e": 1, "fc": 44},
        {"p": 1, "e": 2, "b": "sun", "gm": 1, "ts": 4, "rb": 1},
        {"p": 2, "e": 2, "b": "pass", "gm": 1, "ts": 4, "rb": 1},
        # Trick 1: all spades — A♠(12) > K♠(11) > Q♠(10) > J♠(9) in SUN
        # SUN order: 7<8<9<J<Q<K<10<A -> A wins
        {"p": 1, "e": 4, "c": 12},   # A♠
        {"p": 2, "e": 4, "c": 11},   # K♠
        {"p": 3, "e": 4, "c": 10},   # Q♠
        {"p": 4, "e": 4, "c": 9},    # J♠
        {"p": 99, "e": 6},  # boundary (p ignored)
        # Trick 2: all hearts — 10♥(21) beats A♥(25)? No: SUN A > 10
        # idx: 18=7♥, 19=8♥, 20=9♥, 21=10♥, 22=J♥, 23=Q♥, 24=K♥, 25=A♥
        {"p": 1, "e": 4, "c": 25},   # A♥ (leader from T1)
        {"p": 2, "e": 4, "c": 21},   # 10♥
        {"p": 3, "e": 4, "c": 24},   # K♥
        {"p": 4, "e": 4, "c": 18},   # 7♥
        {"p": 99, "e": 6},  # boundary
        {"e": 12, "rs": {"p1": 40, "p2": 0, "m": 1, "w": 1, "s1": 40, "s2": 0,
                         "e1": 40, "e2": 0, "r1": [], "r2": [], "b": 1}},
    ]


def _hokum_round_events(fc_idx=44, bid_suit=None):
    """A HOKUM round. fc=44=7♦ -> trump=♦ unless bid_suit overrides."""
    events = [
        {"e": 15, "bhr": [0, 0, 0, 0], "fhr": [0, 0, 0, 0]},
        {"p": 1, "e": 1, "fc": fc_idx},
        {"p": 1, "e": 2, "b": "hokom", "gm": 2, "ts": 4, "rb": 1},
    ]
    if bid_suit:
        events.append({"p": 1, "e": 2, "b": bid_suit, "gm": 2, "ts": 2, "rb": 1})
    events.append({"p": 2, "e": 2, "b": "pass", "gm": 2, "ts": 4, "rb": 1})
    # Trick 1: P1 leads A♥(25), P2 plays 8♦(45) which is TRUMP
    # If trump=♦, the 8♦ (trump) beats A♥ (non-trump lead)
    events.extend([
        {"p": 1, "e": 4, "c": 25},   # A♥
        {"p": 2, "e": 4, "c": 45},   # 8♦ (trump!)
        {"p": 3, "e": 4, "c": 19},   # 8♥
        {"p": 4, "e": 4, "c": 24},   # K♥
        {"p": 0, "e": 6},  # boundary
        {"e": 12, "rs": {"p1": 0, "p2": 15, "m": 2, "w": 2, "s1": 0, "s2": 15,
                         "e1": 0, "e2": 15, "r1": [], "r2": [], "b": 1}},
    ])
    return events


def _kaboot_round_events():
    """A round with kaboot (fold) after 5 tricks."""
    events = [
        {"e": 15, "bhr": [0, 0, 0, 0], "fhr": [0, 0, 0, 0]},
        {"p": 1, "e": 1, "fc": 12},
        {"p": 1, "e": 2, "b": "sun", "gm": 1, "ts": 4, "rb": 1},
    ]
    # 5 tricks of all spades
    spade_cards = [
        [12, 11, 10, 9],   # A♠, K♠, Q♠, J♠
        [8, 7, 6, 5],      # 10♠, 9♠, 8♠, 7♠
        [25, 24, 23, 22],   # A♥, K♥, Q♥, J♥
        [21, 20, 19, 18],   # 10♥, 9♥, 8♥, 7♥
        [38, 37, 36, 35],   # A♣, K♣, Q♣, J♣
    ]
    for trick_cards in spade_cards:
        for i, cidx in enumerate(trick_cards):
            events.append({"p": i + 1, "e": 4, "c": cidx})
        events.append({"p": 1, "e": 6})  # boundary

    # Kaboot fold after 5 tricks
    events.append({"p": 2, "e": 5})
    events.append({"e": 12, "rs": {"p1": 44, "p2": 0, "m": 1, "w": 1,
                                    "s1": 44, "s2": 0, "kbt": 1,
                                    "e1": 44, "e2": 0, "r1": [], "r2": [], "b": 1}})
    return events


# ── Tests: Winner Computation ───────────────────────────────────────

class TestComputeWinner:
    """Test _compute_winner() engine logic."""

    def test_sun_ace_wins(self):
        # All spades, SUN: A♠ > K♠ > Q♠ > J♠
        plays = [(1, 12), (2, 11), (3, 10), (4, 9)]
        assert _compute_winner(plays, "SUN", None) == 0  # P1(seat 0) A♠

    def test_sun_ten_beats_king(self):
        # SUN order: 7<8<9<J<Q<K<10<A -> 10 beats K
        plays = [(1, 8), (2, 11), (3, 10), (4, 9)]  # 10♠, K♠, Q♠, J♠
        assert _compute_winner(plays, "SUN", None) == 0  # P1(seat 0) 10♠

    def test_sun_only_lead_suit_counts(self):
        # P1 leads A♠, P2 plays A♥ (wrong suit, doesn't count)
        plays = [(1, 12), (2, 25), (3, 5), (4, 6)]  # A♠, A♥, 7♠, 8♠
        assert _compute_winner(plays, "SUN", None) == 0  # A♠ wins

    def test_hokum_trump_beats_lead(self):
        # P1 leads A♥(25), P2 plays 7♦(44) trump
        plays = [(1, 25), (2, 44), (3, 19), (4, 24)]
        assert _compute_winner(plays, "HOKUM", "♦") == 1  # P2(seat 1) 7♦ trump

    def test_hokum_jack_beats_ace_in_trump(self):
        # All diamonds (trump), HOKUM order: J > 9 > A > 10 > K > Q > 8 > 7
        plays = [(1, 51), (2, 48), (3, 50), (4, 49)]  # A♦, J♦, K♦, Q♦
        assert _compute_winner(plays, "HOKUM", "♦") == 1  # P2(seat 1) J♦

    def test_hokum_nine_beats_ace_in_trump(self):
        # trump=♦, all diamonds
        plays = [(1, 51), (2, 46), (3, 50), (4, 49)]  # A♦, 9♦, K♦, Q♦
        assert _compute_winner(plays, "HOKUM", "♦") == 1  # P2(seat 1) 9♦

    def test_hokum_non_trump_uses_sun_order(self):
        # trump=♦, lead=♠ (non-trump)
        plays = [(1, 12), (2, 11), (3, 10), (4, 9)]  # A♠, K♠, Q♠, J♠
        assert _compute_winner(plays, "HOKUM", "♦") == 0  # A♠ wins (SUN order)


# ── Tests: Trump Resolution ────────────────────────────────────────

class TestResolveTrump:
    """Test _resolve_trump() for HOKUM rounds."""

    def test_sun_returns_none(self):
        events = [{"e": 1, "p": 1, "fc": 44}]
        assert _resolve_trump(events, "SUN") is None

    def test_hokum_from_fc(self):
        events = [
            {"e": 1, "p": 1, "fc": 44},  # 7♦
            {"e": 2, "p": 1, "b": "hokom", "gm": 2, "ts": 4},
        ]
        assert _resolve_trump(events, "HOKUM") == "♦"

    def test_hokum_fc_spade(self):
        events = [
            {"e": 1, "p": 1, "fc": 12},  # A♠
            {"e": 2, "p": 1, "b": "hokom", "gm": 2, "ts": 4},
        ]
        assert _resolve_trump(events, "HOKUM") == "♠"

    def test_explicit_suit_bid_overrides_fc(self):
        events = [
            {"e": 1, "p": 1, "fc": 12},   # A♠ -> fc suit = ♠
            {"e": 2, "p": 1, "b": "hokom", "gm": 2, "ts": 4},
            {"e": 2, "p": 1, "b": "clubs", "gm": 2, "ts": 2},  # explicit clubs
        ]
        assert _resolve_trump(events, "HOKUM") == "♣"

    def test_explicit_diamonds(self):
        events = [
            {"e": 1, "p": 1, "fc": 12},
            {"e": 2, "p": 1, "b": "diamonds", "gm": 2, "ts": 3},
        ]
        assert _resolve_trump(events, "HOKUM") == "♦"

    def test_explicit_hearts(self):
        events = [
            {"e": 1, "p": 1, "fc": 12},
            {"e": 2, "p": 1, "b": "hearts", "gm": 2, "ts": 1},
        ]
        assert _resolve_trump(events, "HOKUM") == "♥"

    def test_explicit_spades(self):
        events = [
            {"e": 1, "p": 1, "fc": 12},
            {"e": 2, "p": 1, "b": "spades", "gm": 2, "ts": 4},
        ]
        assert _resolve_trump(events, "HOKUM") == "♠"

    def test_bid_suit_map_has_all_four(self):
        assert len(BID_SUIT_MAP) == 4
        assert set(BID_SUIT_MAP.values()) == {"♠", "♥", "♣", "♦"}


# ── Tests: Mode Conversion ──────────────────────────────────────────

class TestModeToRaw:
    def test_sun(self):
        assert _mode_to_raw("SUN") == "sun"

    def test_hokum(self):
        assert _mode_to_raw("HOKUM") == "hokom"

    def test_none_defaults_sun(self):
        assert _mode_to_raw(None) == "sun"


# ── Tests: Dealer Finding ───────────────────────────────────────────

class TestFindDealer:
    def test_finds_dealer(self):
        events = [{"e": 1, "p": 3, "fc": 44}]
        # P3 acts first -> dealer = P2 (seat 1)
        assert _find_dealer(events) == 1

    def test_p1_acts_first(self):
        events = [{"e": 1, "p": 1, "fc": 12}]
        # P1 acts first -> dealer = P4 (seat 3)
        assert _find_dealer(events) == 3

    def test_no_round_start(self):
        events = [{"e": 4, "p": 1, "c": 12}]
        assert _find_dealer(events) == 0


# ── Tests: Full Extraction ──────────────────────────────────────────

class TestExtractTricks:
    """Integration tests for extract_tricks_from_archive."""

    def test_sun_round_extraction(self, tmp_path):
        data = _make_archive([{"r": _sun_round_events()}])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)

        assert result.total_tricks == 2
        assert len(result.rounds) == 1
        rnd = result.rounds[0]
        assert rnd.game_mode_raw == "sun"
        assert rnd.trump_suit_idx is None

        # Trick 1: A♠ wins in SUN
        t1 = rnd.tricks[0]
        assert t1.trick_number == 1
        assert t1.winner_seat == 0  # P1 (A♠)
        assert len(t1.cards_by_seat) == 4

        # Trick 2: A♥ wins in SUN (A > 10 > K)
        t2 = rnd.tricks[1]
        assert t2.winner_seat == 0  # P1 (A♥)

    def test_hokum_trump_wins(self, tmp_path):
        data = _make_archive([{"r": _hokum_round_events(fc_idx=44)}])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)

        assert result.total_tricks == 1
        rnd = result.rounds[0]
        assert rnd.game_mode_raw == "hokom"
        assert rnd.trump_suit_idx == 3  # ♦

        # P2 played 8♦ (trump) -> beats A♥ (lead)
        t1 = rnd.tricks[0]
        assert t1.winner_seat == 1  # P2

    def test_hokum_explicit_suit_bid(self, tmp_path):
        # fc=12=A♠ but bid "clubs" -> trump should be ♣
        data = _make_archive([{"r": _hokum_round_events(fc_idx=12, bid_suit="clubs")}])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)
        rnd = result.rounds[0]
        assert rnd.trump_suit_idx == 2  # ♣

    def test_kaboot_round(self, tmp_path):
        data = _make_archive([{"r": _kaboot_round_events()}])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)

        # Should extract 5 tricks (kaboot after 5)
        assert result.total_tricks == 5

    def test_multiple_rounds(self, tmp_path):
        data = _make_archive([
            {"r": _sun_round_events()},
            {"r": _hokum_round_events()},
        ])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)

        assert len(result.rounds) == 2
        assert result.total_tricks == 3  # 2 SUN + 1 HOKUM

    def test_e6_p_field_ignored(self, tmp_path):
        """Verify that the e=6 p field does NOT affect winner computation."""
        events = _sun_round_events()
        # Change e=6 p to something wrong — should NOT affect result
        for evt in events:
            if evt.get("e") == 6:
                evt["p"] = 99  # Garbage value
        data = _make_archive([{"r": events}])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)

        # Winners should still be correct
        assert result.total_tricks == 2
        assert result.rounds[0].tricks[0].winner_seat == 0  # P1 (A♠)
        assert result.rounds[0].tricks[1].winner_seat == 0  # P1 (A♥)

    def test_interleaved_declarations_skipped(self, tmp_path):
        """Declarations (e=3) between card plays should not break tricks."""
        events = [
            {"e": 15, "bhr": [0, 0, 0, 0], "fhr": [0, 0, 0, 0]},
            {"p": 1, "e": 1, "fc": 44},
            {"p": 1, "e": 2, "b": "sun", "gm": 1, "ts": 4, "rb": 1},
            {"p": 1, "e": 4, "c": 12},   # A♠
            {"p": 2, "e": 3, "prj": 1},   # Declaration!
            {"p": 2, "e": 4, "c": 11},   # K♠
            {"p": 3, "e": 4, "c": 10},   # Q♠
            {"p": 4, "e": 3, "prjC": 1024},  # Another declaration!
            {"p": 4, "e": 4, "c": 9},    # J♠
            {"p": 1, "e": 6},
            {"e": 12, "rs": {"p1": 20, "p2": 0, "m": 1, "w": 1,
                             "s1": 20, "s2": 0, "e1": 20, "e2": 0,
                             "r1": [], "r2": [], "b": 1}},
        ]
        data = _make_archive([{"r": events}])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)
        assert result.total_tricks == 1
        assert result.rounds[0].tricks[0].winner_seat == 0  # A♠ wins

    def test_chat_messages_skipped(self, tmp_path):
        """Chat messages (e=8) should not break extraction."""
        events = [
            {"e": 15, "bhr": [0, 0, 0, 0], "fhr": [0, 0, 0, 0]},
            {"p": 1, "e": 1, "fc": 44},
            {"p": 1, "e": 2, "b": "sun", "gm": 1, "ts": 4, "rb": 1},
            {"p": 1, "e": 4, "c": 12},
            {"p": 2, "e": 8, "uid": 100, "msg": "hello"},  # Chat!
            {"p": 2, "e": 4, "c": 11},
            {"p": 3, "e": 4, "c": 10},
            {"p": 4, "e": 4, "c": 9},
            {"p": 1, "e": 6},
            {"e": 12, "rs": {"p1": 20, "p2": 0, "m": 1, "w": 1,
                             "s1": 20, "s2": 0, "e1": 20, "e2": 0,
                             "r1": [], "r2": [], "b": 1}},
        ]
        data = _make_archive([{"r": events}])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)
        assert result.total_tricks == 1

    def test_warnings_on_leftover_cards(self, tmp_path):
        """Leftover cards after all events should produce a warning."""
        events = [
            {"e": 15, "bhr": [0, 0, 0, 0], "fhr": [0, 0, 0, 0]},
            {"p": 1, "e": 1, "fc": 44},
            {"p": 1, "e": 2, "b": "sun", "gm": 1, "ts": 4, "rb": 1},
            {"p": 1, "e": 4, "c": 12},
            {"p": 2, "e": 4, "c": 11},
            # Only 2 cards, no trick boundary -> leftover
            {"e": 12, "rs": {"p1": 0, "p2": 0, "m": 1, "w": 0,
                             "s1": 0, "s2": 0, "e1": 0, "e2": 0,
                             "r1": [], "r2": [], "b": 1}},
        ]
        data = _make_archive([{"r": events}])
        fpath = _write_archive(data, tmp_path)

        result = extract_tricks_from_archive(fpath)
        assert any("leftover" in w for w in result.extraction_warnings)


# ── Tests: Real Archive Data ────────────────────────────────────────

class TestRealArchiveData:
    """Test against actual archive files if available."""

    ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "data" / "archive_captures" / "kammelna_export" / "savedGames"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "data" / "archive_captures" / "kammelna_export" / "savedGames").exists(),
        reason="Archive data not available",
    )
    def test_all_archives_extract_without_errors(self):
        """Every archive should parse and extract without exceptions."""
        files = sorted(self.ARCHIVE_DIR.glob("*.json"))
        assert len(files) > 0

        for f in files:
            result = extract_tricks_from_archive(f)
            assert result.total_tricks > 0, f"No tricks in {f.name}"
            for rnd in result.rounds:
                for trick in rnd.tricks:
                    assert len(trick.cards_by_seat) == 4
                    assert 0 <= trick.winner_seat <= 3

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "data" / "archive_captures" / "kammelna_export" / "savedGames").exists(),
        reason="Archive data not available",
    )
    def test_leader_chain_consistency(self):
        """In every round, the leader of trick N+1 must be the engine
        winner of trick N.  This validates that our trick resolution
        logic matches the actual game flow."""
        from game_engine.models.constants import ORDER_SUN, ORDER_HOKUM

        files = sorted(self.ARCHIVE_DIR.glob("*.json"))
        total_rounds = 0
        consistent = 0

        for f in files:
            data = json.load(open(f, encoding="utf-8"))
            for ri, rnd_data in enumerate(data["rs"]):
                events = rnd_data["r"]

                # Determine mode
                mode = "SUN"
                for evt in events:
                    if evt.get("e") == 2 and evt.get("gm") is not None:
                        gm = evt["gm"]
                        mode = "SUN" if gm in (1, 3) else "HOKUM"

                # Resolve trump
                trump = _resolve_trump(events, mode)

                # Walk tricks and verify leader chain
                trick_plays = []
                prev_winner_p = None
                chain_ok = True
                has_tricks = False

                for evt in events:
                    e = evt.get("e")
                    if e == 4:
                        trick_plays.append(evt)
                    elif e == 6:
                        if len(trick_plays) < 4:
                            trick_plays.clear()
                            continue
                        has_tricks = True
                        cards = trick_plays[-4:]
                        leader_p = cards[0]["p"]

                        if prev_winner_p is not None and leader_p != prev_winner_p:
                            chain_ok = False

                        # Compute winner
                        plays = [(c["p"], c["c"]) for c in cards]
                        winner_seat = _compute_winner(plays, mode, trump)
                        prev_winner_p = winner_seat + 1  # back to 1-indexed

                if has_tricks:
                    total_rounds += 1
                    if chain_ok:
                        consistent += 1

        assert total_rounds > 0
        assert consistent == total_rounds, (
            f"Leader chain broken in {total_rounds - consistent}/{total_rounds} rounds"
        )
