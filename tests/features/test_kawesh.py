import pytest
from game_engine.logic.utils import is_kawesh_hand
from game_engine.models.card import Card
from game_engine.logic.bidding_engine import BiddingEngine, BiddingPhase, BidType

# Mocks
class MockPlayer:
    def __init__(self, index, hand):
        self.index = index
        self.hand = hand
        self.position = ['Bottom', 'Right', 'Top', 'Left'][index]
        self.team = 'us' if index % 2 == 0 else 'them'
        self.name = f"Player {index}"

def test_is_kawesh_hand_valid():
    """Test that a hand with only 7, 8, 9 is a valid Kawesh hand"""
    # 7s, 8s, 9s
    hand = [
        Card('♠', '7'), Card('♥', '8'), Card('♦', '9'), Card('♣', '7'), Card('♠', '8')
    ]
    assert is_kawesh_hand(hand) == True

def test_is_kawesh_hand_invalid():
    """Test that a hand with a court card is NOT a valid Kawesh hand"""
    # Contains Ace
    hand = [
        Card('♠', '7'), Card('♥', '8'), Card('♦', 'A'), Card('♣', '7'), Card('♠', '8')
    ]
    assert is_kawesh_hand(hand) == False
    
    # Contains 10
    hand2 = [
        Card('♠', '7'), Card('♥', '8'), Card('♦', '10'), Card('♣', '7'), Card('♠', '8')
    ]
    assert is_kawesh_hand(hand2) == False

def test_kawesh_action_in_engine():
    """Test that the engine accepts KAWESH action and returns REDEAL"""
    # Setup
    p0_hand = [Card('♠', '7'), Card('♥', '8'), Card('♦', '9'), Card('♣', '7'), Card('♠', '8')] # Valid
    p1_hand = [Card('♠', 'A'), Card('♥', 'K'), Card('♦', 'Q'), Card('♣', 'J'), Card('♠', '10')] # Invalid
    
    players = [
        MockPlayer(0, p0_hand),
        MockPlayer(1, p1_hand),
        MockPlayer(2, []),
        MockPlayer(3, [])
    ]
    
    engine = BiddingEngine(dealer_index=3, floor_card=Card('♠', '7'), players=players, match_scores={})
    
    # Case 1: Player 0 valid Kawesh
    result = engine.process_bid(0, "KAWESH")
    assert result['success'] == True
    assert result['action'] == "REDEAL"
    
    # Case 2: Player 1 invalid Kawesh
    result = engine.process_bid(1, "KAWESH")
    assert 'error' in result
