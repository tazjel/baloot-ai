
import pytest
import time
from unittest.mock import MagicMock, patch
from game_logic import Game, Player, GamePhase, Card

class TestTimers:
    @pytest.fixture
    def game(self):
        g = Game("test_room")
        # Add 4 players
        for i in range(4):
            g.add_player(f"p{i}", f"Player {i}")
        g.start_game()
        g.turn_duration = 2 # Short duration for testing
        return g

    def test_timer_initialization(self, game):
        assert game.timer_active == True
        assert game.timer_start_time > 0
        assert game.turn_duration == 2

    def test_bidding_timeout(self, game):
        # Phase is BIDDING
        game.phase = GamePhase.BIDDING.value
        game.current_turn = 1
        game.reset_timer()
        
        # Simulate time passing (mock time.time would be better for precision, but integration style here)
        # We can just manually set start time to past
        game.timer_start_time = time.time() - 3 
        
        res = game.check_timeout()
        
        assert res is not None
        assert res['success'] == True
        # Check if player passed
        assert game.players[1].action_text == "PASS"
        # Turn should adhere to next logic (1 -> 2)
        assert game.current_turn == 2

    def test_playing_timeout_auto_play(self, game):
        # Setup PLAYING phase
        game.phase = GamePhase.PLAYING.value
        game.current_turn = 0
        p0 = game.players[0]
        # Give specific hand
        p0.hand = [Card('♠', 'A'), Card('♥', '7')] # Ace (11 pts), 7 (0 pts)
        game.reset_timer()
        
        # Determine expected weakest card: 7 Hearts (Points 0)
        # Ace is 11 points.
        
        # Mock timeout
        game.timer_start_time = time.time() - 3
        
        res = game.check_timeout()
        
        assert res is not None
        assert res['success'] == True
        
        # Check that a card was played
        assert len(p0.hand) == 1
        assert len(game.table_cards) == 1
        
        played_card = game.table_cards[0]['card']
        # Should be the 7 (weakest)
        assert played_card.rank == '7'
        assert played_card.suit == '♥'

    def test_auto_play_obeys_rules(self, game):
        # Case: Must follow suit
        game.phase = GamePhase.PLAYING.value
        game.current_turn = 1
        p1 = game.players[1]
        
        # Lead card is Hearts
        game.table_cards = [{'playerId': 'p0', 'card': Card('♥', '10'), 'playedBy': 'Bottom'}]
        
        # Player has Hearts and Spades
        p1.hand = [Card('♠', 'K'), Card('♥', '9'), Card('♥', 'A')] 
        # Must play Hearts. 9 is weaker than Ace.
        
        game.timer_start_time = time.time() - 3
        res = game.check_timeout()
        
        played = game.table_cards[1]['card'] # 2nd card on table
        assert played.suit == '♥'
        assert played.rank == '9' # Weakest legal card
