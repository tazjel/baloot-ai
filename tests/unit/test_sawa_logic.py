import pytest
from unittest.mock import MagicMock
from game_engine.logic.rules.sawa import check_sawa_eligibility
from game_engine.models.card import Card

@pytest.fixture
def mock_sawa_context():
    # Helper to create hand from strings like "A♠"
    def make_hand(cards_str):
        mapping = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
        hand = []
        for cs in cards_str:
            rank = cs[:-1]
            suit_char = cs[-1]
            suit = mapping.get(suit_char, suit_char)
            hand.append(Card(suit, rank))
        return hand
    return make_hand

def test_sawa_sun_perfect(mock_sawa_context):
    """Test Sawa in SUN mode with top cards"""
    hand = mock_sawa_context(["A♠", "10♠", "K♠", "A♥", "10♥"])
    played = set() # Nothing played
    
    # In SUN, A, 10, K are top. 
    # Player holds A, 10, K of Spades -> Mastered.
    # Player holds A, 10 of Hearts -> Mastered.
    # Should be True.
    assert check_sawa_eligibility(hand, played, None, "SUN", "PLAYING") == True

def test_sawa_fail_missing_top(mock_sawa_context):
    """Test Sawa fail when missing top card"""
    # Has 10♠ but Ace is out somewhere
    hand = mock_sawa_context(["10♠", "K♠", "A♥"])
    played = set() 
    
    assert check_sawa_eligibility(hand, played, None, "SUN", "PLAYING") == False

def test_sawa_valid_after_ace_played(mock_sawa_context):
    """Test Sawa valid if top card is already played"""
    # Ace played, so 10 is now master
    hand = mock_sawa_context(["10♠", "K♠"])
    played = {"A♠"} 
    
    assert check_sawa_eligibility(hand, played, None, "SUN", "PLAYING") == True

def test_sawa_hokum_trump_master(mock_sawa_context):
    """Test Sawa in HOKUM with J (Bauer)"""
    # Trump is Spades. J is top.
    hand = mock_sawa_context(["J♠", "9♠", "A♥"])
    played = set()
    
    # Holds Top 2 trumps + Master Ace heart.
    assert check_sawa_eligibility(hand, played, "♠", "HOKUM", "PLAYING") == True

def test_sawa_hokum_fail_outstanding_trump(mock_sawa_context):
    """Test Sawa fail if no trumps and enemies have them"""
    # hand has A♥ (Master Sun) but no trumps
    hand = mock_sawa_context(["A♥", "10♥"])
    played = set()
    # Trump is Spades. We have none. Enemeies have specific trumps? 
    # Logic assumes if we don't hold them and they aren't played, enemies have them.
    
    assert check_sawa_eligibility(hand, played, "♠", "HOKUM", "PLAYING") == False
