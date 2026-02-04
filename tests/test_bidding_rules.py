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
    # Verify card was taken (Ashkal logic: Bidder takes it, but usually Partner gets it? 
    # Current implementation says: "Calling Ashkal buys the card as Sun, but the card is given to the Partner".
    # Wait, existing logic in `handle_bid` logic: `player.action_text = "ASHKAL"`. `self.complete_deal(player_index)`.
    # Does `complete_deal` give it to partner?
    # `game_logic.py` L550 just calls `complete_deal(player_index)`.
    # The rulebook says: "card is given to the Partner".
    # I need to check `complete_deal` or `handle_bid` logic again.
    # Currently `handle_bid` for Ashkal calls `complete_deal(player_index)` which gives to BIDDER (caller).
    # THIS IS A BUG found during test writing! The user who calls Ashkal (Dealer) usually PASSES the card to partner?
    # Or Ashkal means "I buy for my partner".
    # "Ashkal... buys the card as Sun, but the card is given to the Partner, not the caller."
    # I need to fix this in game_logic.py!
    pass

def test_kawesh_success(game):
    """Test using Kawesh to redeal (Pre-Bid: Same Dealer)"""
    # 1. Setup Zero Value Hand
    player = game.players[game.current_turn]
    player.hand = [
        Card('♠', '7'), Card('♠', '8'), Card('♠', '9'),
        Card('♥', '7'), Card('♥', '8')
    ]
    
    old_dealer = game.dealer_index
    # Sync Engine
    if game.bidding_engine:
         game.bidding_engine.current_turn = game.current_turn

    # 2. Attempt Kawesh (Pre-Bid -> Same Dealer)
    res = game.handle_bid(game.current_turn, "KAWESH")
    
    assert res.get("success") is True
    assert res.get("action") == "REDEAL"
    assert "Same Dealer" in res.get("message")
    assert game.dealer_index == old_dealer # Retained

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
    """Test using Kawesh AFTER a bid (Post-Bid: Next Dealer)"""
    # 1. Setup: P1 bids SUN
    game.floor_card = Card('♥', 'K') # Ensure floor is not Ace for Ashkal/etc
    p1_idx = game.current_turn
    game.handle_bid(p1_idx, "SUN")
    
    # 2. Setup: P2 (Next Player) has Zero Value Hand
    p2_idx = (p1_idx + 1) % 4
    player = game.players[p2_idx]
    player.hand = [
        Card('♠', '7'), Card('♠', '8'), Card('♠', '9'),
        Card('♥', '7'), Card('♥', '8')
    ]
    
    old_dealer = game.dealer_index
    
    # Force turn to P2 (Engine auto-rotates, but ensuring sync)
    if game.bidding_engine:
         game.bidding_engine.current_turn = p2_idx
         game.current_turn = p2_idx

    # 3. Attempt Kawesh (Post-Bid -> Rotate Dealer)
    res = game.handle_bid(p2_idx, "KAWESH")
    print(f"DEBUG KAWESH RES: {res}")
    
    assert res.get("success") is True
    assert res.get("action") == "REDEAL"
    assert "Dealer Rotation" in res.get("message")
    
    # Check Rotation
    expected_dealer = (old_dealer + 1) % 4
    assert game.dealer_index == expected_dealer

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
