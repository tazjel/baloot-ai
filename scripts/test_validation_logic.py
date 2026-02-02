
import sys
import os
import logging

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Mock Logger
logging.basicConfig(level=logging.INFO)

from game_engine.models.card import Card
from game_engine.logic.validation import is_move_legal

def test_validation():
    print("=== Testing Validation Logic ===")
    
    # Scenario: Revoke (Lead Clubs, Have Clubs, Play Hearts)
    
    # Lead Card: 7 of Clubs
    lead_play = {'card': Card('♣', '7'), 'playedBy': 'Top'}
    table_cards = [lead_play]
    
    # Hand: [9 Clubs, Ace Hearts]
    c_clubs = Card('♣', '9')
    c_hearts = Card('♥', 'A')
    hand = [c_clubs, c_hearts]
    
    # Test 1: Play Clubs (Follow Suit) -> Should be True
    print("\nTest 1: Play Clubs (Follow Suit)")
    res1 = is_move_legal(
        card=c_clubs,
        hand=hand,
        table_cards=table_cards,
        game_mode='SUN',
        trump_suit=None,
        my_team='us',
        players_team_map={'Top': 'them', 'Bottom': 'us'}
    )
    print(f"Result: {res1} (Expected: True)")
    
    # Test 2: Play Hearts (Revoke) -> Should be False
    print("\nTest 2: Play Hearts (Revoke - Have Suit)")
    res2 = is_move_legal(
        card=c_hearts,
        hand=hand,
        table_cards=table_cards,
        game_mode='SUN',
        trump_suit=None,
        my_team='us',
        players_team_map={'Top': 'them', 'Bottom': 'us'}
    )
    print(f"Result: {res2} (Expected: False)")
    
    if res2 is False:
        print("✅ SUCCESS: Validation correctly identified Revoke.")
    else:
        print("❌ FAILURE: Validation incorrectly allowed Revoke.")

if __name__ == "__main__":
    test_validation()
