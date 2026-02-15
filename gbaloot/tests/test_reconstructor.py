"""
Tests for GameReconstructor — rewritten for real SFS2X protocol.

All test payloads mirror the actual ``fields.p.p`` structure observed
in captured game sessions.
"""
import pytest
from gbaloot.core.reconstructor import (
    GameReconstructor,
    reconstruct_timeline,
    _seat_position,
    GSTG_TO_PHASE,
)
from gbaloot.core.models import GameEvent, BoardState, PlayerState


# ── Helpers ───────────────────────────────────────────────────────────

def _gs_event(inner: dict, action: str = "game_state", ts: float = 1000) -> GameEvent:
    """Build a GameEvent wrapping an inner game-state dict in fields.p.p."""
    return GameEvent(
        timestamp=ts,
        direction="RECV",
        action=action,
        fields={"p": {"p": inner, "c": "game_state"}, "a": 13, "c": 0},
    )


def _non_gs_event(action: str = "ws_connect", ts: float = 500) -> GameEvent:
    """Build a GameEvent that has no game-state payload."""
    return GameEvent(
        timestamp=ts,
        direction="RECV",
        action=action,
        fields={"info": "connected"},
    )


# ── Phase / gStg mapping ─────────────────────────────────────────────

class TestPhaseMapping:
    def test_bidding_phase(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"gStg": 1, "pcsCount": [8, 8, 8, 8]}))
        assert rc.state.phase == "BIDDING"

    def test_playing_phase(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"gStg": 2, "played_cards": [-1, -1, -1, -1]}))
        assert rc.state.phase == "PLAYING"

    def test_trick_complete_phase(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"gStg": 3, "played_cards": [5, 18, 31, 44]}))
        assert rc.state.phase == "TRICK_COMPLETE"

    def test_unknown_gstg_falls_back(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"gStg": 99, "pcsCount": [8, 8, 8, 8]}))
        assert rc.state.phase == "WAITING"


# ── Game mode mapping ─────────────────────────────────────────────────

class TestGameMode:
    def test_ashkal_maps_to_sun(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"gm": "ashkal", "pcsCount": [8, 8, 8, 8]}))
        assert rc.state.game_mode == "SUN"

    def test_hokom_maps_to_hokum(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"gm": "hokom", "pcsCount": [8, 8, 8, 8]}))
        assert rc.state.game_mode == "HOKUM"

    def test_sun_maps_to_sun(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"gm": "sun", "pcsCount": [8, 8, 8, 8]}))
        assert rc.state.game_mode == "SUN"


# ── Dealer and mover (1-indexed → 0-indexed) ─────────────────────────

class TestSeatMapping:
    def test_dealer_1indexed_to_0indexed(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"dealer": 3, "pcsCount": [8, 8, 8, 8]}))
        assert rc.state.dealer_seat == 2

    def test_dealer_marks_player(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"dealer": 1, "pcsCount": [8, 8, 8, 8]}))
        assert rc.state.players[0].is_dealer is True
        assert rc.state.players[1].is_dealer is False

    def test_mover_1indexed_to_0indexed(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"mover": 4, "played_cards": [-1, -1, -1, -1]}))
        assert rc.state.current_player_seat == 3


# ── Trump suit ────────────────────────────────────────────────────────

class TestTrumpSuit:
    def test_trump_spades(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"ts": 0, "played_cards": [-1, -1, -1, -1]}))
        assert rc.state.trump_suit == "♠"

    def test_trump_hearts(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"ts": 1, "played_cards": [-1, -1, -1, -1]}))
        assert rc.state.trump_suit == "♥"

    def test_trump_clubs(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"ts": 2, "played_cards": [-1, -1, -1, -1]}))
        assert rc.state.trump_suit == "♣"

    def test_trump_diamonds(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"ts": 3, "played_cards": [-1, -1, -1, -1]}))
        assert rc.state.trump_suit == "♦"


# ── Played cards → center cards ──────────────────────────────────────

