
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from game_engine.logic.forensic import ForensicReferee
from game_engine.models.constants import ORDER_HOKUM, ORDER_SUN

def test_revoke_scenario():
    print("\n=== Testing REVOKE Scenario ===")
    
    # Mock Game State
    game_state = {
        'roomId': 'TEST_ROOM',
        'gameMode': 'SUN',
        'trumpSuit': None,
        'roundHistory': [] 
    }
    
    # Pre-populate history
    # Trick 1: Bottom leads ♥7. Right plays ♣7 (Revoke!). Top plays ♥8. Left plays ♥9.
    
    trick1 = {
        'cards': [
            {'card': {'suit': '♥', 'rank': '7'}, 'playedBy': 'Bottom'},
            {'card': {'suit': '♣', 'rank': '7'}, 'playedBy': 'Right'}, # THE CRIME
            {'card': {'suit': '♥', 'rank': '8'}, 'playedBy': 'Top'},
            {'card': {'suit': '♥', 'rank': '9'}, 'playedBy': 'Left'}
        ],
        'winner': 'Left',
        'points': 0
    }
    
    # Trick 2: Right plays ♥K (The Proof! He had hearts all along)
    trick2 = {
        'cards': [
             {'card': {'suit': '♥', 'rank': 'K'}, 'playedBy': 'Right'} # THE PROOF
        ]
    }
    
    game_state['roundHistory'] = [trick1, trick2]
    
    # Accusation
    crime_card = {'suit': '♣', 'rank': '7', 'playedBy': 'Right'}
    proof_card = {'suit': '♥', 'rank': 'K', 'playedBy': 'Right'}
    
    verdict = ForensicReferee.validate_accusation(
        game_snapshot=game_state,
        crime_card=crime_card,
        proof_card=proof_card,
        violation_type='REVOKE'
    )
    
    print(f"Verdict: {verdict}")
    if verdict['is_guilty']:
        print("✅ SUCCESS: Revoke correctly identified.")
    else:
        print("❌ FAILURE: Revoke missed.")

def test_eat_scenario():
    print("\n=== Testing EAT Scenario (Hokum) ===")
    # Scenario: 
    # Mode: HOKUM (Spades Trump)
    # Trick 1: 
    # - Bottom leads ♦A (Strong). 
    # - Right (Void in Diamonds) plays ♣7 (Weak Non-Trump). FAILURE TO EAT.
    # - Top plays ♦7.
    # - Left plays ♦8.
    
    # Proof: Right plays ♠7 later.
    
    game_state = {
        'roomId': 'TEST_ROOM',
        'gameMode': 'HOKUM',
        'trumpSuit': '♠',
        'roundHistory': []
    }
    
    trick1 = {
        'cards': [
            {'card': {'suit': '♦', 'rank': 'A'}, 'playedBy': 'Bottom'},
            {'card': {'suit': '♣', 'rank': '7'}, 'playedBy': 'Right'}, # CRIME: Should have eaten with Spade
            {'card': {'suit': '♦', 'rank': '7'}, 'playedBy': 'Top'},
            {'card': {'suit': '♦', 'rank': '8'}, 'playedBy': 'Left'}
        ]
    }
    
    trick2 = {
         'cards': [
              {'card': {'suit': '♠', 'rank': '7'}, 'playedBy': 'Right'} # PROOF
         ]
    }
    
    game_state['roundHistory'] = [trick1, trick2]
    
    crime_card = {'suit': '♣', 'rank': '7', 'playedBy': 'Right'}
    proof_card = {'suit': '♠', 'rank': '7', 'playedBy': 'Right'}
    
    verdict = ForensicReferee.validate_accusation(
        game_snapshot=game_state,
        crime_card=crime_card,
        proof_card=proof_card,
        violation_type='EAT'
    )
    
    print(f"Verdict: {verdict}")
    if verdict['is_guilty']:
        print("✅ SUCCESS: Eat violation correctly identified.")
    else:
        print("❌ FAILURE: Eat violation missed.")

if __name__ == "__main__":
    test_revoke_scenario()
    test_eat_scenario()
