"""
Tests for trick extraction state machine (gbaloot.core.trick_extractor).

Covers: single trick, full 8-trick round, multi-round boundary detection,
incomplete tricks, internal helpers, and edge cases.
"""
import pytest

from gbaloot.core.trick_extractor import (
    extract_tricks,
    _get_game_state_payload,
    _is_trick_complete,
    _detect_round_boundary,
    ExtractedTrick,
    ExtractedRound,
    ExtractionResult,
)


# ── Helpers ─────────────────────────────────────────────────────────

def _make_game_state_event(
    payload: dict,
    timestamp: float = 1000.0,
    action: str = "game_state",
) -> dict:
    """Build an event dict with proper nesting for _get_game_state_payload."""
    return {
        "timestamp": timestamp,
        "direction": "RECV",
        "action": action,
        "fields": {
            "p": {
                "c": "game_state",
                "p": payload,
            }
        },
        "raw_size": 100,
        "decode_errors": [],
    }


def _make_trick_events(
    round_index: int,
    trick_number: int,
    cards: dict,
    winner_seat: int,
    lead_suit: int = 0,
    mode: str = "ashkal",
    trump_suit: int | None = None,
    scores: list | None = None,
    base_ts: float = 1000.0,
) -> list[dict]:
    """Generate the event sequence for a single complete trick.

    Returns 2 events: the complete 4-card state + the eating state.
    """
    if scores is None:
        scores = [0, 0, 0, 0]

    played_cards = [-1, -1, -1, -1]
    for seat, cidx in cards.items():
        played_cards[seat] = cidx

    # Event 1: All 4 cards on table (complete state)
    complete_state = {
        "played_cards": played_cards,
        "last_action": {"action": "a_card_played"},
        "pcsCount": [8 - trick_number] * 4,
        "current_suit": lead_suit,
        "gm": mode,
        "ts": trump_suit,
        "ss": scores,
        "dealer": 0,
        "mover": winner_seat + 1,  # 1-indexed
    }
    ev1 = _make_game_state_event(complete_state, timestamp=base_ts)

    # Event 2: Cards eating (trick cleared)
    eating_state = {
        "played_cards": [-1, -1, -1, -1],
        "last_action": {"action": "a_cards_eating", "ap": winner_seat + 1},
        "pcsCount": [8 - trick_number] * 4,
        "current_suit": lead_suit,
        "gm": mode,
        "ts": trump_suit,
        "ss": scores,
        "dealer": 0,
        "mover": winner_seat + 1,
    }
    ev2 = _make_game_state_event(eating_state, timestamp=base_ts + 100)

    return [ev1, ev2]


# ── _get_game_state_payload ──────────────────────────────────────────

class TestGetGameStatePayload:

    def test_valid_game_state(self):
        event = _make_game_state_event({"played_cards": [1, 2, 3, 4], "pcsCount": [8, 8, 8, 8]})
        payload = _get_game_state_payload(event)
        assert payload is not None
        assert "played_cards" in payload

    def test_non_game_state_action_with_marker(self):
        """card_or_play events with c=game_state marker should be accepted."""
        event = {
            "timestamp": 1000,
            "direction": "RECV",
            "action": "card_or_play",
            "fields": {"p": {"c": "game_state", "p": {"played_cards": [1, 2, 3, 4]}}},
            "raw_size": 0,
            "decode_errors": [],
        }
        payload = _get_game_state_payload(event)
        assert payload is not None

    def test_unrelated_action_returns_none(self):
        event = {
            "timestamp": 1000,
            "direction": "RECV",
            "action": "chat",
            "fields": {"p": {"c": "chat", "p": {"msg": "hello"}}},
            "raw_size": 0,
            "decode_errors": [],
        }
        assert _get_game_state_payload(event) is None

    def test_missing_inner_p_returns_none(self):
        event = {
            "timestamp": 1000,
            "direction": "RECV",
            "action": "game_state",
            "fields": {"p": {"c": "game_state"}},
            "raw_size": 0,
            "decode_errors": [],
        }
        assert _get_game_state_payload(event) is None

    def test_no_played_cards_or_pcscount_returns_none(self):
        event = _make_game_state_event({"gm": "ashkal"})
        # override to remove both expected fields
        event["fields"]["p"]["p"] = {"gm": "ashkal"}
        assert _get_game_state_payload(event) is None


