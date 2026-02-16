"""Tests for StateBuilder — SFS2X event → BotAgent game_state translation."""
from __future__ import annotations

import pytest

from gbaloot.core.state_builder import StateBuilder, POSITIONS


# ── Helpers ──────────────────────────────────────────────────────────

def _make_event(action: str, inner_payload: dict, direction: str = "RECV") -> dict:
    """Build a GameEvent-shaped dict with the standard p.p nesting."""
    return {
        "timestamp": 1000,
        "direction": direction,
        "action": action,
        "fields": {"p": {"p": inner_payload}},
        "raw_size": 100,
    }


def _make_game_state_event(**kwargs) -> dict:
    """Build a game_state event with the given fields in the inner payload."""
    return _make_event("game_state", kwargs)


# ── StateBuilder Initialization ──────────────────────────────────────

class TestStateBuilderInit:
    def test_empty_state_has_required_keys(self):
        sb = StateBuilder(my_username="TestUser")
        gs = sb.game_state

        assert gs["roomId"] == "gbaloot_live"
        assert gs["phase"] is None
        assert gs["gameMode"] is None
        assert gs["trumpSuit"] is None
        assert len(gs["players"]) == 4
        assert gs["players"][0]["position"] == "Bottom"
        assert gs["players"][1]["position"] == "Right"
        assert gs["players"][2]["position"] == "Top"
        assert gs["players"][3]["position"] == "Left"
        assert gs["tableCards"] == []
        assert gs["currentRoundTricks"] == []
        assert gs["bidHistory"] == []
        assert gs["strictMode"] is True

    def test_initial_teams(self):
        sb = StateBuilder(my_username="TestUser")
        assert sb.game_state["players"][0]["team"] == "us"
        assert sb.game_state["players"][1]["team"] == "them"
        assert sb.game_state["players"][2]["team"] == "us"
        assert sb.game_state["players"][3]["team"] == "them"

    def test_is_my_turn_false_initially(self):
        sb = StateBuilder(my_username="TestUser")
        assert sb.is_my_turn() is False


# ── Identity Discovery ──────────────────────────────────────────────

class TestIdentityDiscovery:
    def test_discover_seat_from_sn_fields(self):
        sb = StateBuilder(my_username="Alice")
        event = _make_game_state_event(
            sn0="Bob", sn1="Carol", sn2="Alice", sn3="Dave",
            gStg=2,
        )
        sb.process_event(event)
        assert sb.my_seat == 2

    def test_names_remapped_after_discovery(self):
        sb = StateBuilder(my_username="Alice")
        event = _make_game_state_event(
            sn0="Bob", sn1="Carol", sn2="Alice", sn3="Dave",
            gStg=2,
        )
        sb.process_event(event)
        # Alice (seat 2) should be Bottom (index 0)
        assert sb.game_state["players"][0]["name"] == "Alice"
        # Dave (seat 3) should be Right (index 1)
        assert sb.game_state["players"][1]["name"] == "Dave"
        # Bob (seat 0) should be Top (index 2)
        assert sb.game_state["players"][2]["name"] == "Bob"
        # Carol (seat 1) should be Left (index 3)
        assert sb.game_state["players"][3]["name"] == "Carol"

    def test_identity_not_rediscovered(self):
        sb = StateBuilder(my_username="Alice")
        sb.my_seat = 1  # Pre-set
        event = _make_game_state_event(sn0="Alice", sn1="Bob", gStg=2)
        sb.process_event(event)
        # Should NOT change to seat 0
        assert sb.my_seat == 1


# ── Seat Remapping ──────────────────────────────────────────────────

