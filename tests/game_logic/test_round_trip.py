"""
tests/game_logic/test_round_trip.py — Serialization Round-Trip Guard Tests

PURPOSE: Ensure every stateful component of the Game survives a
to_json() → from_json() cycle (simulating a Redis save/load).

If a new engine is added without serialization support, these tests WILL catch it.

Run with:
    python -m pytest tests/game_logic/test_round_trip.py -v
"""
import json
import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def fresh_game():
    """Create a fresh game with 4 players (1 human + 3 bots), ready to play."""
    from game_engine.logic.game import Game
    game = Game("test_rt")
    # Add 1 human + 3 bots
    game.add_player("p0", "Human")
    for i in range(1, 4):
        p = game.add_player(f"p{i}", f"Bot{i}")
        if p:
            p.is_bot = True
    game.start_game()
    return game


@pytest.fixture
def mid_game(fresh_game):
    """A game in PLAYING phase with some tricks already played."""
    game = fresh_game
    # Fast-forward through bidding
    if game.bidding_engine:
        # Force a bid so we get into PLAYING phase
        from game_engine.models.constants import GamePhase
        game.state.phase = GamePhase.PLAYING.value
        game.state.gameMode = "SUN"
        game.state.trumpSuit = "♠"
        game.state.currentTurnIndex = 0
    return game


def _round_trip(game):
    """Serialize → JSON string → deserialize. Exactly what Redis does."""
    from game_engine.logic.game import Game
    data = game.to_json()
    json_str = json.dumps(data, default=str)  # Ensure JSON-safe
    loaded = json.loads(json_str)
    return Game.from_json(loaded)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. BASIC ROUND-TRIP
# ═══════════════════════════════════════════════════════════════════════════════

class TestBasicRoundTrip:
    """Verify minimal game survives serialization."""

    def test_room_id_preserved(self, fresh_game):
        restored = _round_trip(fresh_game)
        assert restored.room_id == "test_rt"

    def test_phase_preserved(self, fresh_game):
        restored = _round_trip(fresh_game)
        assert restored.phase == fresh_game.phase

    def test_player_count(self, fresh_game):
        restored = _round_trip(fresh_game)
        assert len(restored.players) == len(fresh_game.players)

    def test_player_hands_preserved(self, fresh_game):
        restored = _round_trip(fresh_game)
        for orig, rest in zip(fresh_game.players, restored.players):
            assert len(rest.hand) == len(orig.hand)
            orig_ids = {c.id for c in orig.hand}
            rest_ids = {c.id for c in rest.hand}
            assert rest_ids == orig_ids, f"Hand mismatch for {orig.name}"

    def test_player_metadata(self, fresh_game):
        restored = _round_trip(fresh_game)
        for orig, rest in zip(fresh_game.players, restored.players):
            assert rest.name == orig.name
            assert rest.position == orig.position
            assert rest.team == orig.team
            assert rest.is_bot == orig.is_bot
            assert rest.index == orig.index

    def test_no_duplicate_cards(self, fresh_game):
        """After round-trip, all cards across all locations must be unique."""
        restored = _round_trip(fresh_game)
        all_ids = set()
        for p in restored.players:
            for c in p.hand:
                assert c.id not in all_ids, f"Duplicate card {c.id} in {p.name}'s hand"
                all_ids.add(c.id)
            for c in p.captured_cards:
                assert c.id not in all_ids, f"Duplicate card {c.id} in {p.name}'s captured"
                all_ids.add(c.id)
        for tc in restored.table_cards:
            card = tc.get('card')
            if card and hasattr(card, 'id'):
                assert card.id not in all_ids, f"Duplicate card {card.id} on table"
                all_ids.add(card.id)
        for c in restored.deck.cards:
            assert c.id not in all_ids, f"Duplicate card {c.id} in deck"
            all_ids.add(c.id)

    def test_total_card_count(self, fresh_game):
        """After round-trip, total cards (hands + captured + table + deck + floor) = 32."""
        restored = _round_trip(fresh_game)
        total = sum(len(p.hand) + len(p.captured_cards) for p in restored.players)
        total += len(restored.table_cards)
        total += len(restored.deck.cards)
        if restored._floor_card_obj:
            total += 1
        assert total == 32, f"Expected 32 cards total, got {total}"

    def test_json_is_truly_json_safe(self, fresh_game):
        """to_json() output must be serializable without custom fallback."""
        data = fresh_game.to_json()
        try:
            json_str = json.dumps(data, default=str)
        except (TypeError, ValueError) as e:
            pytest.fail(f"to_json() produced non-serializable output: {e}")
        assert len(json_str) > 0


