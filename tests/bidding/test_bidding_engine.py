
import unittest
import time
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

class TestBiddingEngine(unittest.TestCase):
    def setUp(self):
        self.players = [
            MockPlayer(0, 'Bottom', 'us'),
            MockPlayer(1, 'Right', 'them'),
            MockPlayer(2, 'Top', 'us'),
            MockPlayer(3, 'Left', 'them')
        ]
        # Dealer is 3 (Left). Prio: 0, 1, 2, 3
        self.floor_card = MockCard('7', '♥')
        self.floor_card = MockCard('7', '♥')
        self.engine = BiddingEngine(dealer_index=3, floor_card=self.floor_card, players=self.players, match_scores={'us': 0, 'them': 0})

    def test_sun_firewall_rule(self):
        # Case A: Scores satisfy firewall (Us=120, Them=50)
        # Testing Sun Bid by Us (0), Double by Them (1)
        # Bidder > 100, Doubler < 100 -> OK
        scores_valid = {'us': 120, 'them': 50}
        engine = BiddingEngine(dealer_index=3, floor_card=self.floor_card, players=self.players, match_scores=scores_valid)
        
        engine.process_bid(0, "SUN", None) 
        engine._finalize_auction() # Force to Doubling Phase

        res = engine.process_bid(1, "DOUBLE", "OPEN") # Variant ignored for Sun but okay
        self.assertTrue(res.get('success'), f"Double Allowed. Msg: {res.get('error')}")
        self.assertEqual(engine.contract.level, 2)
        
        # Case B: Scores FAIL firewall (Us=80, Them=50) -> Bidder too low
        scores_invalid = {'us': 80, 'them': 50}
        engine_fail = BiddingEngine(dealer_index=3, floor_card=self.floor_card, players=self.players, match_scores=scores_invalid)
        
        engine_fail.process_bid(0, "SUN", None)
        engine_fail._finalize_auction()

        res_fail = engine_fail.process_bid(1, "DOUBLE", None)
        self.assertIn("error", res_fail)
        self.assertIn("Firewall Active", res_fail['error'])
        self.assertEqual(engine_fail.contract.level, 1, "Double rejected")

    def test_priority_queue(self):
        self.assertEqual(self.engine.priority_queue, [0, 1, 2, 3])

    def test_sun_hijack_with_priority(self):
        # 0 Passes
        self.engine.process_bid(0, 'PASS')
        
        # 1 Bids Hokum
        res = self.engine.process_bid(1, 'HOKUM', '♥')
        self.assertTrue(res['success'])
        self.assertEqual(self.engine.contract.type, BidType.HOKUM)
        self.assertEqual(self.engine.contract.bidder_idx, 1)

        # 2 Bids Sun
        # Priority Queue: [0, 1, 2, 3]. 
        # 1 (Current Contract) is higher priority than 2.
        # So when 2 bids, it should trigger Gablak Window for 1.
        
        res = self.engine.process_bid(2, 'SUN')
        self.assertTrue(res['success'])
        self.assertEqual(res.get('status'), 'GABLAK_TRIGGERED')
        
        # Now 1 must decide. 
        # If 1 Passes (Waives hijack right)
        res = self.engine.process_bid(1, 'PASS')
        self.assertEqual(res.get('status'), 'WAIVED_GABLAK')
        
        # To simulate timeout in test: modify gablak_timer_start locally
        self.engine.gablak_timer_start -= 10 # Force timeout
        
        # Retry finalizing (Any action triggers check? Or separate 'poll' endpoint? logic calls process_bid)
        # Assuming UI would invoke a check or next polling call updates state.
        # Using process_bid again with ANY valid action from ANYONE usually triggers timeout check first.
        # Let's say 2 (who is eager) clicks Sun again?
        res = self.engine.process_bid(2, 'SUN')
        self.assertEqual(res.get('status'), 'GABLAK_TIMEOUT')
        
        # NOW check if contract updated
        self.assertEqual(self.engine.contract.type, BidType.SUN, "Contract should update to Sun after timeout")
        self.assertEqual(self.engine.contract.bidder_idx, 2)
        self.assertEqual(self.engine.phase, BiddingPhase.DOUBLING)

    def test_gablak_interrupt(self):
        # Reset Engine
        self.engine = BiddingEngine(dealer_index=3, floor_card=self.floor_card, players=self.players, match_scores={'us': 0, 'them': 0})
        
        # 0 Passes.
        res = self.engine.process_bid(0, 'PASS')
        self.assertTrue(res['success'])
        
        # Turn is now 1.
        # 2 tries to bid. (Strict turn order says "Not your turn").
        res = self.engine.process_bid(2, 'HOKUM', '♥')
        self.assertEqual(res.get('error'), 'Not your turn', "Strict turn order should block P2 if P1 hasn't acted")

    def test_doubling_chain(self):
        # Setup specific scores to allow Sun Doubling (Firewall: Bidder > 100, Doubler < 100)
        self.engine.match_scores = {'us': 120, 'them': 50} 

        # 0 Bids Sun
        self.engine.process_bid(0, 'SUN')
        self.assertEqual(self.engine.phase, BiddingPhase.DOUBLING)
        
        # 1 (Opponent) Doubles
        res = self.engine.process_bid(1, 'DOUBLE')
        self.assertEqual(self.engine.contract.level, 2)
        
        # 2 (Partner of Taker) Triples
        res = self.engine.process_bid(2, 'TRIPLE')
        self.assertEqual(self.engine.contract.level, 3)
        
        # 3 (Opponent) Fours
        res = self.engine.process_bid(3, 'FOUR')
        self.assertEqual(self.engine.contract.level, 4)
        
        # 0 (Taker) Gahwa
        res = self.engine.process_bid(0, 'GAHWA')
        self.assertEqual(self.engine.contract.level, 100)

if __name__ == '__main__':
    unittest.main()