class TestCenterCards:
    def test_full_trick_4_cards(self):
        # card 37 = ♣K, 6 = ♠8 (wait — let me compute properly)
        # suit_idx * 13 + rank_idx: 37 = 2*13+11 = ♣K, 6 = 0*13+6 = ♠8
        rc = GameReconstructor()
        rc.apply_event(_gs_event({
            "played_cards": [37, 6, 31, 19],
            "pcsCount": [5, 5, 5, 5],
        }))
        assert len(rc.state.center_cards) == 4
        # Each is (seat, card_string)
        seats = [seat for seat, card in rc.state.center_cards]
        assert seats == [0, 1, 2, 3]

    def test_partial_trick(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({
            "played_cards": [5, -1, -1, -1],
            "pcsCount": [7, 8, 8, 8],
        }))
        assert len(rc.state.center_cards) == 1
        seat, card = rc.state.center_cards[0]
        assert seat == 0
        # card 5 = 0*13+5 = ♠7
        assert card == "7♠"

    def test_empty_trick(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({
            "played_cards": [-1, -1, -1, -1],
            "pcsCount": [8, 8, 8, 8],
        }))
        assert len(rc.state.center_cards) == 0

    def test_card_index_mapping_spade_7(self):
        """card index 5 = suit 0 (♠), rank 5 (7) → 7♠"""
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"played_cards": [5, -1, -1, -1], "pcsCount": [7, 8, 8, 8]}))
        _, card = rc.state.center_cards[0]
        assert card == "7♠"

    def test_card_index_mapping_heart_ace(self):
        """card index 25 = suit 1 (♥), rank 12 (A) → A♥"""
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"played_cards": [-1, 25, -1, -1], "pcsCount": [8, 7, 8, 8]}))
        seat, card = rc.state.center_cards[0]
        assert seat == 1
        assert card == "A♥"


# ── Hand bitmask (pcs) ────────────────────────────────────────────────

class TestHandBitmask:
    def test_pcs_decodes_to_hand(self):
        # Build a bitmask with just ♠7 (index 5) and ♠A (index 12)
        pcs = (1 << 5) | (1 << 12)
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"pcs": pcs, "pcsCount": [2, 0, 0, 0]}))
        hand = rc.state.players[0].hand
        assert len(hand) == 2
        assert "7♠" in hand
        assert "A♠" in hand

    def test_pcs_only_assigned_to_player_0(self):
        pcs = (1 << 5)  # Just ♠7
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"pcs": pcs, "pcsCount": [1, 0, 0, 0]}))
        assert len(rc.state.players[0].hand) == 1
        assert len(rc.state.players[1].hand) == 0


# ── Scores ────────────────────────────────────────────────────────────

class TestScores:
    def test_scores_stored_as_list(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"ss": [1, 6, 3, 6], "pcsCount": [5, 5, 5, 5]}))
        assert rc.state.scores == [1, 6, 3, 6]


# ── Trick and round numbers ──────────────────────────────────────────

class TestTrickRoundNumbers:
    def test_trick_number(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"mn": 5, "played_cards": [-1, -1, -1, -1]}))
        assert rc.state.trick_number == 5

    def test_round_number(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"rb": 3, "played_cards": [-1, -1, -1, -1]}))
        assert rc.state.round_number == 3


# ── Lead suit ─────────────────────────────────────────────────────────

class TestLeadSuit:
    def test_current_suit_mapped(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"current_suit": 2, "played_cards": [31, -1, -1, -1]}))
        assert rc.state.lead_suit == "♣"


# ── Last action + bidding history ─────────────────────────────────────

class TestLastAction:
    def test_bid_action_recorded(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({
            "last_action": {"action": "a_bid", "ap": 2, "bt": "hokom2"},
            "pcsCount": [8, 8, 8, 8],
        }))
        assert "bid" in rc.state.last_action_desc.lower()
        assert len(rc.state.bidding_history) == 1
        assert rc.state.bidding_history[0]["seat"] == 1  # 2-1=1
        assert rc.state.bidding_history[0]["bid"] == "hokom2"

    def test_card_played_action_desc(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({
            "last_action": {"action": "a_card_played", "ap": 3},
            "played_cards": [5, 18, -1, -1],
        }))
        assert "played" in rc.state.last_action_desc.lower()

    def test_cards_eating_action_desc(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({
            "last_action": {"action": "a_cards_eating"},
            "played_cards": [5, 18, 31, 44],
        }))
        assert "collected" in rc.state.last_action_desc.lower()


# ── Non-game events ──────────────────────────────────────────────────