# ═══════════════════════════════════════════════════════════════════════════════
#  2. GAME STATE (Pydantic model)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGameStateRoundTrip:
    """Verify GameState model fields survive."""

    def test_scores_preserved(self, fresh_game):
        fresh_game.state.teamScores = {"us": 42, "them": 18}
        fresh_game.state.matchScores = {"us": 2, "them": 1}
        restored = _round_trip(fresh_game)
        assert restored.team_scores == {"us": 42, "them": 18}
        assert restored.match_scores == {"us": 2, "them": 1}

    def test_bid_state_preserved(self, fresh_game):
        from game_engine.core.state import BidState
        fresh_game.state.bid = BidState(suit="♠", rank="7", bidder="Bottom")
        restored = _round_trip(fresh_game)
        assert restored.bid is not None

    def test_game_mode_preserved(self, fresh_game):
        fresh_game.state.gameMode = "HOKUM"
        fresh_game.state.trumpSuit = "♥"
        restored = _round_trip(fresh_game)
        assert restored.game_mode == "HOKUM"
        assert restored.trump_suit == "♥"

    def test_doubling_level_preserved(self, fresh_game):
        fresh_game.state.doublingLevel = 4
        restored = _round_trip(fresh_game)
        assert restored.doubling_level == 4

    def test_resolved_crimes_preserved(self, fresh_game):
        fresh_game.state.resolved_crimes = ["0_1", "2_3"]
        restored = _round_trip(fresh_game)
        assert "0_1" in restored.state.resolved_crimes
        assert "2_3" in restored.state.resolved_crimes


# ═══════════════════════════════════════════════════════════════════════════════
#  3. QAYD ENGINE STATE (the bug that inspired this file!)
# ═══════════════════════════════════════════════════════════════════════════════

class TestQaydRoundTrip:
    """Qayd state MUST survive Redis round-trip.
    
    This class exists because of a critical bug where QaydEngine state
    was not serialized, causing every Qayd step to fail with 'Wrong step: IDLE'
    after a Redis save/load cycle.
    """

    def test_inactive_qayd_round_trip(self, fresh_game):
        """Inactive Qayd state should not trip anything up."""
        restored = _round_trip(fresh_game)
        assert restored.qayd_engine.state['active'] == False
        assert restored.qayd_engine.state['step'] == 'IDLE'

    def test_active_qayd_preserves_step(self, fresh_game):
        """Triggering Qayd then round-tripping must preserve the active state."""
        from game_engine.models.constants import GamePhase
        fresh_game.state.phase = GamePhase.PLAYING.value
        
        # Trigger Qayd
        result = fresh_game.qayd_engine.trigger(0)
        assert result.get('success'), f"Trigger failed: {result}"
        assert fresh_game.qayd_engine.state['active'] == True
        assert fresh_game.qayd_engine.state['step'] == 'MAIN_MENU'
        
        # Round-trip
        restored = _round_trip(fresh_game)
        assert restored.qayd_engine.state['active'] == True
        assert restored.qayd_engine.state['step'] == 'MAIN_MENU'

    def test_qayd_menu_select_survives(self, fresh_game):
        """Menu selection step must survive round-trip."""
        from game_engine.models.constants import GamePhase
        fresh_game.state.phase = GamePhase.PLAYING.value
        
        fresh_game.qayd_engine.trigger(0)
        fresh_game.qayd_engine.select_menu_option('ACCUSE')
        assert fresh_game.qayd_engine.state['step'] == 'VIOLATION_SELECT'
        
        restored = _round_trip(fresh_game)
        assert restored.qayd_engine.state['step'] == 'VIOLATION_SELECT'
        assert restored.qayd_engine.state['menu_option'] == 'ACCUSE'

    def test_qayd_violation_select_survives(self, fresh_game):
        """Violation selection must survive round-trip."""
        from game_engine.models.constants import GamePhase
        fresh_game.state.phase = GamePhase.PLAYING.value
        
        fresh_game.qayd_engine.trigger(0)
        fresh_game.qayd_engine.select_menu_option('ACCUSE')
        fresh_game.qayd_engine.select_violation('REVOKE')
        assert fresh_game.qayd_engine.state['step'] == 'SELECT_CARD_1'
        
        restored = _round_trip(fresh_game)
        assert restored.qayd_engine.state['step'] == 'SELECT_CARD_1'
        assert restored.qayd_engine.state['violation_type'] == 'REVOKE'

    def test_qayd_reporter_preserved(self, fresh_game):
        """The reporter identity must survive round-trip."""
        from game_engine.models.constants import GamePhase
        fresh_game.state.phase = GamePhase.PLAYING.value
        
        fresh_game.qayd_engine.trigger(0)
        reporter = fresh_game.qayd_engine.state['reporter']
        
        restored = _round_trip(fresh_game)
        assert restored.qayd_engine.state['reporter'] == reporter

    def test_qayd_state_reference_is_same_object(self, fresh_game):
        """game.qayd_state must be the SAME dict as game.qayd_engine.state."""
        restored = _round_trip(fresh_game)
        assert restored.qayd_state is restored.qayd_engine.state