class TestSeatRemapping:
    def test_remap_with_seat_0(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        assert sb._remap_seat(0) == 0
        assert sb._remap_seat(1) == 1
        assert sb._remap_seat(2) == 2
        assert sb._remap_seat(3) == 3

    def test_remap_with_seat_2(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 2
        assert sb._remap_seat(2) == 0  # Us → Bottom
        assert sb._remap_seat(3) == 1  # → Right
        assert sb._remap_seat(0) == 2  # → Top (partner)
        assert sb._remap_seat(1) == 3  # → Left

    def test_remap_with_seat_3(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 3
        assert sb._remap_seat(3) == 0  # Us → Bottom
        assert sb._remap_seat(0) == 1  # → Right
        assert sb._remap_seat(1) == 2  # → Top (partner)
        assert sb._remap_seat(2) == 3  # → Left

    def test_remap_without_seat(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = None
        assert sb._remap_seat(2) == 2  # No remap


# ── Game State Processing ───────────────────────────────────────────

class TestGameStateProcessing:
    def test_phase_bidding(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gStg=1))
        assert sb.game_state["phase"] == "BIDDING"

    def test_phase_playing(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gStg=2))
        assert sb.game_state["phase"] == "PLAYING"

    def test_phase_trick_complete_maps_to_playing(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gStg=3))
        assert sb.game_state["phase"] == "PLAYING"

    def test_game_mode_sun_int(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gm=1))
        assert sb.game_state["gameMode"] == "SUN"

    def test_game_mode_hokum_int(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gm=2))
        assert sb.game_state["gameMode"] == "HOKUM"

    def test_game_mode_sun_string(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gm="sun"))
        assert sb.game_state["gameMode"] == "SUN"

    def test_game_mode_hokum_string(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gm="hokom"))
        assert sb.game_state["gameMode"] == "HOKUM"

    def test_trump_suit_hokum(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gm=2, ts=1))
        assert sb.game_state["trumpSuit"] == "♥"

    def test_trump_suit_none_for_sun(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gm=1, ts=2))
        assert sb.game_state["trumpSuit"] is None

    def test_dealer_remapped(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 2
        # Dealer is Source seat 1 (1-indexed), so 0-indexed = 0
        # Remap: (0 - 2) % 4 = 2
        sb.process_event(_make_game_state_event(dealer=1))
        assert sb.game_state["dealerIndex"] == 2

    def test_mover_remapped(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 2
        # Mover is Source seat 3 (1-indexed), so 0-indexed = 2 = us
        # Remap: (2 - 2) % 4 = 0
        sb.process_event(_make_game_state_event(mover=3))
        assert sb.game_state["currentTurnIndex"] == 0

    def test_floor_card(self):
        sb = StateBuilder(my_username="Test")
        # Card index 12 = ♠A (suit=0, rank=12)
        sb.process_event(_make_game_state_event(fc=12))
        assert sb.game_state["floorCard"] == {"suit": "♠", "rank": "A"}


# ── Hand Decoding ───────────────────────────────────────────────────

class TestHandDecoding:
    def test_hand_from_single_bitmask(self):
        sb = StateBuilder(my_username="Test")
        # ♠7 (index 5) + ♠A (index 12) → bits 5 and 12 set
        bitmask = (1 << 5) | (1 << 12)
        sb.process_event(_make_game_state_event(pcs=bitmask))
        hand = sb.game_state["players"][0]["hand"]
        suits_ranks = {(c["suit"], c["rank"]) for c in hand}
        assert ("♠", "7") in suits_ranks
        assert ("♠", "A") in suits_ranks

    def test_hand_from_array_bitmask(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 1
        # Source seat 1 gets cards, others empty
        bitmask_seat1 = (1 << 18) | (1 << 25)  # ♥7 and ♥A
        pcs = [0, bitmask_seat1, 0, 0]
        sb.process_event(_make_game_state_event(pcs=pcs))
        # Seat 1 remapped: (1 - 1) % 4 = 0 → Bottom
        hand = sb.game_state["players"][0]["hand"]
        suits_ranks = {(c["suit"], c["rank"]) for c in hand}
        assert ("♥", "7") in suits_ranks
        assert ("♥", "A") in suits_ranks


# ── Table Cards ─────────────────────────────────────────────────────

class TestTableCards:
    def test_table_cards_from_played_cards(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        # Seat 0 plays ♠A (12), seat 1 plays ♥K (24)
        sb.process_event(_make_game_state_event(
            played_cards=[12, 24, -1, -1]
        ))
        table = sb.game_state["tableCards"]
        assert len(table) == 2
        # Seat 0 → Bottom (remap: 0-0=0)
        assert table[0]["playedBy"] == "Bottom"
        assert table[0]["card"]["suit"] == "♠"
        assert table[0]["card"]["rank"] == "A"
        # Seat 1 → Right (remap: 1-0=1)
        assert table[1]["playedBy"] == "Right"

    def test_negative_indices_ignored(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        sb.process_event(_make_game_state_event(
            played_cards=[-1, -1, -1, -1]
        ))
        assert sb.game_state["tableCards"] == []


# ── Turn Detection ──────────────────────────────────────────────────

class TestTurnDetection:
    def test_my_turn_when_mover_is_us(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 2
        sb.process_event(_make_game_state_event(gStg=2, mover=3))
        # Source mover 3 → 0-indexed 2 → remap (2-2)%4=0 → us
        assert sb.is_my_turn() is True

    def test_not_my_turn_when_mover_is_other(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 2
        sb.process_event(_make_game_state_event(gStg=2, mover=2))
        # Source mover 2 → 0-indexed 1 → remap (1-2)%4=3
        assert sb.is_my_turn() is False

    def test_not_my_turn_when_finished(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        sb.game_state["phase"] = "FINISHED"
        sb.game_state["currentTurnIndex"] = 0
        assert sb.is_my_turn() is False

    def test_not_my_turn_without_seat(self):
        sb = StateBuilder(my_username="Test")
        sb.game_state["phase"] = "PLAYING"
        sb.game_state["currentTurnIndex"] = 0
        assert sb.is_my_turn() is False


# ── Trick Won ───────────────────────────────────────────────────────

class TestTrickWon:
    def test_trick_archived_on_trick_won(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        # Set up table cards
        sb.game_state["tableCards"] = [
            {"card": {"suit": "♠", "rank": "A"}, "playedBy": "Bottom",
             "playerId": None, "metadata": None},
            {"card": {"suit": "♥", "rank": "K"}, "playedBy": "Right",
             "playerId": None, "metadata": None},
        ]
        # Process trick won — ap=1 (Source seat 0 wins)
        event = _make_event("a_cards_eating", {"ap": 1})
        sb.process_event(event)

        assert len(sb.game_state["currentRoundTricks"]) == 1
        trick = sb.game_state["currentRoundTricks"][0]
        assert trick["winner"] == "Bottom"
        assert len(trick["cards"]) == 2
        assert sb.game_state["tableCards"] == []

    def test_trick_count_increments(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        # Two tricks
        for _ in range(2):
            sb.game_state["tableCards"] = [
                {"card": {"suit": "♠", "rank": "7"}, "playedBy": "Bottom",
                 "playerId": None, "metadata": None},
            ]
            sb.process_event(_make_event("a_cards_eating", {"ap": 1}))

        assert sb.game_state["trickCount"] == 2


# ── Bidding ─────────────────────────────────────────────────────────

class TestBidding:
    def test_bid_sun_string(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_event("a_bid", {"bt": "sun", "ap": 1})
        sb.process_event(event)
        assert len(sb.game_state["bidHistory"]) == 1
        assert sb.game_state["bidHistory"][0]["action"] == "SUN"
        assert sb.game_state["bid"]["type"] == "SUN"

    def test_bid_hokum_with_suit(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_event("a_bid", {"bt": "hokom", "ap": 2, "ts": 3})
        sb.process_event(event)
        assert sb.game_state["bidHistory"][0]["action"] == "HOKUM"
        assert sb.game_state["bidHistory"][0]["suit"] == "♦"
        assert sb.game_state["bid"]["type"] == "HOKUM"
        assert sb.game_state["bid"]["suit"] == "♦"

    def test_bid_pass(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_event("a_bid", {"bt": "pass", "ap": 1})
        sb.process_event(event)
        assert sb.game_state["bidHistory"][0]["action"] == "PASS"
        assert sb.game_state["bid"]["type"] is None  # PASS doesn't set bid type

    def test_bid_int_format(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_event("a_bid", {"bt": 2, "ap": 1, "ts": 0})
        sb.process_event(event)
        assert sb.game_state["bidHistory"][0]["action"] == "HOKUM"
        assert sb.game_state["bidHistory"][0]["suit"] == "♠"


# ── New Round ───────────────────────────────────────────────────────

class TestNewRound:
    def test_round_reset_on_pcscount_8(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        # Pre-populate some state
        sb.game_state["trickCount"] = 5
        sb.game_state["currentRoundTricks"] = [{"winner": "Bottom"}]
        sb.game_state["bidHistory"] = [{"action": "SUN"}]

        # pcsCount all 8 = new round
        event = _make_game_state_event(pcsCount=[8, 8, 8, 8])
        sb.process_event(event)

        assert sb.game_state["trickCount"] == 0
        assert sb.game_state["currentRoundTricks"] == []
        assert sb.game_state["bidHistory"] == []
        assert sb.game_state["floorCard"] is None


# ── Round End ───────────────────────────────────────────────────────

class TestRoundEnd:
    def test_phase_set_to_finished(self):
        sb = StateBuilder(my_username="Test")
        event = _make_event("round_over", {})
        sb.process_event(event)
        assert sb.game_state["phase"] == "FINISHED"


# ── Payload Extraction ──────────────────────────────────────────────

class TestPayloadExtraction:
    def test_extracts_nested_p_p(self):
        fields = {"p": {"p": {"gStg": 2, "gm": 1}}}
        payload = StateBuilder._extract_payload(fields)
        assert payload.get("gStg") == 2
        assert payload.get("gm") == 1

    def test_extracts_single_p(self):
        fields = {"p": {"gStg": 1}}
        payload = StateBuilder._extract_payload(fields)
        assert payload.get("gStg") == 1

    def test_returns_fields_if_no_p(self):
        fields = {"gStg": 2}
        payload = StateBuilder._extract_payload(fields)
        assert payload.get("gStg") == 2


# ── Summary / Snapshot ──────────────────────────────────────────────

class TestSnapshot:
    def test_snapshot_is_deep_copy(self):
        sb = StateBuilder(my_username="Test")
        snap = sb.get_snapshot()
        snap["phase"] = "MODIFIED"
        assert sb.game_state["phase"] is None  # Original unmodified

    def test_summary_string(self):
        sb = StateBuilder(my_username="Test")
        sb.process_event(_make_game_state_event(gStg=2, gm=1))
        s = sb.summary()
        assert "PLAYING" in s
        assert "SUN" in s


# ── Integration: Full Game Flow ─────────────────────────────────────

class TestIntegrationFlow:
    def test_bidding_to_playing(self):
        sb = StateBuilder(my_username="Alice")

        # Identity discovery
        sb.process_event(_make_game_state_event(
            sn0="Bob", sn1="Carol", sn2="Alice", sn3="Dave",
            gStg=1, dealer=1,
        ))
        assert sb.my_seat == 2
        assert sb.game_state["phase"] == "BIDDING"

        # Floor card shown
        sb.process_event(_make_game_state_event(fc=12))  # ♠A
        assert sb.game_state["floorCard"]["rank"] == "A"

        # Bid: Alice bids SUN
        sb.process_event(_make_event("a_bid", {"bt": "sun", "ap": 3}))
        assert sb.game_state["bid"]["type"] == "SUN"

        # Bid ends, switch to playing
        sb.process_event(_make_event("hokom_result", {"gm": 1}))
        assert sb.game_state["phase"] == "PLAYING"
        assert sb.game_state["gameMode"] == "SUN"

        # Cards dealt — our hand
        hand_bitmask = (1 << 5) | (1 << 6) | (1 << 7) | (1 << 8)  # ♠7,♠8,♠9,♠10
        sb.process_event(_make_game_state_event(pcs=hand_bitmask, mover=3))
        assert len(sb.game_state["players"][0]["hand"]) == 4
        assert sb.is_my_turn() is True  # mover=3 → seat 2 → us

        # Card played on table
        sb.process_event(_make_game_state_event(
            played_cards=[12, -1, -1, -1], mover=2
        ))
        assert len(sb.game_state["tableCards"]) == 1

        # Trick won
        sb.game_state["tableCards"] = [
            {"card": {"suit": "♠", "rank": "A"}, "playedBy": "Top",
             "playerId": None, "metadata": None},
        ]
        sb.process_event(_make_event("a_cards_eating", {"ap": 1}))
        assert len(sb.game_state["currentRoundTricks"]) == 1


# ── JoinRoom Identity Discovery ─────────────────────────────────────

def _make_joinroom_event(pinfo_data=None, user_list=None) -> dict:
    """Build a JoinRoom event (a=4) with optional pinfo and user list."""
    fields = {"a": 4, "p": {}}
    if pinfo_data is not None:
        # pinfo lives in fields.p.r[8] as a room variable
        room_vars = [["pinfo", 18, pinfo_data]]  # type 18 = SFSArray
        # r is a list, index 8 has room variables
        r = [None, None, None, None, None, None, None, None, room_vars]
        fields["p"]["r"] = r
    if user_list is not None:
        fields["p"]["ul"] = user_list
    return {
        "timestamp": 1000,
        "direction": "RECV",
        "action": "sfs_cmd:0:4",
        "fields": fields,
        "raw_size": 200,
    }


class TestJoinRoomIdentity:
    """Test identity discovery from JoinRoom (a=4) events."""

    def test_pinfo_discovers_seat(self):
        sb = StateBuilder(my_username="Alice")
        pinfo = [
            {"n": "Bob", "i": 100, "pts": 0},
            {"n": "Alice", "i": 101, "pts": 0},
            {"n": "Carol", "i": 102, "pts": 0},
            {"n": "Dave", "i": 103, "pts": 0},
        ]
        event = _make_joinroom_event(pinfo_data=pinfo)
        sb.process_event(event)
        assert sb.my_seat == 1

    def test_pinfo_remaps_names(self):
        sb = StateBuilder(my_username="Alice")
        pinfo = [
            {"n": "Bob", "i": 100},
            {"n": "Alice", "i": 101},
            {"n": "Carol", "i": 102},
            {"n": "Dave", "i": 103},
        ]
        event = _make_joinroom_event(pinfo_data=pinfo)
        sb.process_event(event)
        # Alice seat 1 → Bottom (index 0)
        assert sb.game_state["players"][0]["name"] == "Alice"
        # Carol seat 2 → Right (index 1)
        assert sb.game_state["players"][1]["name"] == "Carol"
        # Dave seat 3 → Top (index 2)
        assert sb.game_state["players"][2]["name"] == "Dave"
        # Bob seat 0 → Left (index 3)
        assert sb.game_state["players"][3]["name"] == "Bob"

    def test_pinfo_no_match(self):
        sb = StateBuilder(my_username="Zara")
        pinfo = [
            {"n": "Bob", "i": 100},
            {"n": "Alice", "i": 101},
        ]
        event = _make_joinroom_event(pinfo_data=pinfo)
        sb.process_event(event)
        assert sb.my_seat is None

    def test_pinfo_empty_names_skipped(self):
        sb = StateBuilder(my_username="Alice")
        pinfo = [
            {"n": "", "i": 100},
            {"n": "Alice", "i": 101},
            {"i": 102},  # missing 'n' key
            {"n": "Dave", "i": 103},
        ]
        event = _make_joinroom_event(pinfo_data=pinfo)
        sb.process_event(event)
        assert sb.my_seat == 1
        assert sb._player_names[0] == ""  # Empty name kept as empty
        assert sb._player_names[2] == ""  # Missing 'n' kept as empty

    def test_pinfo_more_than_4_entries_truncated(self):
        sb = StateBuilder(my_username="Alice")
        pinfo = [
            {"n": "Bob", "i": 1},
            {"n": "Alice", "i": 2},
            {"n": "Carol", "i": 3},
            {"n": "Dave", "i": 4},
            {"n": "Eve", "i": 5},  # 5th entry ignored
        ]
        event = _make_joinroom_event(pinfo_data=pinfo)
        sb.process_event(event)
        assert sb.my_seat == 1

    def test_user_list_discovers_seat(self):
        sb = StateBuilder(my_username="Alice")
        ul = [
            # [internal_id, user_id_str, ?, seat_1indexed, [[key, type, value, ...], ...]]
            [1, "u1", 0, 1, [["n", 8, "Bob"]]],
            [2, "u2", 0, 2, [["n", 8, "Alice"]]],
            [3, "u3", 0, 3, [["n", 8, "Carol"]]],
            [4, "u4", 0, 4, [["n", 8, "Dave"]]],
        ]
        event = _make_joinroom_event(user_list=ul)
        sb.process_event(event)
        # seat_1indexed=2 → 0-indexed=1
        assert sb.my_seat == 1

    def test_user_list_remaps_names(self):
        sb = StateBuilder(my_username="Alice")
        ul = [
            [1, "u1", 0, 1, [["n", 8, "Bob"]]],
            [2, "u2", 0, 2, [["n", 8, "Alice"]]],
            [3, "u3", 0, 3, [["n", 8, "Carol"]]],
            [4, "u4", 0, 4, [["n", 8, "Dave"]]],
        ]
        event = _make_joinroom_event(user_list=ul)
        sb.process_event(event)
        assert sb.game_state["players"][0]["name"] == "Alice"   # Bottom
        assert sb.game_state["players"][1]["name"] == "Carol"   # Right
        assert sb.game_state["players"][2]["name"] == "Dave"    # Top
        assert sb.game_state["players"][3]["name"] == "Bob"     # Left

    def test_user_list_invalid_seat_skipped(self):
        sb = StateBuilder(my_username="Alice")
        ul = [
            [1, "u1", 0, 0, [["n", 8, "Bob"]]],    # seat 0 invalid (1-indexed)
            [2, "u2", 0, 5, [["n", 8, "Alice"]]],   # seat 5 invalid
        ]
        event = _make_joinroom_event(user_list=ul)
        sb.process_event(event)
        assert sb.my_seat is None

    def test_user_list_short_entry_skipped(self):
        sb = StateBuilder(my_username="Alice")
        ul = [
            [1, "u1"],  # Too short (< 5 elements)
            [2, "u2", 0, 2, [["n", 8, "Alice"]]],
        ]
        event = _make_joinroom_event(user_list=ul)
        sb.process_event(event)
        assert sb.my_seat == 1

    def test_pinfo_and_user_list_combined(self):
        """When both pinfo and ul are present, pinfo runs first."""
        sb = StateBuilder(my_username="Alice")
        pinfo = [
            {"n": "Bob", "i": 100},
            {"n": "Alice", "i": 101},
            {"n": "Carol", "i": 102},
            {"n": "Dave", "i": 103},
        ]
        ul = [
            [1, "u1", 0, 1, [["n", 8, "Bob"]]],
            [2, "u2", 0, 2, [["n", 8, "Alice"]]],
        ]
        event = _make_joinroom_event(pinfo_data=pinfo, user_list=ul)
        sb.process_event(event)
        # pinfo discovers seat first
        assert sb.my_seat == 1

    def test_joinroom_doesnt_override_existing_seat(self):
        sb = StateBuilder(my_username="Alice")
        sb.my_seat = 3  # Pre-set
        pinfo = [
            {"n": "Bob", "i": 100},
            {"n": "Alice", "i": 101},
        ]
        event = _make_joinroom_event(pinfo_data=pinfo)
        sb.process_event(event)
        # Should NOT change existing seat
        assert sb.my_seat == 3

    def test_non_joinroom_event_no_pinfo_processing(self):
        """Regular events with a=13 should NOT trigger JoinRoom processing."""
        sb = StateBuilder(my_username="Alice")
        event = {
            "timestamp": 1000,
            "direction": "RECV",
            "action": "game_state",
            "fields": {"a": 13, "p": {"r": [None] * 9}},
            "raw_size": 100,
        }
        sb.process_event(event)
        assert sb.my_seat is None


# ── Declarations ───────────────────────────────────────────────────────

class TestDeclarations:
    def test_declarations_from_dp_field(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_game_state_event(
            dp=[[], ["baloot"], [], []],
            gStg=2,
        )
        sb.process_event(event)
        decl = sb.game_state["declarations"]
        # Seat 1 → Right (remap: 1-0=1)
        assert "Right" in decl
        assert decl["Right"] == ["baloot"]

    def test_declarations_empty_slots_skipped(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_game_state_event(
            dp=[[], [], [], []],
            gStg=2,
        )
        sb.process_event(event)
        assert sb.game_state["declarations"] == {}

    def test_declarations_remapped_with_seat(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 2
        event = _make_game_state_event(
            dp=[["sra"], [], ["baloot"], []],
            gStg=2,
        )
        sb.process_event(event)
        decl = sb.game_state["declarations"]
        # Seat 0 → Top (remap: (0-2)%4=2)
        assert "Top" in decl
        assert decl["Top"] == ["sra"]
        # Seat 2 → Bottom (remap: (2-2)%4=0)
        assert "Bottom" in decl
        assert decl["Bottom"] == ["baloot"]


# ── Pinfo in Game State ──────────────────────────────────────────────

class TestPinfoInGameState:
    def test_pinfo_names_in_game_state_event(self):
        """pinfo array in the game_state payload sets player names."""
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_game_state_event(
            pinfo=[
                {"n": "Test", "i": 1},
                {"n": "Bob", "i": 2},
                {"n": "Carol", "i": 3},
                {"n": "Dave", "i": 4},
            ],
            gStg=2,
        )
        sb.process_event(event)
        # Seat 0 → Bottom, seat 1 → Right, etc.
        assert sb.game_state["players"][0]["name"] == "Test"
        assert sb.game_state["players"][1]["name"] == "Bob"
        assert sb.game_state["players"][2]["name"] == "Carol"
        assert sb.game_state["players"][3]["name"] == "Dave"

    def test_pinfo_names_remapped_with_seat(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 2
        event = _make_game_state_event(
            pinfo=[
                {"n": "Alice", "i": 1},
                {"n": "Bob", "i": 2},
                {"n": "Test", "i": 3},
                {"n": "Dave", "i": 4},
            ],
            gStg=2,
        )
        sb.process_event(event)
        # Seat 2 → Bottom, seat 3 → Right, seat 0 → Top, seat 1 → Left
        assert sb.game_state["players"][0]["name"] == "Test"
        assert sb.game_state["players"][1]["name"] == "Dave"
        assert sb.game_state["players"][2]["name"] == "Alice"
        assert sb.game_state["players"][3]["name"] == "Bob"


# ── Scores ─────────────────────────────────────────────────────────────

class TestScores:
    def test_scores_from_ss_array(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_game_state_event(ss=[10, 5, 15, 8])
        sb.process_event(event)
        # us = seats 0+2 = 10+15 = 25, them = seats 1+3 = 5+8 = 13
        assert sb.game_state["teamScores"]["us"] == 25
        assert sb.game_state["teamScores"]["them"] == 13

    def test_scores_remapped_with_seat(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 1
        event = _make_game_state_event(ss=[10, 5, 15, 8])
        sb.process_event(event)
        # us = seats 1+3 = 5+8 = 13, them = seats 0+2 = 10+15 = 25
        assert sb.game_state["teamScores"]["us"] == 13
        assert sb.game_state["teamScores"]["them"] == 25

    def test_scores_without_seat(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = None
        event = _make_game_state_event(ss=[10, 5, 15, 8])
        sb.process_event(event)
        # Default: us = seats 0+2, them = seats 1+3
        assert sb.game_state["teamScores"]["us"] == 25
        assert sb.game_state["teamScores"]["them"] == 13


# ── Round/Trick Number ─────────────────────────────────────────────────

class TestRoundTrickNumber:
    def test_trick_number_from_mn(self):
        sb = StateBuilder(my_username="Test")
        event = _make_game_state_event(mn=5)
        sb.process_event(event)
        assert sb.game_state["trickCount"] == 5

    def test_round_number_from_rb(self):
        sb = StateBuilder(my_username="Test")
        event = _make_game_state_event(rb=3)
        sb.process_event(event)
        assert sb.game_state["biddingRound"] == 3


# ── Bid End Processing ─────────────────────────────────────────────────

class TestBidEnd:
    def test_bid_end_sets_game_mode_and_playing(self):
        sb = StateBuilder(my_username="Test")
        event = _make_event("hokom_result", {"gm": "hokom", "ts": 2})
        sb.process_event(event)
        assert sb.game_state["gameMode"] == "HOKUM"
        assert sb.game_state["trumpSuit"] == "♣"
        assert sb.game_state["phase"] == "PLAYING"

    def test_bid_end_sun_no_trump(self):
        sb = StateBuilder(my_username="Test")
        event = _make_event("hokom_result", {"gm": 1})
        sb.process_event(event)
        assert sb.game_state["gameMode"] == "SUN"
        assert sb.game_state["phase"] == "PLAYING"

    def test_bid_end_int_mode(self):
        sb = StateBuilder(my_username="Test")
        event = _make_event("hokom_result", {"gm": 2, "ts": 0})
        sb.process_event(event)
        assert sb.game_state["gameMode"] == "HOKUM"
        assert sb.game_state["trumpSuit"] == "♠"


# ── Deal Processing ───────────────────────────────────────────────────

class TestDealProcessing:
    def test_deal_resets_round_state(self):
        sb = StateBuilder(my_username="Test")
        sb.game_state["trickCount"] = 4
        sb.game_state["bidHistory"] = [{"action": "SUN"}]
        sb.game_state["currentRoundTricks"] = [{"cards": []}]
        sb.game_state["floorCard"] = {"suit": "♠", "rank": "A"}

        event = _make_event("a_hand_dealt", {})
        sb.process_event(event)

        assert sb.game_state["trickCount"] == 0
        assert sb.game_state["bidHistory"] == []
        assert sb.game_state["currentRoundTricks"] == []
        assert sb.game_state["floorCard"] is None


# ── Last Action Processing ───────────────────────────────────────────

class TestLastAction:
    def test_last_action_bid_processed(self):
        sb = StateBuilder(my_username="Test")
        sb.my_seat = 0
        event = _make_game_state_event(
            gStg=1,
            last_action={"action": "a_bid", "bt": "sun", "ap": 2},
        )
        sb.process_event(event)
        assert len(sb.game_state["bidHistory"]) == 1
        assert sb.game_state["bidHistory"][0]["action"] == "SUN"
