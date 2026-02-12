
import unittest
from unittest.mock import MagicMock, patch
import time
from game_engine.logic.game import Game
from game_engine.models.constants import GamePhase

class TestQaydStabilization(unittest.TestCase):
    def setUp(self):
        self.game = Game("test_room_qayd")
        # Setup 4 players
        for i in range(4):
            self.game.add_player(f"p{i}", f"Player {i}")
        self.game.start_game()
        
        # Advance to PLAYING
        self.game.handle_bid(self.game.current_turn, "SUN", "SUN") 
        self.game.complete_deal(self.game.bidding_engine.contract.bidder_idx)
        
    def test_qayd_trigger_lock_and_release(self):
        """Test that Qayd locks the game and releases it after cancel/timeout"""
        player_idx = self.game.current_turn
        
        # 1. Trigger Qayd
        print(f"\n[TEST] Triggering Qayd for P{player_idx}")
        res = self.game.handle_qayd_trigger(player_idx)
        self.assertTrue(res['success'], "Qayd trigger failed")
        self.assertTrue(self.game.is_locked, "Game should be locked after Qayd trigger")
        self.assertTrue(self.game.qayd_state['active'], "Qayd state should be active")
        
        # 2. Verify Actions Blocked
        print("[TEST] Attempting to play card while locked...")
        play_res = self.game.play_card(player_idx, 0)
        self.assertFalse(play_res.get('success'), "Should NOT be able to play card while locked")
        
        # 3. Cancel Qayd (Simulate Timeout or Manual Cancel)
        print("[TEST] Cancelling Qayd...")
        cancel_res = self.game.handle_qayd_cancel()
        self.assertTrue(cancel_res['success'], "Cancel should succeed")
        
        # 4. Verify Unlock
        self.assertFalse(self.game.is_locked, "Game should be UNLOCKED after cancel")
        self.assertFalse(self.game.qayd_state['active'], "Qayd state should be inactive")
        self.assertEqual(self.game.phase, GamePhase.PLAYING.value, "Phase should be PLAYING")
        
        # 5. Play should now work
        print("[TEST] Playing card after unlock...")
        play_res_2 = self.game.play_card(player_idx, 0)
        # Note: Play might fail if it's not valid move, but it shouldn't fail due to LOCK
        if not play_res_2.get('success'):
            self.assertNotEqual(play_res_2.get('error'), "Game is locked", "Error should not be lock related")

    def test_zombie_state_prevention(self):
        """Test logic that prevents zombie states (Active Qayd but no Phase change)"""
        # Force a broken state: Active Qayd but Phase is PLAYING
        self.game.qayd_engine.state['active'] = True
        self.game.phase = GamePhase.PLAYING.value
        
        # The 'handle_qayd_cancel' should fix this mismatch
        print("\n[TEST] Forcing Zombie State (Active Qayd + PLAYING Phase)...")
        res = self.game.handle_qayd_cancel()
        
        self.assertFalse(self.game.qayd_engine.state['active'], "Qayd should be deactivated")
        self.assertFalse(self.game.is_locked, "Game should be unlocked")

if __name__ == '__main__':
    unittest.main()