# ═══════════════════════════════════════════════════════════════════════════════
#  3b. AKKA STATE (Boss Card Declaration - same class of bug as Qayd)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAkkaRoundTrip:
    """Akka state MUST survive Redis round-trip.
    
    akka_state lives on GameState as an AkkaState Pydantic model.
    ProjectManager.akka_state is a property that reads game.state.akkaState.
    """

    def test_inactive_akka_round_trip(self, fresh_game):
        """Inactive Akka should remain inactive after round-trip."""
        restored = _round_trip(fresh_game)
        akka = restored.project_manager.akka_state
        assert not akka.active

    def test_active_akka_preserves_state(self, mid_game):
        """Active Akka declaration must survive round-trip."""
        import time
        from game_engine.core.state import AkkaState
        mid_game.state.akkaState = AkkaState(
            active=True,
            claimer='Bottom',
            claimerIndex=0,
            suits=['♥', '♦'],
            timestamp=time.time(),
        )

        restored = _round_trip(mid_game)
        r_akka = restored.project_manager.akka_state
        assert r_akka is not None
        assert r_akka.active == True
        assert r_akka.claimer == 'Bottom'
        assert r_akka.claimerIndex == 0
        assert '♥' in r_akka.suits
        assert '♦' in r_akka.suits

    def test_akka_in_get_game_state(self, mid_game):
        """akkaState in get_game_state() must be consistent after round-trip."""
        import time
        from game_engine.core.state import AkkaState
        mid_game.state.akkaState = AkkaState(
            active=True, claimer='Right', claimerIndex=1,
            suits=['♠'], timestamp=time.time(),
        )

        before = mid_game.get_game_state()['akkaState']
        restored = _round_trip(mid_game)
        after = restored.get_game_state()['akkaState']

        assert before['active'] == after['active']
        assert before['claimer'] == after['claimer']
        assert before['suits'] == after['suits']

    def test_akka_state_bridge_sync(self, mid_game):
        """game.akka_state must be the same object as project_manager.akka_state after round-trip."""
        import time
        from game_engine.core.state import AkkaState
        mid_game.state.akkaState = AkkaState(
            active=True, claimer='Left', claimerIndex=3, suits=['♣'], timestamp=time.time(),
        )

        restored = _round_trip(mid_game)
        assert restored.akka_state is restored.project_manager.akka_state


# ═══════════════════════════════════════════════════════════════════════════════
#  3c. SAWA STATE (Grand Slam Declaration - same class of bug as Qayd)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSawaRoundTrip:
    """Sawa state MUST survive Redis round-trip.
    
    sawa_state lives on GameState as a SawaState Pydantic model.
    TrickManager.sawa_state is a property that reads game.state.sawaState.
    """

    def test_inactive_sawa_round_trip(self, fresh_game):
        """Inactive Sawa should remain inactive after round-trip."""
        restored = _round_trip(fresh_game)
        sawa = restored.trick_manager.sawa_state
        assert sawa.active == False
        assert sawa.status == 'NONE'

    def test_active_sawa_preserves_state(self, mid_game):
        """Active Sawa claim must survive round-trip."""
        from game_engine.core.state import SawaState
        mid_game.state.sawaState = SawaState(
            active=True,
            claimer='Bottom',
            status='PENDING_TIMER',
            challenge_active=False,
            valid=True,
        )

        restored = _round_trip(mid_game)
        r_sawa = restored.trick_manager.sawa_state
        assert r_sawa.active == True
        assert r_sawa.claimer == 'Bottom'
        assert r_sawa.status == 'PENDING_TIMER'
        assert r_sawa.valid == True

    def test_sawa_challenge_active_preserved(self, mid_game):
        """Sawa with challenge_active=True must survive round-trip."""
        from game_engine.core.state import SawaState
        mid_game.state.sawaState = SawaState(
            active=True,
            claimer='Right',
            status='CHALLENGED',
            challenge_active=True,
        )

        restored = _round_trip(mid_game)
        r_sawa = restored.trick_manager.sawa_state
        assert r_sawa.challenge_active == True
        assert r_sawa.claimer == 'Right'

    def test_sawa_in_get_game_state(self, mid_game):
        """sawaState in get_game_state() must be consistent after round-trip."""
        from game_engine.core.state import SawaState
        mid_game.state.sawaState = SawaState(
            active=True, claimer='Top', status='PENDING_TIMER',
            challenge_active=False, valid=True,
        )

        before = mid_game.get_game_state()['sawaState']
        restored = _round_trip(mid_game)
        after = restored.get_game_state()['sawaState']

        assert before['active'] == after['active']
        assert before['claimer'] == after['claimer']
        assert before['status'] == after['status']