# ── _is_trick_complete ───────────────────────────────────────────────

class TestIsTrickComplete:

    def test_all_filled(self):
        assert _is_trick_complete([5, 18, 31, 44]) is True

    def test_has_negative(self):
        assert _is_trick_complete([5, 18, -1, 44]) is False

    def test_all_negative(self):
        assert _is_trick_complete([-1, -1, -1, -1]) is False

    def test_wrong_length(self):
        assert _is_trick_complete([5, 18, 31]) is False
        assert _is_trick_complete([]) is False

    def test_zero_is_valid(self):
        assert _is_trick_complete([0, 0, 0, 0]) is True


# ── _detect_round_boundary ──────────────────────────────────────────

class TestDetectRoundBoundary:

    def test_pcs_count_reset(self):
        prev = {"pcsCount": [1, 1, 1, 1], "dealer": 0}
        curr = {"pcsCount": [8, 8, 8, 8], "dealer": 1}
        assert _detect_round_boundary(prev, curr) is True

    def test_no_boundary_mid_round(self):
        prev = {"pcsCount": [6, 6, 6, 6], "dealer": 0}
        curr = {"pcsCount": [5, 5, 5, 5], "dealer": 0}
        assert _detect_round_boundary(prev, curr) is False

    def test_dealer_change_with_full_hands(self):
        prev = {"pcsCount": [2, 2, 2, 2], "dealer": 0}
        curr = {"pcsCount": [8, 8, 8, 8], "dealer": 1}
        assert _detect_round_boundary(prev, curr) is True

    def test_dealer_change_without_full_hands(self):
        prev = {"pcsCount": [3, 3, 3, 3], "dealer": 0}
        curr = {"pcsCount": [3, 3, 3, 3], "dealer": 1}
        assert _detect_round_boundary(prev, curr) is False


# ── extract_tricks — Single trick ────────────────────────────────────

class TestExtractSingleTrick:

    def test_single_trick_extracted(self):
        """A basic single trick should be extracted correctly."""
        events = _make_trick_events(
            round_index=0,
            trick_number=1,
            cards={0: 5, 1: 18, 2: 31, 3: 44},
            winner_seat=2,
            lead_suit=0,
            mode="ashkal",
        )
        result = extract_tricks(events, "test_session")
        assert result.total_tricks == 1
        assert len(result.rounds) == 1
        assert result.rounds[0].tricks[0].winner_seat == 2
        assert result.rounds[0].tricks[0].cards_by_seat == {0: 5, 1: 18, 2: 31, 3: 44}

    def test_trick_winner_from_mover(self):
        """Winner seat comes from mover field (1-indexed → 0-indexed)."""
        events = _make_trick_events(
            round_index=0, trick_number=1,
            cards={0: 5, 1: 18, 2: 31, 3: 44},
            winner_seat=3,  # mover=4 → seat 3
        )
        result = extract_tricks(events)
        assert result.rounds[0].tricks[0].winner_seat == 3


# ── extract_tricks — Full round ──────────────────────────────────────

class TestExtractFullRound:

    def test_eight_trick_round(self):
        """A complete 8-trick round should all be in the same ExtractedRound."""
        events = []
        for t in range(1, 9):
            trick_events = _make_trick_events(
                round_index=0,
                trick_number=t,
                cards={0: 5, 1: 18, 2: 31, 3: 44},
                winner_seat=t % 4,
                base_ts=1000.0 + t * 1000,
            )
            events.extend(trick_events)

        result = extract_tricks(events, "full_round")
        assert result.total_tricks == 8
        assert len(result.rounds) == 1
        assert len(result.rounds[0].tricks) == 8

    def test_trick_numbers_increment(self):
        events = []
        for t in range(1, 4):
            events.extend(_make_trick_events(
                round_index=0, trick_number=t,
                cards={0: 5, 1: 18, 2: 31, 3: 44},
                winner_seat=0,
                base_ts=t * 1000.0,
            ))
        result = extract_tricks(events)
        assert result.rounds[0].tricks[0].trick_number == 1
        assert result.rounds[0].tricks[1].trick_number == 2
        assert result.rounds[0].tricks[2].trick_number == 3


