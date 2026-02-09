
import sys
import os

# Add parent directory to path to import game_logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_logic import validate_project, Card

def test_baloot_project_valid():
    # Setup: Hokum mode, Trump = Hearts
    game_mode = 'HOKUM'
    trump_suit = '♥'
    
    # Hand: K♥, Q♥, 7♠, 8♠, 9♠
    hand = [
        Card('♥', 'K'),
        Card('♥', 'Q'),
        Card('♠', '7'),
        Card('♠', '8'),
        Card('♠', '9')
    ]
    
    result = validate_project(hand, 'BALOOT', game_mode, trump_suit)
    
    if result['valid'] and result['type'] == 'BALOOT' and result['score'] == 20:
        print("PASS: Baloot detected correctly.")
    else:
        print(f"FAIL: Expected Baloot valid, got {result}")

def test_baloot_project_invalid_suit():
    # Setup: Hokum mode, Trump = Hearts
    game_mode = 'HOKUM'
    trump_suit = '♥'
    
    # Hand: K♠, Q♠ (Not trump), ...
    hand = [
        Card('♠', 'K'),
        Card('♠', 'Q'),
        Card('♠', '7'),
        Card('♠', '8'),
        Card('♠', '9')
    ]
    
    result = validate_project(hand, 'BALOOT', game_mode, trump_suit)
    
    if not result['valid']:
        print("PASS: Non-trump Baloot rejected.")
    else:
        print(f"FAIL: Expected Invalid, got {result}")

def test_baloot_project_invalid_mode():
    # Setup: SUN mode (Baloot invalid in Sun)
    game_mode = 'SUN'
    trump_suit = None
    
    # Hand: K♥, Q♥
    hand = [
        Card('♥', 'K'),
        Card('♥', 'Q'),
        Card('♠', '7'),
        Card('♠', '8'),
        Card('♠', '9')
    ]
    
    result = validate_project(hand, 'BALOOT', game_mode, trump_suit)
    
    if not result['valid']:
        print("PASS: Sun Baloot rejected.")
    else:
        print(f"FAIL: Expected Invalid in Sun, got {result}")

if __name__ == "__main__":
    try:
        test_baloot_project_valid()
        test_baloot_project_invalid_suit()
        test_baloot_project_invalid_mode()
        print("All Baloot tests completed.")
    except Exception as e:
        print(f"ERROR: {e}")
