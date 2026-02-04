import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.logic.game import Game
from game_engine.models.constants import GamePhase
from game_engine.logic.phases.challenge_phase import ChallengePhase
from game_engine.logic.trick_manager import TrickManager
from game_engine.models.player import Player

class TestQaydScore(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room_score")
        
        # Setup Players
        self.game.players = []
        for i in range(4):
            p = Player(f"p{i}", f"P{i}", i, self.game)
            # Team: Bottom(0)/Top(2) = 'us', Right(1)/Left(3) = 'them'
            self.game.players.append(p)
            
        self.game.trick_manager = TrickManager(self.game)
        self.game.challenge_phase = ChallengePhase(self.game)
        
        # Setup Game Mode
        self.game.game_mode = 'SUN'
        self.game.bid = {'type': 'SUN'}
        self.game.match_scores = {'us': 0, 'them': 0}
        self.game.past_round_results = []

    def test_self_report_score(self):
        """
        Test: User (Bottom, 'us') triggers Qayd with NO crime found (False Accusation / Self-Report?).
        Expectation: 'us' is the LOSER. 'them' gets 26 points.
        """
        reporter_idx = 0 # Bottom (Us)
        
        # 1. Trigger Qayd (No crime on table)
        print(f"\n[TEST] Triggering Qayd by {self.game.players[reporter_idx].position} ('us')...")
        self.game.trick_manager.propose_qayd(reporter_idx)
        
        qayd_state = self.game.trick_manager.qayd_state
        print(f"[TEST] Verdict: {qayd_state.get('verdict')}")
        print(f"[TEST] Loser Team: {qayd_state.get('loser_team')}")
        
        # 2. Confirm Qayd
        print("[TEST] Confirming Qayd...")
        self.game.challenge_phase.resolve_verdict()
        
        # 3. Check Scores
        scores = self.game.match_scores
        print(f"[TEST] Finals Scores -> US: {scores['us']}, THEM: {scores['them']}")
        
        # Expectation: US (Reporter) made False Accusation -> US Loses -> THEM gets 26.
        self.assertEqual(scores['them'], 26, "Opponent should get 26 points")
        self.assertEqual(scores['us'], 0, "Reporter (Us) should get 0 points")

if __name__ == '__main__':
    unittest.main()
