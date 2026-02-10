"""
tests/game_logic/test_qayd_e2e_flow.py — End-to-End Qayd Flow Test

PURPOSE: Exercise the COMPLETE 5-step Qayd pipeline with Redis round-trips
between every step, exactly simulating real gameplay:

    TRIGGER → MENU_SELECT → VIOLATION_SELECT → SELECT_CRIME → SELECT_PROOF → RESULT

If ANY step breaks due to missing serialization, wrong routing, or
validation failures, this test will catch it.

This is the single test that would have caught all 3 layers of the
qayd freeze bug:
  1. Socket routing (frontend) — N/A here, but covered by flow continuity
  2. isSendingAction guard — N/A here, but covered by flow continuity
  3. Redis serialization — directly tested by round-tripping between steps

Run with:
    python -m pytest tests/game_logic/test_qayd_e2e_flow.py -v
"""
import json
import pytest
from game_engine.logic.game import Game
from game_engine.models.constants import GamePhase


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _round_trip(game: Game) -> Game:
    """Serialize → JSON string → deserialize. Exactly what Redis does."""
    data = game.to_json()
    json_str = json.dumps(data, default=str)
    loaded = json.loads(json_str)
    return Game.from_json(loaded)


def _create_playing_game() -> Game:
    """Create a game in PLAYING phase with tricks in history for Qayd selection."""
    game = Game("test_qayd_e2e")
    game.add_player("p0", "Human")
    for i in range(1, 4):
        p = game.add_player(f"p{i}", f"Bot{i}")
        if p:
            p.is_bot = True
    game.start_game()

    # Force into PLAYING phase
    game.state.phase = GamePhase.PLAYING.value
    game.state.gameMode = "SUN"
    game.state.trumpSuit = "♠"
    game.state.currentTurnIndex = 0
    game.is_locked = False
    game.timer_paused = False

    # Create fake trick history with real cards from player hands
    # Take cards from each player's hand to build a realistic trick
    cards_for_trick = []
    played_by_list = []
    for p in game.players:
        if p.hand:
            card = p.hand[0]  # Use first card
            cards_for_trick.append({'suit': card.suit, 'rank': card.rank})
            played_by_list.append(p.position)

    if len(cards_for_trick) >= 4:
        game.round_history = [{
            'cards': cards_for_trick,
            'playedBy': played_by_list,
            'winner': game.players[0].position,
            'points': 5,
        }]

    return game


# ═══════════════════════════════════════════════════════════════════════════════
#  FULL 5-STEP FLOW (with Redis round-trip between each step)
# ═══════════════════════════════════════════════════════════════════════════════

