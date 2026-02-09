import pytest
from server.schemas.game import GameStateModel
from server.schemas.base import GamePhase, Team

def test_gamestate_serialization():
    # Mock data representing a typical game state dict
    mock_state = {
        "roomId": "test_room",
        "phase": "PLAYING",
        "biddingPhase": "FINISHED",
        "players": [
            {
                "id": "p1", "name": "User1", "avatar": "av1", "index": 0,
                "hand": [{"suit": "♠", "rank": "7", "id": "7♠", "value": 0}],
                "score": 0, "team": "us", "position": "Bottom",
                "isDealer": True, "actionText": "", "lastReasoning": "", "isBot": False
            }
        ],
        "tableCards": [],
        "currentTurnIndex": 0,
        "gameMode": "SUN",
        "trumpSuit": "♠",
        "bid": {"type": "SUN", "playerIndex": 0},
        "teamScores": {"us": 0, "them": 0},
        "matchScores": {"us": 0, "them": 0},
        "analytics": {"winProbability": [0.5], "blunders": []},
        "floorCard": None,
        "dealerIndex": 0,
        "biddingRound": 1,
        "declarations": {"Bottom": []},
        "timer": {"remaining": 10, "duration": 30, "elapsed": 20, "active": True},
        "isProjectRevealing": False,
        "doublingLevel": 1,
        "isLocked": False,
        "dealingPhase": "FINISHED",
        "lastTrick": None,
        "roundHistory": [],
        "currentRoundTricks": [],
        "sawaState": None,
        "qaydState": None,
        "challengeActive": False,
        "timerStartTime": 0,
        "turnDuration": 30,
        "serverTime": 1234567890,
        "akkaState": None,
        "gameId": "test_room",
        "settings": {}
    }

    # Validate
    model = GameStateModel(**mock_state)
    assert model.roomId == "test_room"
    assert model.phase == GamePhase.PLAYING
    assert model.players[0].team == Team.US
    assert model.players[0].hand[0].suit == "♠"

    # Export
    output = model.model_dump(mode='json', by_alias=True)
    assert output['roomId'] == "test_room"
    assert output['players'][0]['team'] == "us"
    
    print("Serialization Test Passed!")

if __name__ == "__main__":
    test_gamestate_serialization()
