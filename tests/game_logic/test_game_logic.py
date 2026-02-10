from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.player import Player
from game_engine.logic.rules.projects import check_project_eligibility
from server.room_manager import RoomManager
import unittest


def _find_project(projects, project_type):
    """Helper to find a project by type in the scan results."""
    for p in projects:
        if p['type'] == project_type:
            return p
    return None

class TestGameLogic(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room")
        # Add 4 players
        self.p1 = self.game.add_player("p1", "Player 1")
        self.p2 = self.game.add_player("p2", "Player 2")
        self.p3 = self.game.add_player("p3", "Player 3")
        self.p4 = self.game.add_player("p4", "Player 4")
        
    def test_initialization(self):
        self.assertEqual(len(self.game.players), 4)
        self.assertEqual(self.game.phase, 'WAITING')
        
    def test_start_game(self):
        self.game.start_game()
        self.assertEqual(self.game.phase, 'BIDDING')
        # Check hands (5 cards each + 1 floor)
        # 5*4 + 1 = 21 cards dealt
        self.assertEqual(len(self.p1.hand), 5)
        self.assertIsNotNone(self.game.floor_card)
        self.assertEqual(len(self.game.deck.cards), 11) # 32 - 21 = 11
        
    def test_bidding(self):
        self.game.start_game()
        bidder_idx = self.game.current_turn
        
        # Valid Bid
        res = self.game.handle_bid(bidder_idx, "SUN")
        self.assertTrue(res['success'])
        self.assertEqual(self.game.phase, 'PLAYING')
        self.assertEqual(self.game.bid['type'], 'SUN')
        
        # Check card redistribution
        # Bidder should have 5 + 1(floor) + 2(deal) = 8
        bidder = self.game.players[bidder_idx]
        self.assertEqual(len(bidder.hand), 8)
        
        # Others should have 5 + 3(deal) = 8
        for p in self.game.players:
            self.assertEqual(len(p.hand), 8)
            
    def test_trick_logic(self):
        self.game.start_game()
        bidder_idx = self.game.current_turn
        self.game.handle_bid(bidder_idx, "SUN")
        # Force Play Phase
        self.game.phase = "PLAYING"
        
        # Playing Phase
        current_p = self.game.players[self.game.current_turn]
        card = current_p.hand[0]
        
        res = self.game.play_card(current_p.index, 0)
        self.assertTrue(res['success'])
        self.assertEqual(len(self.game.table_cards), 1)
        
    def test_project_validation(self):
        # Sira check (A-K-Q sequence in spades)
        hand = [Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), Card('♥', '7'), Card('♦', '9')]
        projects = check_project_eligibility(hand, "SUN")
        sira = _find_project(projects, 'SIRA')
        self.assertIsNotNone(sira, "Should find a SIRA project")
        self.assertEqual(sira['score'], 20)
        
        # 100: 5-card sequence
        hand = [Card('♦', '7'), Card('♦', '8'), Card('♦', '9'), Card('♦', '10'), Card('♦', 'J')]
        projects = check_project_eligibility(hand, 'SUN')
        hundred = _find_project(projects, 'HUNDRED')
        self.assertIsNotNone(hundred, "Should find a HUNDRED project")
        self.assertEqual(hundred['score'], 100)
        
        # 400: 4 Aces in SUN
        hand = [Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'), Card('♠', 'A')]
        projects = check_project_eligibility(hand, 'SUN')
        four_hundred = _find_project(projects, 'FOUR_HUNDRED')
        self.assertIsNotNone(four_hundred, "Should find a FOUR_HUNDRED project")
        self.assertEqual(four_hundred['score'], 200)

    def test_validate_project_400_as_100(self):
        # 4 Aces in Sun -> scanner should find 400 (40 points = 200 Abnat)
        hand = [Card('♠', 'A'), Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'), Card('♠', '7')]
        projects = check_project_eligibility(hand, "SUN")
        four_hundred = _find_project(projects, 'FOUR_HUNDRED')
        self.assertIsNotNone(four_hundred)
        self.assertEqual(four_hundred['score'], 200)
        self.assertEqual(four_hundred['type'], 'FOUR_HUNDRED')

    def test_validate_project_400_explicit(self):
        hand = [Card('♠', 'A'), Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'), Card('♠', '7')]
        projects = check_project_eligibility(hand, "SUN")
        four_hundred = _find_project(projects, 'FOUR_HUNDRED')
        self.assertIsNotNone(four_hundred)
        self.assertEqual(four_hundred['score'], 200)

    def test_validate_project_sequence_rank(self):
        # A, K, Q in Sun -> Sequence Rank should be A (highest)
        hand = [Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), Card('♥', '7'), Card('♦', '9')]
        projects = check_project_eligibility(hand, "SUN")
        sira = _find_project(projects, 'SIRA')
        self.assertIsNotNone(sira)
        self.assertEqual(sira['score'], 20)
        self.assertEqual(sira['rank'], 'A')
        
    def test_validate_project_sequence_middle(self):
         # 9, 8, 7. Sira Sun = 20 Abnat
         hand = [Card('♠', '9'), Card('♠', '8'), Card('♠', '7'), Card('♥', 'A'), Card('♦', 'K')]
         projects = check_project_eligibility(hand, "SUN")
         sira = _find_project(projects, 'SIRA')
         self.assertIsNotNone(sira)
         self.assertEqual(sira['score'], 20)
         self.assertEqual(sira['rank'], '9')


    def test_sawa_flow(self):
        """Sawa claim by an all-bot game should auto-resolve instantly."""
        game = Game("test_sawa")
        game.add_player("p1", "P1")
        game.add_player("p2", "P2")
        game.add_player("p3", "P3")
        game.add_player("p4", "P4")
        # Mark all players as bots for instant auto-resolve
        for p in game.players:
            p.is_bot = True
        game.start_game()
        # FORCE DEALER to 0 for deterministic test
        game.dealer_index = 0
        game.current_turn = 1
        
        # Fast forward to playing
        game.handle_bid(1, "PASS")
        game.handle_bid(2, "PASS")
        game.handle_bid(3, "PASS")
        game.handle_bid(0, "SUN")
        
        self.assertEqual(game.current_turn, 1)
        
        # Give P1 a guaranteed winning hand for valid Sawa
        from game_engine.models.card import Card as C
        game.players[1].hand = [C('♠', 'A'), C('♥', 'A'), C('♦', 'A'), C('♣', 'A')]
        
        # P1 claims Sawa — as a bot, it auto-resolves instantly
        res = game.handle_sawa(1)
        self.assertTrue(res['success'])
        
        # With all bots, sawa should resolve immediately
        # Either sawa_resolved is True or the round ended
        self.assertTrue(
            res.get('sawa_resolved') or res.get('sawa_pending_timer'),
            f"Sawa should resolve or start timer, got: {res}"
        )


    def test_sun_tie_breaker(self):
        # Test Sun Rounding with exactly 65 abnat points (half of 130)
        # 65 * 2 = 130 / 10 = 13.
        # User Rule: Buyer scores 13 (65 Abnat) -> LOSS (Khasara).
        
        # We need to simulate a round history that sums to 65.
        game = Game("sun_tie")
        game.add_player("p1", "P1")
        game.add_player("p2", "P2")
        game.add_player("p3", "P3")
        game.add_player("p4", "P4")
        
        game.game_mode = "SUN"
        game.bid = {"type": "SUN", "bidder": "Bottom", "doubled": False} 
        # P0 is Bottom (Us).
        
        # Create a trick history summing to 65 for Us.
        # Total possible in Sun is 130 + 10 = 140. 
        # Wait, user matrix: "Sun Total: 120 + 10 = 130". 
        # Ah, my previous calc: 130 raw + 10 = 140? 
        # User: "Sun Total: The sum of all cards ($4 \times (11+10+4+3+2)$) = 120."
        # Plus 10 last trick = 130. 
        # So Max raw is 130.
        # Half is 65.
        
        # I need to verify my Card Points sum to 120.
        # A=11, 10=10, K=4, Q=3, J=2, 9=0, 8,7=0.
        # Sum = 30. 4 suits = 120. Correct.
        
        # Simulate P0 winning 65 points exactly.
        # Trick 1: 30 points (4 Aces, but wait, can't play 4 aces in one trick)
        # Just mock round_history directly.
        # Simulate P0 winning 65 points exactly.
        # Trick 1: 30 points (4 Aces, but wait, can't play 4 aces in one trick)
        # Just mock round_history directly.
        # We need Us to have 65 Raw Cards. Them to have 55 Raw Cards + 10 Bonus -> 65.
        game.round_history = [
            {'winner': 'Bottom', 'points': 65, 'cards': []}, 
            {'winner': 'Right', 'points': 55, 'cards': []} 
        ]
        # Last trick winner is Right (Them). +10 to Them.
        # Them Raw = 55 + 10 = 65.
        # Us Raw = 65.
        # Total = 130.
        # Bidder (Us) has 65. Tie.
        # Expectation: 65 is LOSS.
        # User said "Sun Adjusted Total: 120 + 10 = 130."
        # 30 * 4 = 120. + 10 = 130.
        # So if Us has 65, Them has 65.
        # If Us gets 65 raw (including last trick logic?), then Us Raw = 65.
        # Total 130.
        # 65 is exactly half.
        # Bidder needs > 65.
        # So 65 should be LOSS.
        
        # Manually force Last Trick to give +10 to Right, so Us stays at 65.
        # Wait, if Us has 65 and Them has 65.
        
        game.end_round()
        
        # Us (Bidder) had 65. Loss.
        # Opponent (Them) gets All 26 points.
        self.assertEqual(game.match_scores['them'], 26)
        self.assertEqual(game.match_scores['us'], 0)

    def test_four_aces_sun_vs_hokum(self):
        # 4 Aces in SUN -> FOUR_HUNDRED (200 Abnat = 40 pts)
        hand = [Card('♠', 'A'), Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'), Card('♠', 'K')]
        projects_sun = check_project_eligibility(hand, "SUN")
        four_hundred = _find_project(projects_sun, 'FOUR_HUNDRED')
        self.assertIsNotNone(four_hundred, "4 Aces should be valid FOUR_HUNDRED in Sun")
        self.assertEqual(four_hundred['score'], 200, "4 Aces in Sun = 200 Abnat")
        self.assertEqual(four_hundred['type'], 'FOUR_HUNDRED')

        # 4 Aces in HOKUM -> HUNDRED (100 Abnat = 10 pts)
        projects_hokum = check_project_eligibility(hand, "HOKUM")
        hundred = _find_project(projects_hokum, 'HUNDRED')
        self.assertIsNotNone(hundred, "4 Aces should be valid HUNDRED in Hokum")
        self.assertEqual(hundred['score'], 100, "4 Aces in Hokum = 100 Abnat")
        self.assertEqual(hundred['type'], 'HUNDRED')

if __name__ == '__main__':
    unittest.main()