class TestQaydFullFlow:
    """Test the COMPLETE 5-step Qayd pipeline with round-trips between steps.
    
    This simulates real gameplay where room_manager.get_game() deserializes
    from Redis on EVERY action.
    """

    def test_complete_flow_with_round_trips(self):
        """The gold standard: full TRIGGER → RESULT with Redis simulation."""
        game = _create_playing_game()
        assert len(game.round_history) >= 1, "Need trick history for card selection"
        
        # ── Step 1: TRIGGER ──────────────────────────────────────────────
        result = game.qayd_engine.trigger(0)
        assert result['success'], f"Trigger failed: {result}"
        assert game.qayd_engine.state['step'] == 'MAIN_MENU'
        assert game.qayd_engine.state['active'] == True
        assert game.phase == GamePhase.CHALLENGE.value
        
        # 🔄 Redis round-trip
        game = _round_trip(game)
        assert game.qayd_engine.state['step'] == 'MAIN_MENU', "Step lost after round-trip 1"
        assert game.qayd_engine.state['active'] == True
        
        # ── Step 2: MENU_SELECT ──────────────────────────────────────────
        result = game.qayd_engine.select_menu_option('ACCUSE')
        assert result['success'], f"Menu select failed: {result}"
        assert game.qayd_engine.state['step'] == 'VIOLATION_SELECT'
        
        # 🔄 Redis round-trip
        game = _round_trip(game)
        assert game.qayd_engine.state['step'] == 'VIOLATION_SELECT', "Step lost after round-trip 2"
        assert game.qayd_engine.state['menu_option'] == 'ACCUSE'
        
        # ── Step 3: VIOLATION_SELECT ─────────────────────────────────────
        result = game.qayd_engine.select_violation('REVOKE')
        assert result['success'], f"Violation select failed: {result}"
        assert game.qayd_engine.state['step'] == 'SELECT_CARD_1'
        
        # 🔄 Redis round-trip
        game = _round_trip(game)
        assert game.qayd_engine.state['step'] == 'SELECT_CARD_1', "Step lost after round-trip 3"
        assert game.qayd_engine.state['violation_type'] == 'REVOKE'

        # ── Step 4: SELECT_CRIME ─────────────────────────────────────────
        trick = game.round_history[0]
        crime_card_data = {
            'suit': trick['cards'][0]['suit'],
            'rank': trick['cards'][0]['rank'],
            'trick_idx': 0,
            'card_idx': 0,
            'played_by': trick['playedBy'][0],
        }
        result = game.qayd_engine.select_crime_card(crime_card_data)
        assert result['success'], f"Select crime failed: {result}"
        assert game.qayd_engine.state['step'] == 'SELECT_CARD_2'
        
        # 🔄 Redis round-trip
        game = _round_trip(game)
        assert game.qayd_engine.state['step'] == 'SELECT_CARD_2', "Step lost after round-trip 4"
        assert game.qayd_engine.state['crime_card'] is not None

        # ── Step 5: SELECT_PROOF ─────────────────────────────────────────
        proof_card_data = {
            'suit': trick['cards'][1]['suit'],
            'rank': trick['cards'][1]['rank'],
            'trick_idx': 0,
            'card_idx': 1,
            'played_by': trick['playedBy'][1],
        }
        result = game.qayd_engine.select_proof_card(proof_card_data)
        assert result['success'], f"Select proof failed: {result}"
        
        # ── RESULT (adjudication happened automatically) ─────────────────
        assert game.qayd_engine.state['step'] == 'RESULT'
        assert game.qayd_engine.state['verdict'] in ('CORRECT', 'WRONG')
        assert game.qayd_engine.state['penalty_points'] > 0
        assert game.qayd_engine.state['loser_team'] in ('us', 'them')
        assert game.qayd_engine.state['reason'] is not None
        
        # 🔄 Final Redis round-trip — verdict must survive
        game = _round_trip(game)
        assert game.qayd_engine.state['step'] == 'RESULT', "Step lost after round-trip 5"
        assert game.qayd_engine.state['verdict'] in ('CORRECT', 'WRONG')
        assert game.qayd_engine.state['verdict_message'] is not None

    def test_flow_without_round_trips(self):
        """Same flow but without round-trips — tests pure engine logic."""
        game = _create_playing_game()
        
        result = game.qayd_engine.trigger(0)
        assert result['success']
        
        result = game.qayd_engine.select_menu_option('ACCUSE')
        assert result['success']
        
        result = game.qayd_engine.select_violation('REVOKE')
        assert result['success']
        
        trick = game.round_history[0]
        result = game.qayd_engine.select_crime_card({
            'suit': trick['cards'][0]['suit'],
            'rank': trick['cards'][0]['rank'],
            'trick_idx': 0, 'card_idx': 0,
            'played_by': trick['playedBy'][0],
        })
        assert result['success']
        
        result = game.qayd_engine.select_proof_card({
            'suit': trick['cards'][1]['suit'],
            'rank': trick['cards'][1]['rank'],
            'trick_idx': 0, 'card_idx': 1,
            'played_by': trick['playedBy'][1],
        })
        assert result['success']
        assert game.qayd_engine.state['verdict'] in ('CORRECT', 'WRONG')


# ═══════════════════════════════════════════════════════════════════════════════
#  WRONG-STEP REJECTION (ensure steps can't be skipped)
# ═══════════════════════════════════════════════════════════════════════════════

