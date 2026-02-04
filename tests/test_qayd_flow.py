"""
Integration test for Qayd (Forensic Investigation) flow.
Tests the complete cycle: illegal move detection → Qayd trigger → auto-confirm → unlock.
"""
import pytest
import json
from game_engine.logic.game import Game
from game_engine.models.card import Card


def create_test_game_with_illegal_setup():
    """Create a game setup where an illegal move can be made"""
    game = Game("test_qayd_room")
    
    # Setup 4 players
    p0 = game.add_player("player0", "Player 0")
    p1 = game.add_player("bot1", "Bot 1")
    p2 = game.add_player("bot2", "Bot 2")
    p3 = game.add_player("bot3", "Bot 3")
    
    # Set bot flags
    p0.is_bot = False
    p1.is_bot = True
    p2.is_bot = True
    p3.is_bot = True
    
    # Start game
    game.start_game()
    
    # Force to PLAYING phase with HOKUM mode
    game.phase = "PLAYING"
    game.game_mode = "HOKUM"
    game.trump_suit = "HEARTS"
    game.current_turn = 0
    
    # Setup hands to create illegal move scenario
    # Player 0 has hearts but will try to play spades (illegal)
    game.players[0].hand = [
        Card("HEARTS", "ACE"),
        Card("HEARTS", "KING"),
        Card("SPADES", "ACE"),  # This will be the illegal card
    ]
    
    # Other players have cards
    for i in range(1, 4):
        game.players[i].hand = [
            Card("HEARTS", "10"),
            Card("DIAMONDS", "JACK"),
        ]
    
    # Start a trick with HEARTS lead
    game.table_cards = [{
        'card': Card("HEARTS", "QUEEN"),
        'playedBy': 'Bottom',
        'metadata': {}
    }]
    game.led_suit = "HEARTS"
    
    return game


def test_qayd_flow_no_freeze():
    """
    Test that Qayd doesn't freeze the game.
    Verifies: detect → trigger → auto-confirm → unlock → continue
    """
    game = create_test_game_with_illegal_setup()
    
    # Player 0 tries to play SPADES ACE when they have HEARTS (illegal move)
    # This should be flagged as illegal
    result = game.play_card(0, 2)  # Index 2 = SPADES ACE
    
    # The move should succeed (we allow illegal moves for Qayd detection)
    assert result.get('success'), f"Play card failed: {result}"
    
    # Verify the move was flagged as illegal
    last_play = game.table_cards[-1]
    assert last_play['metadata'].get('is_illegal'), "Move should be flagged as illegal"
    
    # Trigger Qayd (simulating user detection to verify locked state)
    game.players[1].is_bot = False
    qayd_result = game.handle_qayd_trigger(1)  # Player 1 triggers
    
    # Verify Qayd was triggered (Phase 1)
    assert qayd_result.get('success'), f"Qayd trigger failed: {qayd_result}"
    assert game.is_locked, "Game should be locked after Qayd trigger"
    assert game.phase == "CHALLENGE"

    # Confirm Qayd (Phase 2)
    confirm_result = game.handle_qayd_confirm()
    assert confirm_result.get('success'), f"Qayd confirm failed: {confirm_result}"
    
    # CRITICAL: Game should be unlocked after confirm
    assert not game.is_locked, "Game should be unlocked after Qayd confirm"
    
    # Verify Qayd state shows resolution
    assert game.qayd_state.get('status') == 'RESOLVED', \
        f"Qayd should be resolved, got: {game.qayd_state.get('status')}"


def test_qayd_state_serializable():
    """
    Test that Qayd state is JSON-serializable.
    This prevents the serialization error that caused the freeze.
    """
    import json
    game = create_test_game_with_illegal_setup()
    
    # Make illegal move
    game.play_card(0, 2)
    
    # Trigger Qayd
    game.handle_qayd_trigger(1)
    
    # Confirm
    game.handle_qayd_confirm()
    
    # Get qayd state directly (not full game state to avoid schema issues)
    qayd_state = game.qayd_state
    
    # Verify it's JSON-serializable (this would raise TypeError if not)
    try:
        json_str = json.dumps(qayd_state)
        assert json_str, "JSON serialization produced empty string"
    except TypeError as e:
        pytest.fail(f"Qayd state not JSON-serializable: {e}")
    
    # Verify qaydState has expected structure
    assert qayd_state.get('active') is not None, "qaydState.active should be set"
    assert qayd_state.get('status') == 'RESOLVED', "qaydState should be resolved"


def test_qayd_penalty_applied():
    """
    Test that Qayd correctly applies penalty to offending team.
    """
    game = create_test_game_with_illegal_setup()
    
    # Make illegal move
    game.play_card(0, 2)
    
    # Trigger Qayd
    game.handle_qayd_trigger(1)
    
    # Confirm Qayd
    game.handle_qayd_confirm()
    
    # Verify penalty was applied
    # Player 0 is on team 'us', so 'us' should have lost points
    assert game.qayd_state.get('loser_team') == 'us', \
        "Offending team should be marked as loser"
    
    # Verify penalty points were set
    penalty = game.qayd_state.get('penalty_points', 0)
    assert penalty > 0, f"Penalty should be positive, got: {penalty}"


def test_lock_decorator_prevents_timeout():
    """
    Test that @requires_unlocked decorator prevents timeout during Qayd.
    """
    game = create_test_game_with_illegal_setup()
    
    # Make illegal move and trigger Qayd
    game.play_card(0, 2)
    
    # Manually lock the game (simulating mid-Qayd state before auto-confirm)
    game.is_locked = True
    
    # Try to check timeout - should return None due to decorator
    result = game.check_timeout()
    assert result is None, "check_timeout should return None when game is locked"
    
    # Try to auto-play - should return None due to decorator
    result = game.auto_play_card(1)
    assert result is None, "auto_play_card should return None when game is locked"
    
    # Unlock and verify functions work again
    game.is_locked = False
    result = game.check_timeout()
    # Result can be None or dict, but shouldn't raise an error
    assert result is None or isinstance(result, dict), \
        f"check_timeout should work when unlocked, got: {type(result)}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
