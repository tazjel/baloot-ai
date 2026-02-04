import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.logic.game import Game
from game_engine.models.constants import GamePhase
from game_engine.logic.phases.challenge_phase import ChallengePhase

class TestQaydPhaseReversion(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room")
        # Mock dependencies to avoid full stack requirement
        self.game.trick_manager = MagicMock()
        self.game.trick_manager.propose_qayd.return_value = {'success': True}
        self.game.trick_manager.cancel_qayd.return_value = {'success': True}
        self.game.trick_manager.qayd_state = {'active': False}
        
        # Ensure ChallengePhase is attached
        self.game.challenge_phase = ChallengePhase(self.game)
        
        # Add a dummy player
        from game_engine.models.player import Player
        p = Player("p0", "P0", 0, self.game)
        self.game.players.append(p)

    def test_revert_to_finished(self):
        """
        Test that cancelling Qayd when game was FINISHED returns to FINISHED, not PLAYING.
        """
        # 1. Simulate Round End
        self.game.phase = GamePhase.FINISHED.value
        print(f"\n[TEST] Initial Phase: {self.game.phase}")
        
        # 2. Trigger Qayd
        print("[TEST] Triggering Qayd...")
        self.game.handle_qayd_trigger(0)
        
        self.assertEqual(self.game.phase, GamePhase.CHALLENGE.value, "Game should be in CHALLENGE phase")
        print(f"[TEST] Phase after Trigger: {self.game.phase}")
        
        # 3. Cancel Qayd
        print("[TEST] Cancelling Qayd...")
        self.game.handle_qayd_cancel()
        
        print(f"[TEST] Phase after Cancel: {self.game.phase}")
        
        # 4. Assert
        self.assertEqual(self.game.phase, GamePhase.FINISHED.value, 
                        f"Game Phase should be FINISHED, but was {self.game.phase}")

if __name__ == '__main__':
    unittest.main()
