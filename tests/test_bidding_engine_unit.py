import pytest
import time
from game_engine.logic.bidding_engine import BiddingEngine, BiddingPhase, BidType, ContractState
from game_engine.models.card import Card

class MockPlayer:
    def __init__(self, index, team, position):
        self.index = index
        self.team = team
        self.position = position
        self.hand = []

@pytest.fixture
def players():
    return [
        MockPlayer(0, 'us', 'Bottom'),
        MockPlayer(1, 'them', 'Right'),
        MockPlayer(2, 'us', 'Top'),
        MockPlayer(3, 'them', 'Left')
    ]

@pytest.fixture
def floor_card():
    return Card('♠', '7')

@pytest.fixture
def engine(players, floor_card):
    # Dealer is P3 (Left). First turn is P0.
    return BiddingEngine(dealer_index=3, floor_card=floor_card, players=players, match_scores={'us': 0, 'them': 0})

def test_initial_state(engine):
    assert engine.phase == BiddingPhase.ROUND_1
    assert engine.current_turn == 0
    assert engine.priority_queue == [0, 1, 2, 3]

def test_pass_round_1_all(engine):
    for i in range(4):
        res = engine.process_bid(i, "PASS")
        assert res.get("success") is True
    assert engine.phase == BiddingPhase.ROUND_2

def test_pass_round_1_and_2_all(engine):
    # Pass R1
    for i in range(4): engine.process_bid(i, "PASS")
    # Pass R2
    for i in range(4): engine.process_bid(i, "PASS")
    assert engine.phase == BiddingPhase.FINISHED
    assert engine.contract.type is None

def test_hokum_bid_round_1_success(engine):
    # P0 bids Hokum Spades (floor suit)
    res = engine.process_bid(0, "HOKUM", suit='♠')
    assert res.get("success") is True
    assert engine.contract.type == BidType.HOKUM
    assert engine.contract.bidder_idx == 0
    assert engine.current_turn == 1

def test_hokum_bid_round_1_wrong_suit(engine):
    res = engine.process_bid(0, "HOKUM", suit='♥')
    assert res.get("error") == "Round 1 Hokum must be floor suit"

def test_sun_bid_hijack_hokum_directly(engine):
    # P0 bids Sun (Highest Priority)
    res = engine.process_bid(0, "SUN")
    assert res.get("success") is True
    assert res.get("phase_change") == "DOUBLING"
    assert engine.contract.type == BidType.SUN
    assert engine.contract.bidder_idx == 0

def test_gablak_trigger_simple(engine):
    # If P0 passes, P1 is turn. 
    engine.process_bid(0, "PASS")
    # If P1 (turn) bids, and P0 has already passed R1, no Gablak window should trigger 
    # because no one with BETTER priority is "Available" (Has not passed current round).
    res = engine.process_bid(1, "HOKUM", suit='♠')
    assert res.get("success") is True
    assert engine.contract.type == BidType.HOKUM

def test_gablak_priority_steal_window(engine):
    # Rotate to P2
    engine.process_bid(0, "PASS")
    engine.process_bid(1, "PASS")
    
    # P2 bids HOKUM. P0 and P1 have passed, so no Gablak.
    res = engine.process_bid(2, "HOKUM", suit='♠')
    assert res.get("success") is True
    assert engine.phase == BiddingPhase.ROUND_1
    
    # Now P3 (Dealer) wants to bid SUN. 
    # Wait, it's P3's turn now. 
    # If P3 bids SUN, P2 (who bid Hokum) is higher priority? 
    # self.priority_queue is [0, 1, 2, 3]. P2 (index 2) is priority 2. P3 (index 3) is priority 3.
    # P2 is indeed higher priority than P3.
    res = engine.process_bid(3, "SUN")
    assert res.get("status") == "GABLAK_TRIGGERED"
    assert engine.phase == BiddingPhase.GABLAK_WINDOW

def test_doubling_chain(engine):
    # 1. Finalize an auction (P0 bids Sun)
    engine.process_bid(0, "SUN")
    assert engine.phase == BiddingPhase.DOUBLING
    
    # Set scores to allow SUN doubling firewall
    engine.match_scores = {'us': 150, 'them': 50}
    
    # 2. P1 (Opponent) Doubles
    res = engine.process_bid(1, "DOUBLE")
    assert res.get("success") is True
    assert engine.contract.level == 2
    
    # 3. P0 (Taker) Triples
    res = engine.process_bid(0, "TRIPLE")
    assert res.get("success") is True
    assert engine.contract.level == 3
    
    # 4. P3 (Opponent Partner) Fours
    res = engine.process_bid(3, "FOUR")
    assert res.get("success") is True
    assert engine.contract.level == 4
    
    # 5. P2 (Partner of P0 - Taker Team) Gahwa
    res = engine.process_bid(2, "GAHWA")
    assert res.get("success") is True
    assert engine.contract.level == 100

def test_sun_double_firewall(engine):
    # Set scores below threshold
    engine.match_scores = {'us': 50, 'them': 50}
    engine.process_bid(0, "SUN") # Taker: P0 (us)
    
    # P1 (them) tries to double. 
    res = engine.process_bid(1, "DOUBLE")
    assert res.get("error") is not None
    assert "Firewall Active" in res.get("error")

def test_variant_selection(engine):
    # 1. Hokum Bid
    engine.process_bid(0, "HOKUM", suit='♠')
    # Finalize contract by passing around
    engine.process_bid(1, "PASS")
    engine.process_bid(2, "PASS")
    engine.process_bid(3, "PASS")
    
    assert engine.phase == BiddingPhase.DOUBLING
    
    # 2. P1 (Opponent) doubles
    engine.process_bid(1, "DOUBLE")
    
    # 3. Everyone passes to end doubling phase
    # Current implementation: ONE pass from anyone in doubling phase transitions if Hokum
    res = engine.process_bid(2, "PASS") 
    
    assert res.get("phase_change") == "VARIANT_SELECTION"
    assert engine.phase == BiddingPhase.VARIANT_SELECTION
    assert engine.current_turn == 0 # P0 is bidder
    
    # 4. P0 selects OPEN
    res = engine.process_bid(0, "OPEN")
    assert res.get("success") is True
    assert engine.contract.variant == "OPEN"
    assert engine.phase == BiddingPhase.FINISHED

def test_kawesh_pre_bid(engine, players):
    # P0 has zero point hand
    p0 = players[0]
    p0.hand = [Card('♠', '7'), Card('♠', '8'), Card('♠', '9'), Card('♥', '7'), Card('♥', '8')]
    
    res = engine.process_bid(0, "KAWESH")
    assert res.get("success") is True
    assert res.get("action") == "REDEAL"
    assert res.get("rotate_dealer") is False

def test_kawesh_post_bid_rotation(engine, players):
    # 1. P0 bids Sun
    engine.process_bid(0, "SUN")
    
    # 2. P1 has zero point hand
    p1 = players[1]
    p1.hand = [Card('♠', '7'), Card('♠', '8'), Card('♠', '9'), Card('♥', '7'), Card('♥', '8')]
    
    res = engine.process_bid(1, "KAWESH")
    assert res.get("success") is True
    assert res.get("action") == "REDEAL"
    assert res.get("rotate_dealer") is True
