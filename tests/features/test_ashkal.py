
import unittest
from game_engine.logic.bidding_engine import BiddingEngine, BiddingPhase, BidType

class MockPlayer:
    def __init__(self, idx, pos, team):
        self.index = idx
        self.position = pos
        self.team = team

class MockCard:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
    def to_dict(self):
        return {'rank': self.rank, 'suit': self.suit}

class TestAshkal(unittest.TestCase):
    def setUp(self):
        self.players = [
            MockPlayer(0, 'Bottom', 'us'),   # Dealer
            MockPlayer(1, 'Right', 'them'),
            MockPlayer(2, 'Top', 'us'),
            MockPlayer(3, 'Left', 'them')
        ]
        # Dealer is 0 (Bottom). Priority: 1, 2, 3, 0
        self.floor_card = MockCard('7', '♠')  # Non-Ace floor card (Ashkal allowed)
        self.engine = BiddingEngine(
            dealer_index=0, floor_card=self.floor_card,
            players=self.players, match_scores={'us': 0, 'them': 0}
        )

    def test_ashkal_valid_dealer(self):
        # Dealer is Index 0, priority queue: [1, 2, 3, 0]
        # current_turn starts at 1. Pass 1, 2, 3 to reach 0's turn.
        self.engine.process_bid(1, 'PASS')
        self.engine.process_bid(2, 'PASS')
        self.engine.process_bid(3, 'PASS')
        # Now it's 0's turn (Dealer)
        res = self.engine.process_bid(0, 'ASHKAL', '♠')
        self.assertTrue(res.get('success'), f"Dealer should be allowed to Ashkal. Error: {res.get('error')}")
        self.assertEqual(self.engine.contract.type, BidType.SUN)
        self.assertTrue(self.engine.contract.is_ashkal)

    def test_ashkal_valid_left_opponent(self):
        # Left of Dealer (0) is Index 3.
        # Priority: [1, 2, 3, 0]. Pass 1 and 2, then 3 can bid.
        self.engine.process_bid(1, 'PASS')
        self.engine.process_bid(2, 'PASS')
        res = self.engine.process_bid(3, 'ASHKAL', '♠')
        self.assertTrue(res.get('success'), f"Left Opponent should be allowed to Ashkal. Error: {res.get('error')}")
        self.assertEqual(self.engine.contract.type, BidType.SUN)
        self.assertTrue(self.engine.contract.is_ashkal)
        
    def test_ashkal_invalid_right_opponent(self):
        # Right of Dealer (0) is Index 1 — NOT eligible for Ashkal.
        res = self.engine.process_bid(1, 'ASHKAL', '♠')
        self.assertIn('error', res)
        self.assertIn('Ashkal', res['error'])

    def test_ashkal_invalid_partner(self):
        # Partner of Dealer (0) is Index 2 — NOT eligible for Ashkal.
        self.engine.process_bid(1, 'PASS')
        res = self.engine.process_bid(2, 'ASHKAL', '♠')
        self.assertIn('error', res)
        self.assertIn('Ashkal', res['error'])

    def test_ashkal_valid_round_2(self):
        # Pass everyone through Round 1, then in Round 2 Dealer can Ashkal
        self.engine.process_bid(1, 'PASS')
        self.engine.process_bid(2, 'PASS')
        self.engine.process_bid(3, 'PASS')
        self.engine.process_bid(0, 'PASS')
        # Should now be Round 2
        self.assertEqual(self.engine.phase, BiddingPhase.ROUND_2)
        
        # 1, 2, 3 pass again, then 0 (Dealer) bids Ashkal
        self.engine.process_bid(1, 'PASS')
        self.engine.process_bid(2, 'PASS')
        self.engine.process_bid(3, 'PASS')
        res = self.engine.process_bid(0, 'ASHKAL', '♠')
        self.assertTrue(res.get('success'), f"Ashkal should be allowed in Round 2. Error: {res.get('error')}")
        self.assertEqual(self.engine.contract.type, BidType.SUN)

if __name__ == '__main__':
    unittest.main()
