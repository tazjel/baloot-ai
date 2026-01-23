
import sys
import os

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_logic import Game, Player, Card, validate_project, compare_projects, sort_hand, SUITS, RANKS, scan_hand_for_projects

# --- Helper Functions ---
def create_hand(cards_str_list):
    """
    Creates a list of Card objects from strings like '7♥', 'A♠'.
    """
    hand = []
    for c_str in cards_str_list:
        rank = c_str[:-1]
        suit = c_str[-1]
        hand.append(Card(suit, rank))
    return hand

def run_tests():
    print("Running tests...")
    
    # Test 1: Scan Sira
    hand = create_hand(['7♥', '8♥', '9♥', 'K♠', 'A♠'])
    projs = scan_hand_for_projects(hand, 'SUN')
    sira = next((p for p in projs if p['type'] == 'SIRA'), None)
    assert sira is not None, "Failed to detect Sira"
    assert sira['rank'] == '9', f"Wrong rank for Sira: {sira['rank']}"
    print("Test 1 (Scan Sira): PASS")

    # Test 2: Validate Project (Integration)
    hand = create_hand(['7♥', '8♥', '9♥'])
    res = validate_project(hand, "SIRA", "SUN")
    assert res['valid'] == True, "Failed to validate SIRA request"
    print("Test 2 (Validate SIRA): PASS")

    # Test 3: Fifty
    hand = create_hand(['7♥', '8♥', '9♥', '10♥'])
    res = validate_project(hand, "FIFTY", "SUN")
    assert res['valid'] == True
    assert res['type'] == 'FIFTY'
    print("Test 3 (Fifty): PASS")

    # Test 4: Hundred Sequence
    hand = create_hand(['7♥', '8♥', '9♥', '10♥', 'J♥'])
    res = validate_project(hand, "HUNDRED", "SUN")
    assert res['valid'] == True
    assert res['type'] == 'HUNDRED'
    print("Test 4 (Hundred Seq): PASS")

    # Test 5: Hundred 4Kind
    hand = create_hand(['K♥', 'K♠', 'K♦', 'K♣', '7♥'])
    res = validate_project(hand, "HUNDRED", "SUN")
    assert res['valid'] == True
    # Check if 'kind' is mostly internal, but validation shoud pass
    print("Test 5 (Hundred 4Kind): PASS")

    # Test 6: 400
    hand = create_hand(['A♥', 'A♠', 'A♦', 'A♣', '7♥'])
    res = validate_project(hand, "FOUR_HUNDRED", "SUN")
    assert res['valid'] == True
    print("Test 6 (400): PASS")

    # Test 7: Comparison Hierarchy
    p1 = {'type': 'FOUR_HUNDRED', 'rank': 'A', 'score': 40}
    p2 = {'type': 'HUNDRED', 'rank': 'A', 'score': 20}
    res = compare_projects(p1, p2, "SUN", 0, 1, 2)
    assert res == 1, "400 did not beat 100"
    print("Test 7 (Comparison): PASS")

    # Test 8: Tie Breaker (Rank)
    p1 = {'type': 'SIRA', 'rank': 'A'}
    p2 = {'type': 'SIRA', 'rank': 'K'}
    res = compare_projects(p1, p2, "SUN", 0, 1, 2)
    assert res == 1, "Sira A did not beat Sira K"
    print("Test 8 (Tie Rank): PASS")
    
    # Test 9: Tie Breaker (Position)
    p1 = {'type': 'SIRA', 'rank': '9'}
    p2 = {'type': 'SIRA', 'rank': '9'}
    # P1 index 1, P2 index 2. Dealer 0. P1 is closer.
    res = compare_projects(p1, p2, "SUN", 0, 1, 2)
    assert res == 1, "Position tie-break failed (Expected 1)"
    print("Test 9 (Tie Position): PASS")

if __name__ == "__main__":
    try:
        run_tests()
        print("\nAll Tests Passed!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

