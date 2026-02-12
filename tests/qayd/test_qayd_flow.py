"""
Integration test for Qayd (Forensic Investigation) flow.
Tests the complete cycle: illegal move detection → Qayd trigger → accusation → confirm → unlock.

IMPORTANT:
  - game.qayd_state is the canonical alias for game.qayd_engine.state
  - game.trick_manager.qayd_state is a SEPARATE dict (do NOT use it here)
"""
import pytest
import json
from game_engine.logic.game import Game
from game_engine.models.card import Card


def create_test_game_with_illegal_setup():
    """Create a game setup where an illegal move can be made."""
    game = Game("test_qayd_room")

    # Setup 4 players: Bottom(0), Right(1), Top(2), Left(3)
    for i, (pid, name) in enumerate([
        ("player0", "Player 0"), ("bot1", "Bot 1"),
        ("bot2", "Bot 2"), ("bot3", "Bot 3")
    ]):
        p = game.add_player(pid, name)
        p.is_bot = (i > 0)

    game.start_game()

    # Force PLAYING / HOKUM
    game.phase = "PLAYING"
    game.game_mode = "HOKUM"
    game.trump_suit = "HEARTS"
    game.current_turn = 0  # Bottom's turn

    # Player 0 (Bottom) has HEARTS but will play SPADES (illegal revoke)
    game.players[0].hand = [
        Card("HEARTS", "ACE"),
        Card("HEARTS", "KING"),
        Card("SPADES", "ACE"),   # index 2 — the illegal card
    ]
    for i in range(1, 4):
        game.players[i].hand = [
            Card("HEARTS", "10"),
            Card("DIAMONDS", "JACK"),
        ]

    # Current trick: Left led HEARTS
    game.table_cards = [{
        'playerId': 'bot3',
        'card': Card("HEARTS", "QUEEN"),
        'playedBy': 'Left',
        'metadata': {}
    }]

    return game


# ──────────────────────────────────────────────────────────────────────────────
#  TESTS
# ──────────────────────────────────────────────────────────────────────────────

def test_qayd_flow_no_freeze():
    """Full flow: illegal play → bot accusation → confirm → unlock."""
    game = create_test_game_with_illegal_setup()

    # Bottom plays SPADES ACE (index 2) — illegal revoke
    result = game.play_card(0, 2)
    assert result.get('success'), f"Play card failed: {result}"

    # Bot 1 (Right) accuses Bottom of REVOKE
    accusation = {
        'violation_type': 'REVOKE',
        'crime_card': {
            'suit': 'SPADES', 'rank': 'ACE',
            'trick_idx': 0, 'card_idx': 1, 'played_by': 'Bottom'
        },
        'proof_card': {
            'suit': 'HEARTS', 'rank': 'ACE',
            'trick_idx': -1, 'card_idx': 0, 'played_by': 'Bottom'
        },
    }
    qayd_result = game.process_accusation(1, accusation)
    assert qayd_result.get('success'), f"Qayd accusation failed: {qayd_result}"

    # Verify state reached RESULT
    qs = game.qayd_state  # canonical alias
    assert qs['step'] == 'RESULT', f"Expected RESULT, got {qs['step']}"
    assert qs['verdict'] == 'CORRECT'
    assert game.is_locked
    assert game.phase == "CHALLENGE"

    # Confirm → apply penalty, unlock
    confirm = game.handle_qayd_confirm()
    assert confirm.get('success'), f"Qayd confirm failed: {confirm}"
    assert not game.is_locked, "Game should be unlocked after confirm"
    assert qs['status'] == 'RESOLVED'


def test_qayd_state_serializable():
    """Qayd state must be JSON-serializable after resolution."""
    game = create_test_game_with_illegal_setup()
    game.play_card(0, 2)

    accusation = {
        'violation_type': 'REVOKE',
        'crime_card': {'suit': 'SPADES', 'rank': 'ACE', 'trick_idx': 0, 'card_idx': 1, 'played_by': 'Bottom'},
        'proof_card': {'suit': 'HEARTS', 'rank': 'ACE', 'trick_idx': -1, 'card_idx': 0, 'played_by': 'Bottom'},
    }
    game.process_accusation(1, accusation)
    game.handle_qayd_confirm()

    qs = game.qayd_state
    try:
        json_str = json.dumps(qs)
        assert json_str
    except TypeError as e:
        pytest.fail(f"Qayd state not JSON-serializable: {e}")

    assert qs['status'] == 'RESOLVED'


def test_qayd_penalty_applied():
    """Penalty is applied to the correct team."""
    game = create_test_game_with_illegal_setup()
    game.play_card(0, 2)

    accusation = {
        'violation_type': 'REVOKE',
        'crime_card': {'suit': 'SPADES', 'rank': 'ACE', 'trick_idx': 0, 'card_idx': 1, 'played_by': 'Bottom'},
        'proof_card': {'suit': 'HEARTS', 'rank': 'ACE', 'trick_idx': -1, 'card_idx': 0, 'played_by': 'Bottom'},
    }
    game.process_accusation(1, accusation)
    game.handle_qayd_confirm()

    qs = game.qayd_state
    # Bottom (index 0) is team 'us'. Verdict CORRECT → offender penalised.
    assert qs['loser_team'] == 'us', f"Expected 'us', got {qs['loser_team']}"
    assert qs['penalty_points'] > 0, f"Penalty should be > 0, got {qs['penalty_points']}"


def test_lock_decorator_prevents_play():
    """@requires_unlocked blocks play_card and auto_play_card when locked.
    
    NOTE: check_timeout intentionally does NOT have @requires_unlocked
    (removed to prevent deadlocks). It handles Qayd internally via
    qayd_engine.check_timeout().
    """
    game = create_test_game_with_illegal_setup()

    # Manually lock
    game.is_locked = True

    # auto_play_card should be blocked
    result = game.auto_play_card(1)
    assert isinstance(result, dict) and result.get('error') == 'Game is locked'

    # play_card should be blocked
    result = game.play_card(0, 0)
    assert isinstance(result, dict) and 'locked' in result.get('error', '').lower()

    # Unlock — should not return the locked error anymore
    game.is_locked = False
    result = game.play_card(0, 0)
    if isinstance(result, dict):
        assert 'locked' not in result.get('error', '').lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
