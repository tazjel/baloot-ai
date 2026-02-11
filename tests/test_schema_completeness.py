import pytest
from game_engine.logic.game import Game
from server.schemas.game import GameStateModel

def test_game_state_schema_completeness():
    """
    Ensures that every key returned by Game.get_game_state() is present in GameStateModel.
    This prevents fields from being silently dropped by Pydantic when sending to frontend.
    """
    # 1. Instantiate a Game
    game = Game("test_room_123")

    # 2. Get the raw state dictionary
    raw_state = game.get_game_state()

    # 3. Validate against GameStateModel
    # Pydantic (v2) by default ignores extra fields unless configured otherwise.
    # To strictly check for missing fields in the *Model* (i.e., keys in dict but not in model),
    # we can iterate over the keys.

    model_fields = GameStateModel.model_fields.keys()
    missing_in_model = []

    for key in raw_state.keys():
        if key not in model_fields:
            # Pydantic might use aliases, so we should check by_alias if needed,
            # but here we use populate_by_name=True so names should match.
            missing_in_model.append(key)

    assert not missing_in_model, f"The following keys from Game.get_game_state() are missing in GameStateModel: {missing_in_model}"

    # 4. Also ensure instantiation works (validating types)
    try:
        model = GameStateModel(**raw_state)
    except Exception as e:
        pytest.fail(f"GameStateModel instantiation failed with raw state: {e}")
