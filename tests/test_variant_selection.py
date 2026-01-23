import pytest
from game_engine.models.card import Card
from server.bidding_engine import BiddingEngine, BiddingPhase, BidType

# Mocks
class MockPlayer:
    def __init__(self, index):
        self.index = index
        self.hand = []
        self.position = ['Bottom', 'Right', 'Top', 'Left'][index]
        self.team = 'us' if index % 2 == 0 else 'them'
        self.name = f"Player {index}"

def test_variant_selection_flow():
    """Test flow: Hokum Bid -> Doubling Pass -> Variant Selection -> Finished"""
    players = [MockPlayer(i) for i in range(4)]
    engine = BiddingEngine(dealer_index=3, floor_card=Card('♠', '7'), players=players, match_scores={})

    # 1. P0 Bids HOKUM (Must match floor suit in R1)
    res = engine.process_bid(0, "HOKUM", suit='♠')
    assert res['success'] == True
    assert engine.contract.type == BidType.HOKUM
    
    # 2. Transition to Checking Gablak/Turn...
    # In standard engine, bidding might continue.
    # We need to finalize the bid.
    # Assuming standard flow where everyone else passes
    engine.process_bid(1, "PASS")
    engine.process_bid(2, "PASS")
    res = engine.process_bid(3, "PASS")
    
    # After everyone passes, it should go to DOUBLING
    assert engine.phase == BiddingPhase.DOUBLING
    
    # 3. Doubling Phase: Opponent Passes (Waives right)
    # Turn is P1 (Left of Bidder P0)
    res = engine.process_bid(1, "PASS")
    
    # 4. Check Phase Transition
    # Should be VARIANT_SELECTION because contract is HOKUM
    assert res['phase_change'] == "VARIANT_SELECTION"
    assert engine.phase == BiddingPhase.VARIANT_SELECTION
    assert engine.current_turn == 0 # Back to Bidder (P0)
    
    # 5. Variant Selection
    res = engine.process_bid(0, "OPEN")
    assert res['success'] == True
    assert engine.contract.variant == "OPEN"
    assert engine.phase == BiddingPhase.FINISHED

def test_sun_variant_flow():
    """Test flow: Sun Bid -> Doubling Pass -> Finished (No Variant Selection)"""
    players = [MockPlayer(i) for i in range(4)]
    engine = BiddingEngine(dealer_index=3, floor_card=Card('♠', '7'), players=players, match_scores={})

    # 1. P0 Bids SUN (Ends Auction Immediately)
    engine.process_bid(0, "SUN")
    assert engine.contract.type == BidType.SUN
    assert engine.phase == BiddingPhase.DOUBLING
    
    # 2. Doubling Phase Pass (P1 passes)
    res = engine.process_bid(1, "PASS")
    
    # 3. Check Phase
    # Should be FINISHED (No open/closed for Sun, Doubling ended)
    assert engine.phase == BiddingPhase.FINISHED
    assert res['phase_change'] == "FINISHED"
