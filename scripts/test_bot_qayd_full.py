
import sys
import os
import logging
from unittest.mock import MagicMock

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.constants import GamePhase
from game_engine.models.player import Player

# Setup Logger
logging.basicConfig(level=logging.INFO)

def test_qayd_flow():
    print("=== Testing Full Qayd Flow (Engine + Serialization) ===")
    
    # 1. Initialize Game
    game = Game("test_room")
    game.phase = GamePhase.PLAYING.value
    game.game_mode = 'SUN'
    game.trump_suit = None
    
    # Setup Players
    # Player(id, name, index, game)
    p1 = Player("P1", "Me", 0, game)
    p2 = Player("P2", "Right", 1, game)
    p3 = Player("P3", "Partner", 2, game)
    p4 = Player("P4", "Left", 3, game)
    game.players = [p1, p2, p3, p4]
    
    # 2. Simulate Illegal Move
    # P2 plays illegal card
    card = Card('♥', 'A')
    play = {
        'card': card,
        'playedBy': 'Right',
        'playerId': 'P2',
        'metadata': {'is_illegal': True, 'illegal_reason': 'REVOKE'}
    }
    game.table_cards.append(play)
    
    # 3. Trigger Qayd (via Auto-Play)
    # We need to Mock BotAgent to return QAYD_TRIGGER or trust the real one
    # Let's trust the real one since we verified it in simulation
    print("Asking Bot (P1) to analyze and trigger...")
    
    # Inject Game State into Bot logic (Mocking context if needed)
    # Actually auto_play_card calls bot_agent.get_decision(game.get_game_state(), index)
    
    # We need to ensure the Bot sees the illegal move.
    # The illegal move is in table_cards with metadata.
    
    try:
        from ai_worker.agent import bot_agent
        # Force Bot to see the move
        decision = bot_agent.get_decision(game.get_game_state(), 0)
        print(f"Bot Decision: {decision}")
        
        if decision['action'] == 'QAYD_TRIGGER':
             print("✅ Bot correctly decided to Trigger Qayd.")
        else:
             print(f"❌ Bot FAIL. Decided: {decision}")
             return False
             
        # Execute via Game.auto_play_card logic manually (since auto_play_card does networking/time checks usually)
        # Or just call handle_qayd_trigger directly as the 'result' of the decision
        result = game.handle_qayd_trigger(0)
             
    except Exception as e:
        print(f"❌ Error during Bot execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    if not result.get('success'):
        print(f"❌ FAILURE: propose_qayd failed: {result}")
        return False
        
    print(f"Result: {result}")
    qayd_state = result['qayd_state'] # key is qayd_state as per handle_qayd_trigger
    print(f"✅ Qayd Proposed. State: {qayd_state}")
    
    # Verify Verdict Field
    if qayd_state.get('verdict') is None:
         # Verdict might be None until Confirmed
         pass
         
    # 4. Verify Serialization (Game.get_game_state)
    # This checks if Game correctly picks up TrickManager's state
    game_state = game.get_game_state()
    # Game.get_game_state uses camelCase 'qaydState' for frontend
    serialized_qayd = game_state.get('qaydState')
    
    if serialized_qayd and serialized_qayd.get('active'):
        print("✅ Game.get_game_state() correctly serialized QaydState!")
    else:
        print(f"❌ FAILURE: Game state serialization issue. Got: {serialized_qayd}")
        return False
        
    # 5. Confirm Qayd (This generates verdict)
    print("Confirming Qayd...")
    game.trick_manager.confirm_qayd()
    
    if game.trick_manager.qayd_state['status'] == 'RESOLVED':
        print("✅ Qayd Resolved.")
        print(f"Verdict: {game.trick_manager.qayd_state.get('verdict')}")
    else:
        print(f"❌ FAILURE: Qayd status not RESOLVED. Got: {game.trick_manager.qayd_state['status']}")
        return False

    print("=== ALL TESTS PASSED ===")
    return True

def test_last_trick_qayd_serialization():
    print("\n=== Testing Last Trick Serialization (Explicit Card.from_dict check) ===")
    game = Game("test_room_2")
    game.phase = GamePhase.PLAYING.value
    p1 = Player("P1", "Me", 0, game)
    game.players = [p1, Player("P2", "Right", 1, game), Player("P3", "Partner", 2, game), Player("P4", "Left", 3, game)]
    
    # Mock Last Trick with Illegal Move
    # Note: trick_history stores cards as dicts
    game.round_history = [{
        'cards': [
            {'suit': 'H', 'rank': '7', 'id': '7H', 'value': 0},
            {'suit': 'D', 'rank': 'K', 'id': 'KD', 'value': 4}
        ],
        'playedBy': ['Top', 'Right'],
        'metadata': [{}, {'is_illegal': True}]
    }]
    game.last_trick = {
        'cards': [{'suit': 'H', 'rank': '7'}, {'suit': 'D', 'rank': 'K'}],
        'metadata': [{}, {'is_illegal': True}]
    }
    
    # Trigger Qayd
    print("Triggering Qayd on Last Trick...")
    result = game.handle_qayd_trigger(0)
    
    if result.get('success'):
        print(f"✅ Last Trick Qayd Success! State: {result.get('qayd_state')}")
        return True
    else:
        print(f"❌ Failed to trigger Last Trick Qayd: {result}")
        return False

if __name__ == "__main__":
    if test_qayd_flow():
        test_last_trick_qayd_serialization()