class TestNonGameEvents:
    def test_non_game_event_increments_index(self):
        rc = GameReconstructor()
        rc.apply_event(_non_gs_event())
        assert rc.state.event_index == 1
        assert rc.state.phase == "WAITING"  # Unchanged

    def test_non_game_event_records_action(self):
        rc = GameReconstructor()
        rc.apply_event(_non_gs_event("ws_connect"))
        assert rc.state.last_action_desc == "ws_connect"


# ── Timeline reconstruction ──────────────────────────────────────────

class TestTimeline:
    def test_timeline_length_matches_events(self):
        events = [
            _non_gs_event("ws_connect", 100),
            _gs_event({"gStg": 1, "gm": "ashkal", "pcsCount": [8, 8, 8, 8]}, ts=200),
            _gs_event({"gStg": 2, "played_cards": [-1, -1, -1, -1]}, ts=300),
        ]
        timeline = reconstruct_timeline(events)
        assert len(timeline) == 3

    def test_timeline_states_independent(self):
        """Each snapshot is a deep copy — mutating one doesn't affect others."""
        events = [
            _gs_event({"gStg": 1, "pcsCount": [8, 8, 8, 8]}, ts=100),
            _gs_event({"gStg": 2, "played_cards": [5, -1, -1, -1]}, ts=200),
        ]
        timeline = reconstruct_timeline(events)
        timeline[0].phase = "MODIFIED"
        assert timeline[1].phase == "PLAYING"

    def test_timeline_progressive_state(self):
        """State accumulates across events."""
        events = [
            _gs_event({"gm": "hokom", "gStg": 1, "pcsCount": [8, 8, 8, 8]}, ts=100),
            _gs_event({"dealer": 2, "pcsCount": [8, 8, 8, 8]}, ts=200),
            _gs_event({"ts": 1, "gStg": 2, "played_cards": [-1, -1, -1, -1]}, ts=300),
        ]
        timeline = reconstruct_timeline(events)
        last = timeline[-1]
        assert last.game_mode == "HOKUM"
        assert last.dealer_seat == 1  # 2-1
        assert last.trump_suit == "♥"
        assert last.phase == "PLAYING"


# ── Seat position helper ─────────────────────────────────────────────

class TestSeatPosition:
    def test_seat_positions(self):
        assert _seat_position(0) == "BOTTOM"
        assert _seat_position(1) == "RIGHT"
        assert _seat_position(2) == "TOP"
        assert _seat_position(3) == "LEFT"

    def test_invalid_seat_defaults_bottom(self):
        assert _seat_position(5) == "BOTTOM"


# ── Reset ─────────────────────────────────────────────────────────────

class TestReset:
    def test_reset_clears_state(self):
        rc = GameReconstructor()
        rc.apply_event(_gs_event({"gStg": 2, "gm": "ashkal", "played_cards": [5, 18, 31, 44]}))
        assert rc.state.game_mode == "SUN"
        rc.reset()
        assert rc.state.game_mode == ""
        assert rc.state.phase == "WAITING"
        assert len(rc.state.center_cards) == 0
        assert len(rc.state.players) == 4


# ── BoardState compatibility properties ──────────────────────────────

class TestBoardStateCompat:
    def test_current_player_id_alias(self):
        bs = BoardState(current_player_seat=2)
        assert bs.current_player_id == 2

    def test_dealer_id_alias(self):
        bs = BoardState(dealer_seat=3)
        assert bs.dealer_id == 3

    def test_last_action_alias(self):
        bs = BoardState(last_action_desc="test")
        assert bs.last_action == "test"

    def test_contract_alias(self):
        bs = BoardState(game_mode="HOKUM")
        assert bs.contract == "HOKUM"

    def test_contract_none_when_empty(self):
        bs = BoardState(game_mode="")
        assert bs.contract is None

    def test_to_dict_serializes_center_cards(self):
        bs = BoardState(center_cards=[(0, "A♠"), (1, "K♥")])
        d = bs.to_dict()
        assert d["center_cards"] == [[0, "A♠"], [1, "K♥"]]


# ── PlayerState compatibility ─────────────────────────────────────────

class TestPlayerStateCompat:
    def test_id_alias(self):
        ps = PlayerState(seat=2)
        assert ps.id == 2
