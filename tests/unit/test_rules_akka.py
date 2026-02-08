import pytest
from game_engine.logic.rules.akka import check_akka_eligibility

class MockCard:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank}{self.suit}"

@pytest.fixture
def mock_hand():
    return [
        MockCard('K', '♠'),
        MockCard('10', '♠'),
        MockCard('7', '♥'),
    ]

def test_akka_happy_path_highest_card(mock_hand):
    # Ace of Spades is played, so King is now Boss
    played_cards = {'A♠'} 
    trump = '♥'
    mode = 'HOKUM'
    phase = 'PLAYING'
    
    result = check_akka_eligibility(mock_hand, played_cards, trump, mode, phase)
    assert '♠' in result

def test_akka_negative_path_higher_card_exists(mock_hand):
    # Ace of Spades is NOT played, so King is NOT Boss
    played_cards = set()
    trump = '♥'
    mode = 'HOKUM'
    phase = 'PLAYING'
    
    result = check_akka_eligibility(mock_hand, played_cards, trump, mode, phase)
    assert '♠' not in result

def test_akka_self_evident_ace():
    # Player holds Ace, should rely on Project logic or just considered "too obvious" 
    # (The rule says "Must NOT be Ace"). 
    hand = [MockCard('A', '♠')]
    played = set()
    result = check_akka_eligibility(hand, played, '♥', 'HOKUM', 'PLAYING')
    assert '♠' not in result

def test_akka_wrong_mode():
    hand = [MockCard('K', '♠')]
    played = {'A♠'}
    # SUN mode -> Akka invalid
    result = check_akka_eligibility(hand, played, '♥', 'SUN', 'PLAYING')
    assert result == []

def test_akka_trump_suit():
    # King of Hearts (Trump) -> Akka invalid for Trump suit
    hand = [MockCard('K', '♥')] 
    played = {'A♥'}
    trump = '♥'
    result = check_akka_eligibility(hand, played, trump, 'HOKUM', 'PLAYING')
    assert '♥' not in result

def test_akka_king_fails_if_10_unplayed():
    """
    CRITICAL TEST: Verify User Report
    If 10 of Spades is NOT played, King cannot be Akka even if Ace is played.
    """
    hand = [MockCard('K', '♠')]
    played = {'A♠'} # Ace is gone
    # 10 is NOT in played, and NOT in hand.
    
    trump = '♥'
    result = check_akka_eligibility(hand, played, trump, 'HOKUM', 'PLAYING')
    assert '♠' not in result

def test_akka_king_succeeds_if_10_played():
    """
    CRITICAL TEST: Verify User Report
    If 10 of Spades IS played (and A is played), King IS Akka.
    """
    hand = [MockCard('K', '♠')]
    played = {'A♠', '10♠'} # Both bosses gone
    
    trump = '♥'
    result = check_akka_eligibility(hand, played, trump, 'HOKUM', 'PLAYING')
    assert '♠' in result

def test_akka_ten_is_boss_if_ace_played():
    """
    If I hold 10, and Ace is played, 10 is Akka.
    """
    hand = [MockCard('10', '♠')]
    played = {'A♠'}
    
    trump = '♥'
    result = check_akka_eligibility(hand, played, trump, 'HOKUM', 'PLAYING')
    assert '♠' in result
