import pytest
from game_engine.logic.game import Game
from game_engine.models.player import Player
from game_engine.models.card import Card
from game_engine.models.constants import BiddingPhase

@pytest.fixture
def game():
    g = Game("test_room")
    g.add_player("p1", "Player 1")
    g.add_player("p2", "Player 2")
    g.add_player("p3", "Player 3")
    g.add_player("p4", "Player 4")
    g.start_game()
    return g

def test_ashkal_ace_constraint(game):
    """Test that Ashkal is rejected if Floor Card is an Ace"""
    # 1. Setup: Force Floor Card to be Ace of Hearts
    game.floor_card = Card('♥', 'A')
    if game.bidding_engine:
        game.bidding_engine.floor_card = game.floor_card
    
    # Advance to Dealer's turn 
    for i in range(3):
        idx = (game.dealer_index + 1 + i) % 4
        game.handle_bid(idx, "PASS")
        
    game.current_turn = game.dealer_index 
    
    # 2. Attempt Ashkal
    res = game.handle_bid(game.current_turn, "ASHKAL")
    
    # 3. Assert Failure
    assert res.get("error") == "Ashkal banned on Ace"
    assert game.bid["type"] is None

def test_ashkal_success_non_ace(game):
    """Test that Ashkal works if Floor Card is NOT an Ace"""
    # 1. Setup: Force Floor Card to be King of Hearts
    game.floor_card = Card('♥', 'K')
    if game.bidding_engine:
         game.bidding_engine.floor_card = game.floor_card
    
    # 2. Advance to Dealer's turn by passing others
    for i in range(3):
        idx = (game.dealer_index + 1 + i) % 4
        game.handle_bid(idx, "PASS")
    
    game.current_turn = game.dealer_index 
    
    # 3. Attempt Ashkal
    res = game.handle_bid(game.current_turn, "ASHKAL")
    
    # 4. Assert Success (Since no one better exists, it finalizes)
    assert res.get("success") is True
    assert game.bid["type"] == "SUN"
    # Bidder should be PARTNER (dealer index + 2)
    partner_pos = game.players[(game.dealer_index + 2) % 4].position
    assert game.bid["bidder"] == partner_pos
    pass

def test_kawesh_success(game):
    """Test using Kawesh to redeal (Pre-Bid: Same Dealer) — tests bidding engine directly"""
    engine = game.bidding_engine
    if not engine:
        pytest.skip("No bidding engine available")
    
    # 1. Setup Zero Value Hand on the current turn player
    turn = engine.current_turn
    player = engine.players[turn]
    player.hand = [
        Card('♠', '7'), Card('♠', '8'), Card('♠', '9'),
        Card('♥', '7'), Card('♥', '8')
    ]
    
    old_dealer = engine.dealer_index

    # 2. Attempt Kawesh (Pre-Bid -> Same Dealer) directly on engine
    res = engine.process_bid(turn, "KAWESH")
    
    assert res.get("success") is True
    assert res.get("action") == "REDEAL"
    assert res.get("rotate_dealer") is False  # Pre-bid: same dealer

def test_kawesh_fail_with_points(game):
    """Test Kawesh rejected if hand has points"""
    player = game.players[game.current_turn]
    # Give player points (Ace)
    player.hand = [
        Card('♠', 'A'), Card('♠', '8'), Card('♠', '9'),
        Card('♥', '7'), Card('♥', '8')
    ]
    if game.bidding_engine:
         game.bidding_engine.current_turn = game.current_turn
    
    res = game.handle_bid(game.current_turn, "KAWESH")
    assert res.get("error") == "Cannot call Kawesh with points (A, K, Q, J, 10) in hand"

def test_kawesh_post_bid_rotation(game):
    """Test using Kawesh AFTER a bid (Post-Bid: Next Dealer) — tests bidding engine directly"""
    engine = game.bidding_engine
    if not engine:
        pytest.skip("No bidding engine available")
    
    # 1. Setup: P1 bids SUN via the engine (not game.handle_bid which auto-finalizes)
    p1_idx = engine.current_turn
    engine.process_bid(p1_idx, "SUN")
    
    # After SUN, engine moves to DOUBLING phase.
    # Kawesh intercept in process_bid happens BEFORE the FINISHED check,
    # so it should still work.
    
    # 2. Setup: P2 (Next Player) has Zero Value Hand
    p2_idx = (p1_idx + 1) % 4
    player = engine.players[p2_idx]
    player.hand = [
        Card('♠', '7'), Card('♠', '8'), Card('♠', '9'),
        Card('♥', '7'), Card('♥', '8')
    ]
    
    old_dealer = engine.dealer_index
    
    # 3. Attempt Kawesh (Post-Bid -> Rotate Dealer)
    res = engine.process_bid(p2_idx, "KAWESH")
    
    assert res.get("success") is True
    assert res.get("action") == "REDEAL"
    assert res.get("rotate_dealer") is True  # Post-bid: dealer rotates

def test_round_2_hukum_restriction(game):
    """Test rejection of Hukum bid on Floor Card suit in Round 2"""
    # 1. Advance to Round 2
    game.bidding_round = 2
    game.floor_card = Card('♠', 'K') # Spades
    # Reset phase and sync floor card
    if game.bidding_engine: 
        game.bidding_engine.phase = BiddingPhase.ROUND_2
        game.bidding_engine.floor_card = game.floor_card
    
    # 2. Attempt Hukum Spades
    res = game.handle_bid(game.current_turn, "HOKUM", suit='♠')
    
    assert res.get("error") == "Cannot bid floor suit in Round 2"
    
    # 3. Attempt Hukum Hearts (Valid)
    res = game.handle_bid(game.current_turn, "HOKUM", suit='♥')
    assert res.get("success") is True
