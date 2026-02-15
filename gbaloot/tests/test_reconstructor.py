"""
Tests for GameReconstructor.
"""
import pytest
from gbaloot.core.reconstructor import GameReconstructor
from gbaloot.core.models import GameEvent

def test_game_info_reconstruction():
    reconstructor = GameReconstructor()
    event = GameEvent(
        timestamp=1000,
        direction="RECV",
        action="game_info",
        fields={
            "players": [
                {"id": 1, "name": "Player 1"},
                {"id": 2, "name": "Player 2"},
                {"id": 3, "name": "Player 3"},
                {"id": 4, "name": "Player 4"},
            ]
        }
    )
    reconstructor.apply_event(event)
    state = reconstructor.state
    
    assert len(state.players) == 4
    assert state.players[0].name == "Player 1"
    assert state.players[0].position == "BOTTOM"
    assert state.players[2].name == "Player 3"
    assert state.players[2].position == "TOP"

def test_card_played_logic():
    reconstructor = GameReconstructor()
    # Setup players
    reconstructor.apply_event(GameEvent(1, "RECV", "game_info", {"players": [{"id": 1, "name": "Me"}]}))
    # Setup hand
    reconstructor.apply_event(GameEvent(2, "RECV", "game_state", {"hands": {"1": ["7H", "8H", "9H"]}}))
    
    assert "7H" in reconstructor.state.players[0].hand
    
    # Play card
    reconstructor.apply_event(GameEvent(3, "RECV", "card_played", {"playerId": 1, "card": "7H"}))
    
    assert "7H" not in reconstructor.state.players[0].hand
    assert "7H" in reconstructor.state.center_cards

def test_cards_eating():
    reconstructor = GameReconstructor()
    reconstructor.state.center_cards = ["7H", "8H"]
    reconstructor.apply_event(GameEvent(4, "RECV", "cards_eating", {}))
    assert len(reconstructor.state.center_cards) == 0
