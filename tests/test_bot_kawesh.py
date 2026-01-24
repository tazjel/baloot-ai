import pytest
from ai_worker.agent import BotAgent

@pytest.fixture
def bot():
    return BotAgent()

def create_card(rank, suit):
    return {'rank': rank, 'suit': suit}

@pytest.fixture
def kawesh_hand():
    return [
        create_card('7', '♠'), create_card('8', '♠'), create_card('9', '♠'),
        create_card('7', '♥'), create_card('8', '♥')
    ]

@pytest.fixture
def normal_hand():
    return [
        create_card('A', '♠'), create_card('K', '♠'), create_card('Q', '♠'),
        create_card('J', '♥'), create_card('10', '♥')
    ]

def test_kawesh_pre_bid(bot, kawesh_hand):
    """Case A: No bids yet -> Call Kawesh"""
    game_state = {
        'biddingPhase': 'ROUND_1',
        'matchScores': {'us': 0, 'them': 0},
        'bid': {'type': None, 'bidder': None},
        'floorCard': {'rank': 'K', 'suit': '♦'}
    }
    player = {'index': 0, 'position': 'Bottom', 'hand': kawesh_hand}
    
    decision = bot.get_bidding_decision(game_state, player)
    assert decision['action'] == "KAWESH"
    assert "Standard Gravity" in decision['reasoning']

def test_kawesh_opponent_bid(bot, kawesh_hand):
    """Case B: Opponent Bids -> Call Kawesh (Tactical Nuke)"""
    # Opponent is Right (1) or Left (3) relative to Bottom (0)
    game_state = {
        'biddingPhase': 'ROUND_1',
        'matchScores': {'us': 0, 'them': 0},
        'bid': {'type': 'SUN', 'bidder': 'Right'}, 
        'floorCard': {'rank': 'K', 'suit': '♦'}
    }
    player = {'index': 0, 'position': 'Bottom', 'hand': kawesh_hand}
    
    decision = bot.get_bidding_decision(game_state, player)
    assert decision['action'] == "KAWESH"
    assert "Antigravity" in decision['reasoning']

def test_kawesh_partner_bid_safe(bot, kawesh_hand):
    """Case C1: Partner Bids (Safe Score) -> PASS (Friendly Fire)"""
    # Partner is Top (2) relative to Bottom (0)
    game_state = {
        'biddingPhase': 'ROUND_1',
        'matchScores': {'us': 0, 'them': 0},
        'bid': {'type': 'SUN', 'bidder': 'Top'}, 
        'floorCard': {'rank': 'K', 'suit': '♦'}
    }
    player = {'index': 0, 'position': 'Bottom', 'hand': kawesh_hand}
    
    decision = bot.get_bidding_decision(game_state, player)
    assert decision['action'] == "PASS" # Don't void partner
    assert "Friendly Fire" in decision['reasoning']

def test_kawesh_partner_bid_risky(bot, kawesh_hand):
    """Case C2: Partner Bids (Risk Zone >100 vs <100) -> KAWESH (Safety Nuke)"""
    game_state = {
        'biddingPhase': 'ROUND_1',
        # US > 100, THEM < 100 -> Danger of Double
        'matchScores': {'us': 120, 'them': 50},
        'bid': {'type': 'SUN', 'bidder': 'Top'}, 
        'floorCard': {'rank': 'K', 'suit': '♦'}
    }
    player = {'index': 0, 'position': 'Bottom', 'hand': kawesh_hand}
    
    decision = bot.get_bidding_decision(game_state, player)
    assert decision['action'] == "KAWESH"
    assert "Safety Nuke" in decision['reasoning']

def test_no_kawesh_with_points(bot, normal_hand):
    """Invalid Hand -> Normal Logic (Not Kawesh)"""
    game_state = {
        'biddingPhase': 'ROUND_1',
        'matchScores': {'us': 0, 'them': 0},
        'bid': {'type': None, 'bidder': None},
        'floorCard': {'rank': 'K', 'suit': '♦'}
    }
    player = {'index': 0, 'position': 'Bottom', 'hand': normal_hand}
    
    decision = bot.get_bidding_decision(game_state, player)
    # Should bid based on strength (Sun >= 20)
    # Normal hand (A, K, Q...) is very strong Sun.
    assert decision['action'] in ["SUN", "HOKUM", "ASHKAL", "PASS"]
    assert decision['action'] != "KAWESH"