# ── extract_tricks — Multi-round ─────────────────────────────────────

class TestExtractMultiRound:

    def test_two_rounds_via_pcs_reset(self):
        """pcsCount reset signals new round."""
        events = []
        # Round 1: 2 tricks with low pcsCount
        for t in range(1, 3):
            events.extend(_make_trick_events(
                round_index=0, trick_number=t,
                cards={0: 5, 1: 18, 2: 31, 3: 44},
                winner_seat=0, base_ts=t * 1000.0,
            ))
        # Round boundary: pcsCount jumps back to 8
        boundary_state = {
            "played_cards": [-1, -1, -1, -1],
            "last_action": {"action": "round_init"},
            "pcsCount": [8, 8, 8, 8],
            "current_suit": -1,
            "gm": "ashkal",
            "ts": None,
            "ss": [10, 5, 10, 5],
            "dealer": 1,
        }
        events.append(_make_game_state_event(boundary_state, timestamp=10000))

        # Round 2: 1 trick
        events.extend(_make_trick_events(
            round_index=1, trick_number=1,
            cards={0: 6, 1: 19, 2: 32, 3: 45},
            winner_seat=1, base_ts=11000.0,
        ))

        result = extract_tricks(events, "multi_round")
        assert len(result.rounds) == 2
        assert result.rounds[0].round_index == 0
        assert result.rounds[1].round_index == 1


# ── extract_tricks — Edge cases ──────────────────────────────────────

class TestExtractEdgeCases:

    def test_empty_events(self):
        result = extract_tricks([], "empty")
        assert result.total_tricks == 0
        assert result.rounds == []

    def test_no_game_state_events(self):
        events = [
            {"timestamp": 1000, "direction": "RECV", "action": "chat",
             "fields": {"msg": "hello"}, "raw_size": 10, "decode_errors": []},
        ]
        result = extract_tricks(events, "no_game_state")
        assert result.total_tricks == 0

    def test_incomplete_trick_warns(self):
        """If played_cards has fewer than 4 valid entries, a warning is emitted."""
        # Build a state with only 3 cards filled + eating
        complete_state = {
            "played_cards": [5, 18, 31, -1],  # seat 3 missing
            "last_action": {"action": "a_card_played"},
            "pcsCount": [7, 7, 7, 7],
            "current_suit": 0, "gm": "ashkal", "ts": None,
            "ss": [0, 0, 0, 0], "dealer": 0, "mover": 1,
        }
        eating_state = {
            "played_cards": [-1, -1, -1, -1],
            "last_action": {"action": "a_cards_eating", "ap": 1},
            "pcsCount": [7, 7, 7, 7],
            "current_suit": 0, "gm": "ashkal", "ts": None,
            "ss": [0, 0, 0, 0], "dealer": 0, "mover": 1,
        }
        events = [
            _make_game_state_event(complete_state, timestamp=1000),
            _make_game_state_event(eating_state, timestamp=1100),
        ]
        result = extract_tricks(events)
        # The trick won't be extracted since only 3 cards
        assert result.total_tricks == 0

    def test_hokum_mode_carries_trump(self):
        events = _make_trick_events(
            round_index=0, trick_number=1,
            cards={0: 5, 1: 18, 2: 31, 3: 44},
            winner_seat=1, mode="hokom", trump_suit=2,
        )
        result = extract_tricks(events)
        assert result.rounds[0].game_mode_raw == "hokom"
        assert result.rounds[0].trump_suit_idx == 2

    def test_extraction_result_metadata(self):
        events = _make_trick_events(
            round_index=0, trick_number=1,
            cards={0: 5, 1: 18, 2: 31, 3: 44},
            winner_seat=0,
        )
        result = extract_tricks(events, "meta_test")
        assert result.session_path == "meta_test"
        assert result.total_events_scanned > 0