class TestQaydStepEnforcement:
    """Verify that actions sent in the wrong order are rejected."""

    def test_crime_card_without_trigger(self):
        game = _create_playing_game()
        result = game.qayd_engine.select_crime_card({
            'suit': '♠', 'rank': 'A', 'trick_idx': 0, 'card_idx': 0,
        })
        assert not result['success']
        assert 'Wrong step' in result['error']

    def test_proof_card_without_crime(self):
        game = _create_playing_game()
        game.qayd_engine.trigger(0)
        game.qayd_engine.select_menu_option('ACCUSE')
        game.qayd_engine.select_violation('REVOKE')
        # Skip crime card, go straight to proof
        result = game.qayd_engine.select_proof_card({
            'suit': '♠', 'rank': 'A', 'trick_idx': 0, 'card_idx': 0,
        })
        assert not result['success']
        assert 'Wrong step' in result['error']

    def test_violation_without_menu(self):
        game = _create_playing_game()
        game.qayd_engine.trigger(0)
        # Skip menu_select, go straight to violation
        result = game.qayd_engine.select_violation('REVOKE')
        assert not result['success']
        assert 'Wrong step' in result['error']

    def test_menu_select_after_round_trip_gets_correct_step(self):
        """After trigger + round-trip, menu select should work."""
        game = _create_playing_game()
        game.qayd_engine.trigger(0)
        
        game = _round_trip(game)
        
        # This is the exact scenario that was broken before the fix
        result = game.qayd_engine.select_menu_option('ACCUSE')
        assert result['success'], f"Menu select after round-trip failed: {result}"

    def test_violation_after_double_round_trip(self):
        """After trigger + menu + two round-trips, violation should work."""
        game = _create_playing_game()
        game.qayd_engine.trigger(0)
        game = _round_trip(game)
        
        game.qayd_engine.select_menu_option('ACCUSE')
        game = _round_trip(game)
        
        result = game.qayd_engine.select_violation('REVOKE')
        assert result['success'], f"Violation after double round-trip failed: {result}"


# ═══════════════════════════════════════════════════════════════════════════════
#  CANCEL AND CONFIRM
# ═══════════════════════════════════════════════════════════════════════════════

class TestQaydCancelConfirm:
    """Test cancel and confirm actions with round-trips."""

    def test_cancel_mid_flow(self):
        game = _create_playing_game()
        game.qayd_engine.trigger(0)
        game.qayd_engine.select_menu_option('ACCUSE')
        
        game = _round_trip(game)
        
        result = game.qayd_engine.cancel()
        assert result['success']
        assert game.qayd_engine.state['active'] == False
        assert game.qayd_engine.state['step'] == 'IDLE'

    def test_confirm_after_verdict(self):
        game = _create_playing_game()
        game.qayd_engine.trigger(0)
        game.qayd_engine.select_menu_option('ACCUSE')
        game.qayd_engine.select_violation('REVOKE')
        
        trick = game.round_history[0]
        game.qayd_engine.select_crime_card({
            'suit': trick['cards'][0]['suit'], 'rank': trick['cards'][0]['rank'],
            'trick_idx': 0, 'card_idx': 0, 'played_by': trick['playedBy'][0],
        })
        game.qayd_engine.select_proof_card({
            'suit': trick['cards'][1]['suit'], 'rank': trick['cards'][1]['rank'],
            'trick_idx': 0, 'card_idx': 1, 'played_by': trick['playedBy'][1],
        })
        
        game = _round_trip(game)
        assert game.qayd_engine.state['step'] == 'RESULT'
        
        result = game.qayd_engine.confirm()
        assert result['success']


# ═══════════════════════════════════════════════════════════════════════════════
#  FRONTEND STATE CHECK
# ═══════════════════════════════════════════════════════════════════════════════

class TestQaydFrontendState:
    """Verify that get_frontend_state() returns correct data at each step."""

    def test_frontend_state_at_each_step(self):
        game = _create_playing_game()
        
        # Before trigger — inactive
        fs = game.qayd_engine.get_frontend_state()
        assert fs['active'] == False
        
        # After trigger
        game.qayd_engine.trigger(0)
        fs = game.qayd_engine.get_frontend_state()
        assert fs['active'] == True
        assert fs['step'] == 'MAIN_MENU'
        assert fs['reporter'] is not None
        
        # After round-trip — frontend state must be identical
        game = _round_trip(game)
        fs2 = game.qayd_engine.get_frontend_state()
        assert fs2['active'] == True
        assert fs2['step'] == 'MAIN_MENU'
        assert fs2['reporter'] == fs['reporter']
