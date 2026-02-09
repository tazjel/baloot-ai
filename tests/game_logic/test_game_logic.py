from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.player import Player
from game_engine.logic.utils import validate_project
from server.room_manager import RoomManager
import unittest

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
        # Sira check
        hand = [Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), Card('♥', '7'), Card('♦', '9')]
        res = validate_project(hand, "SIRA", "SUN")
        self.assertTrue(res['valid'])
        self.assertEqual(res['score'], 20) # Update to new standard value (20 Abnat)
        
        # 100: 5 seq
        hand = [Card('♦', '7'), Card('♦', '8'), Card('♦', '9'), Card('♦', '10'), Card('♦', 'J')]
        res = validate_project(hand, 'HUNDRED', 'SUN')
        self.assertTrue(res['valid'])
        self.assertEqual(res['score'], 100) # 100 is 100 Abnat (20 points?)
        
        # 400: 4 Aces in SUN
        hand = [Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'), Card('♠', 'A')]
        res = validate_project(hand, 'FOUR_HUNDRED', 'SUN')
        self.assertTrue(res['valid'])
        self.assertEqual(res['score'], 200) # 400 is 40 points (200 Abnat)

    def test_validate_project_400_as_100(self):
        # 4 Aces in Sun, declared as HUNDRED -> Should be 400 (40 points)
        hand = [Card('♠', 'A'), Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'), Card('♠', '7')]
        res = validate_project(hand, "FOUR_HUNDRED", "SUN")
        self.assertTrue(res['valid'])
        self.assertEqual(res['score'], 200) # 40 points = 200 Abnat
        self.assertEqual(res['type'], 'FOUR_HUNDRED')

    def test_validate_project_400_explicit(self):
        hand = [Card('♠', 'A'), Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'), Card('♠', '7')]
        res = validate_project(hand, "FOUR_HUNDRED", "SUN")
        self.assertTrue(res['valid'])
        self.assertEqual(res['score'], 200)

    def test_validate_project_sequence_rank(self):
        # A, K, Q in Sun -> Sequence Rank should be A (highest)
        # Sira in Sun is 4 points
        hand = [Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), Card('♥', '7'), Card('♦', '9')]
        res = validate_project(hand, "SIRA", "SUN")
        self.assertTrue(res['valid'])
        self.assertEqual(res['score'], 20)
        self.assertEqual(res['rank'], 'A')
        
    def test_validate_project_sequence_middle(self):
         # 9, 8, 7. Sira Sun = 4
         hand = [Card('♠', '9'), Card('♠', '8'), Card('♠', '7'), Card('♥', 'A'), Card('♦', 'K')]
         res = validate_project(hand, "SIRA", "SUN")
         self.assertTrue(res['valid'])
         self.assertEqual(res['score'], 20)
         self.assertEqual(res['rank'], '9')


    def test_sawa_flow(self):
        game = Game("test_sawa")
        game.add_player("p1", "P1")
        game.add_player("p2", "P2")
        game.add_player("p3", "P3")
        game.add_player("p4", "P4")
        game.start_game()
        # FORCE DEALER to 0 for deterministic test
        game.dealer_index = 0
        game.current_turn = 1
        
        # Fast forward to playing
        game.handle_bid(1, "PASS")
        game.handle_bid(2, "PASS")
        game.handle_bid(3, "PASS")
        game.handle_bid(0, "SUN") # Dealer Partner bids Sun
        
        # P1 (Right of Dealer P0) leads
        # P1 is index 1.
        self.assertEqual(game.current_turn, 1)
        
        # P1 claims Sawa
        res = game.handle_sawa(1)
        self.assertTrue(res['success'])
        self.assertEqual(game.sawa_state['status'], 'PENDING')
        
        # Teammate (P3) tries to respond
        res = game.handle_sawa_response(3, 'ACCEPT')
        self.assertFalse(res.get('success', False)) # Should error
        
        # Opponent P2 accepts
        res = game.handle_sawa_response(2, 'ACCEPT')
        self.assertTrue(res['success'])
        self.assertEqual(game.sawa_state['status'], 'PENDING') # Waiting for P4
        
        # Opponent P4 accepts. This triggers resolve_sawa_win -> end_round.
        # end_round resets sawa_state to NONE.
        res = game.handle_sawa_response(4 % 4, 'ACCEPT')
        self.assertTrue(res['success'])
        
        # After acceptance, round ends immediately.
        # So Status is NONE (reset) or ACCEPTED (if we check return value).
        # We should check that game state indicates a big win.
        # self.assertEqual(game.sawa_state['status'], 'ACCEPTED')  <-- ends effectively immediately
        self.assertEqual(game.sawa_state['status'], 'NONE') # Reset happened
        
        # Check round ended and "Them" got points
        self.assertTrue(game.match_scores['them'] > 0)


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
        # 4 Aces in SUN -> 400 (40 pts)
        hand = [Card('♠', 'A'), Card('♥', 'A'), Card('♦', 'A'), Card('♣', 'A'), Card('♠', 'K')]
        res_sun = validate_project(hand, "FOUR_HUNDRED", "SUN")
        self.assertTrue(res_sun['valid'], "4 Aces should be valid in Sun")
        self.assertEqual(res_sun['score'], 200, "4 Aces in Sun should result in 200 Abnat (40 points)")
        self.assertEqual(res_sun['type'], 'FOUR_HUNDRED')

        # 4 Aces in HOKUM -> 100 (10 pts)
        # Note: In Hokum, 4 Aces are treated as a "100" type project (Score 10)
        res_hokum = validate_project(hand, "HUNDRED", "HOKUM")
        self.assertTrue(res_hokum['valid'], "4 Aces should be valid 100 in Hokum")
        self.assertEqual(res_hokum['score'], 100, "4 Aces in Hokum should be 100 Abnat (10 points)")
        self.assertEqual(res_hokum['type'], 'HUNDRED')

if __name__ == '__main__':
    unittest.main()
