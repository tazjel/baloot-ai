from game_engine.logic.game import Game
from server.schemas.game import GameStateModel
import logging

try:
    game = Game("test_room")
    # Simulate problematic state matched from logs
    game.dealing_phase = 0
    game.win_probability_history = [{'trick': 7, 'us': 0.115}, {'trick': 8, 'us': 0.230}]
    game.blunders = {'Bottom': 2}
    
    print("Generating Game State...")
    state_dict = game.get_game_state()
    
    print("Validating against Pydantic Model...")
    model = GameStateModel(**state_dict)
    
    print("✅ Schema Validation Passed!")
    print(f"Serialized dealingPhase: {model.dealingPhase} (Type: {type(model.dealingPhase)})")
    print(f"Serialized blunders: {model.analytics.blunders} (Type: {type(model.analytics.blunders)})")
    
except Exception as e:
    print(f"❌ Schema Validation Failed: {e}")
    exit(1)
