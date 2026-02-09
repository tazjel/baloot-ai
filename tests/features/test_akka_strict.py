import unittest
from game_logic import Game, Player, Card, GamePhase

class TestAkkaStrict(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room")
        self.game.add_player("p1", "Player 1")
        self.game.add_player("p2", "Player 2")
        self.game.add_player("p3", "Player 3")
        self.game.add_player("p4", "Player 4")
        self.game.start_game()
        
        # Set to Playing phase manually
        self.game.phase = GamePhase.PLAYING.value
        self.p1 = self.game.players[0]
        self.p2 = self.game.players[1]
        
    def test_akka_mode_restriction(self):
        # 1. SUN Mode -> Akka disabled
        self.game.game_mode = 'SUN'
        self.p1.hand = [Card('♥', 'K')]
        # Make Ace played
        self.game.round_history = [{'cards': [{'rank': 'A', 'suit': '♥'}, {'rank': '7', 'suit': '♥'}, {'rank': '8', 'suit': '♥'}, {'rank': '9', 'suit': '♥'}]}]
        
        eligible = self.game.check_akka_eligibility(0)
        self.assertEqual(eligible, [], "Should be empty in SUN mode")

    def test_akka_trump_restriction(self):
        # 2. Trump Suit -> Akka disabled
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠' # Spades is trump
        
        # Player has master of Trump (J in Hokum)
        # Or let's say King of Trump (if J/9 played) - logic handles strict trump exclusion
        self.p1.hand = [Card('♠', 'K')]
        
        eligible = self.game.check_akka_eligibility(0)
        self.assertEqual(eligible, [], "Should be empty for Trump suit")

    def test_akka_ace_restriction(self):
        # 3. Ace -> Akka disabled (Self-evident)
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        
        # Player has Ace of Hearts (Non-Trump)
        self.p1.hand = [Card('♥', 'A')]
        
        eligible = self.game.check_akka_eligibility(0)
        self.assertEqual(eligible, [], "Should be empty for Ace")

    def test_akka_valid_scenario(self):
        # 4. Valid Scenario: 10 of Hearts is master (Ace played)
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        
        self.p1.hand = [Card('♥', '10')]
        
        # Determine that Ace is played
        self.game.round_history = [{'cards': [{'rank': 'A', 'suit': '♥'}, {'rank': '7', 'suit': '♦'}, {'rank': '8', 'suit': '♦'}, {'rank': '9', 'suit': '♦'}]}]
        
        eligible = self.game.check_akka_eligibility(0)
        self.assertEqual(eligible, ['♥'], "Should be eligible for Hearts")

    def test_akka_invalid_scenario(self):
        # 5. Invalid Scenario: 10 of Hearts, but Ace NOT played
        self.game.game_mode = 'HOKUM'
        self.game.trump_suit = '♠'
        
        self.p1.hand = [Card('♥', '10')]
        self.game.round_history = [] # Nothing played
        self.game.table_cards = []
        
        eligible = self.game.check_akka_eligibility(0)
        self.assertEqual(eligible, [], "Should NOT be eligible if Ace is unplayed")

if __name__ == '__main__':
    unittest.main()
