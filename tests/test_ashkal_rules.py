
import unittest
from game_engine.logic.bidding_engine import BiddingEngine
from game_engine.models.constants import BiddingPhase, BidType

class MockPlayer:
    def __init__(self, idx, pos, team):
        self.index = idx
        self.position = pos
        self.team = team
        self.hand = [] # Needed for Kawesh checks potentially

class MockCard:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
    def to_dict(self):
        return {'rank': self.rank, 'suit': self.suit}

class TestAshkalRules(unittest.TestCase):
    def setUp(self):
        # Dealer = 0 (Bottom) -> Turn Order: Right(1), Top(2), Left(3), Bottom(0)
        self.players = [
            MockPlayer(0, 'Bottom', 'us'),
            MockPlayer(1, 'Right', 'them'),
            MockPlayer(2, 'Top', 'us'),
            MockPlayer(3, 'Left', 'them')
        ]
        self.floor_not_ace = MockCard('7', '♥')
        self.floor_ace = MockCard('A', '♥')
        
    def test_ashkal_eligibility_round_1(self):
        """Test Ashkal in Round 1. Only Dealer(0) and Left(3) eligible."""
        dealer_idx = 0
        engine = BiddingEngine(dealer_idx, self.floor_not_ace, self.players, {'us':0, 'them':0})
        
        # 1. Right (1) [Prio 0] - Cannot Ashkal
        res = engine.process_bid(1, 'ASHKAL')
        self.assertFalse(res.get('success'), "Right Opponent (1) should NOT be eligible")
        engine.process_bid(1, 'PASS') # Pass to move turn
        
        # 2. Top (2) [Partner, Prio 1] - Cannot Ashkal
        res = engine.process_bid(2, 'ASHKAL')
        self.assertFalse(res.get('success'), "Partner (2) should NOT be eligible")
        engine.process_bid(2, 'PASS') # Pass
        
        # 3. Left (3) [Prio 2] - ELIGIBLE
        # Since 0 and 1 passed, Prio 2 is highest available. Should finalize immediately?
        res = engine.process_bid(3, 'ASHKAL')
        self.assertTrue(res.get('success'), f"Left (3) should be eligible. Err: {res.get('error')}")
        self.assertEqual(engine.contract.is_ashkal, True)
        self.assertEqual(engine.contract.type, BidType.SUN)
        self.assertEqual(engine.contract.bidder_idx, 1) # Partner of 3 is 1 (Right)
        
    def test_ashkal_dealer_eligibility(self):
        """Test Dealer (0) Ashkal Eligibility"""
        engine = BiddingEngine(0, self.floor_not_ace, self.players, {'us':0, 'them':0})
        # Reset turns by passing everyone up to Dealer
        engine.process_bid(1, 'PASS')
        engine.process_bid(2, 'PASS')
        engine.process_bid(3, 'PASS')
        
        # Dealer (0) [Prio 3]
        res = engine.process_bid(0, 'ASHKAL')
        self.assertTrue(res.get('success'))
        self.assertEqual(engine.contract.is_ashkal, True)
        self.assertEqual(engine.contract.bidder_idx, 2) # Partner of 0 is 2 (Top)

    def test_ashkal_round_2(self):
        """Test Ashkal in Round 2"""
        engine = BiddingEngine(0, self.floor_not_ace, self.players, {'us':0, 'them':0})
        # Round 1 Passes
        engine.process_bid(1, 'PASS')
        engine.process_bid(2, 'PASS')
        engine.process_bid(3, 'PASS')
        engine.process_bid(0, 'PASS')
        
        self.assertEqual(engine.phase, BiddingPhase.ROUND_2)
        
        # Round 2: Right(1) passes
        engine.process_bid(1, 'PASS')
        
        # Partner(2) passes
        engine.process_bid(2, 'PASS')
        
        # Left(3) calls Ashkal in R2
        res = engine.process_bid(3, 'ASHKAL')
        self.assertTrue(res.get('success'), "Ashkal should be allowed in Round 2")
        self.assertEqual(engine.contract.is_ashkal, True)
        self.assertEqual(engine.contract.type, BidType.SUN)

    def test_ashkal_ace_constraint(self):
        """Cannot call Ashkal if floor is Ace"""
        engine = BiddingEngine(0, self.floor_ace, self.players, {'us':0, 'them':0})
        engine.process_bid(1, 'PASS')
        engine.process_bid(2, 'PASS')
        
        res = engine.process_bid(3, 'ASHKAL')
        self.assertFalse(res.get('success'))
        self.assertIn("Ace", res.get('error', ''))

if __name__ == '__main__':
    unittest.main()