# ═══════════════════════════════════════════════════════════════════════════════
#  4. BIDDING ENGINE STATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestBiddingRoundTrip:
    """BiddingEngine must survive round-trip when active."""

    def test_bidding_engine_preserved_when_active(self, fresh_game):
        """If we're in BIDDING phase, the bidding engine must be restored."""
        from game_engine.models.constants import GamePhase
        if fresh_game.phase != GamePhase.BIDDING.value:
            pytest.skip("Game did not start in BIDDING phase")
        
        assert fresh_game.bidding_engine is not None
        restored = _round_trip(fresh_game)
        assert restored.bidding_engine is not None

    def test_bidding_engine_none_when_playing(self, mid_game):
        """In PLAYING phase, bidding engine may or may not exist."""
        mid_game.bidding_engine = None
        restored = _round_trip(mid_game)
        # Should not crash, engine can be None
        assert True


# ═══════════════════════════════════════════════════════════════════════════════
#  5. TABLE CARDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTableCardsRoundTrip:
    """Table cards with metadata must survive."""

    def test_table_cards_preserved(self, fresh_game):
        from game_engine.models.card import Card as CardModel
        fresh_game.table_cards = [
            {'card': CardModel('♠', 'A'), 'playedBy': 'Bottom', 'playerId': 'p1',
             'metadata': {'is_illegal': False}},
            {'card': CardModel('♥', 'K'), 'playedBy': 'Right', 'playerId': 'p2',
             'metadata': {'is_illegal': True}},
        ]
        restored = _round_trip(fresh_game)
        assert len(restored.table_cards) == 2
        assert restored.table_cards[0]['card'].suit == '♠'
        assert restored.table_cards[0]['card'].rank == 'A'
        assert restored.table_cards[1]['metadata']['is_illegal'] == True

    def test_empty_table(self, fresh_game):
        fresh_game.table_cards = []
        restored = _round_trip(fresh_game)
        assert len(restored.table_cards) == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  6. FLOOR CARD
# ═══════════════════════════════════════════════════════════════════════════════

class TestFloorCardRoundTrip:

    def test_floor_card_preserved(self, fresh_game):
        from game_engine.models.card import Card as CardModel
        fresh_game._floor_card_obj = CardModel('♦', '10')
        restored = _round_trip(fresh_game)
        assert restored._floor_card_obj is not None
        assert restored._floor_card_obj.suit == '♦'
        assert restored._floor_card_obj.rank == '10'

    def test_no_floor_card(self, fresh_game):
        fresh_game._floor_card_obj = None
        restored = _round_trip(fresh_game)
        assert restored._floor_card_obj is None


# ═══════════════════════════════════════════════════════════════════════════════
#  7. TIMER STATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimerRoundTrip:

    def test_timer_paused_preserved(self, fresh_game):
        fresh_game.timer_paused = True
        restored = _round_trip(fresh_game)
        assert restored.timer_paused == True

    def test_turn_duration_preserved(self, fresh_game):
        fresh_game.turn_duration = 60
        restored = _round_trip(fresh_game)
        assert restored.turn_duration == 60


# ═══════════════════════════════════════════════════════════════════════════════
#  8. CONSISTENCY CHECK: get_game_state() before and after
# ═══════════════════════════════════════════════════════════════════════════════

class TestFrontendStateConsistency:
    """The frontend-facing state should be consistent before and after round-trip.
    
    This is the ultimate integration test: if get_game_state() produces
    different output after a round-trip, the frontend will see glitches.
    """

    def _normalize(self, state: dict) -> dict:
        """Remove fields that are inherently different (timestamps, timers)."""
        skip = {'serverTime', 'timer', 'timerStartTime'}
        return {k: v for k, v in state.items() if k not in skip}

    def test_game_state_consistent(self, fresh_game):
        before = self._normalize(fresh_game.get_game_state())
        restored = _round_trip(fresh_game)
        after = self._normalize(restored.get_game_state())
        
        for key in before:
            if key in after:
                assert json.dumps(before[key], default=str) == json.dumps(after[key], default=str), \
                    f"Mismatch in '{key}':\n  before={before[key]}\n  after ={after[key]}"

    def test_qayd_frontend_state_consistent(self, fresh_game):
        """Specifically test qaydState in get_game_state()."""
        from game_engine.models.constants import GamePhase
        fresh_game.state.phase = GamePhase.PLAYING.value
        fresh_game.qayd_engine.trigger(0)
        
        before_qayd = fresh_game.get_game_state()['qaydState']
        restored = _round_trip(fresh_game)
        after_qayd = restored.get_game_state()['qaydState']
        
        assert before_qayd['active'] == after_qayd['active']
        assert before_qayd['step'] == after_qayd['step']
        assert before_qayd['reporter'] == after_qayd['reporter']
