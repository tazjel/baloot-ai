"""
Reproduction Script: User Revokes and Gets Rewarded (Bug)

This script simulates the exact scenario the user reported:
1. User (Bottom, 'us' team) plays an illegal card (revokes)
2. Someone triggers Qayd
3. Qayd is confirmed
4. Expected: Us=0, Them=26
5. Actual (per user): Us=26, Them=0
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from game_engine.game import Game
from game_engine.models.card import Card
import unittest

class TestQaydUserRevoke(unittest.TestCase):
    def test_user_revoke_penalty(self):
        """Test that when Bottom (us) revokes, they get penalized (0 points), opponent gets 26."""
        game = Game(room_id="test_user_revoke")
        
        # Add 4 players
        for i in range(4):
            game.add_player(f"p{i}", f"Player{i}")
        
        # Start game
        game.start_game()
        
        # Force SUN mode
        game.game_mode = "SUN"
        game.bid = {'type': 'SUN', 'bidder': 'Bottom'}
        
        # Bottom is index 0, team 'us'
        bottom = game.players[0]
        right = game.players[1]
        
        # Clear hands for this test
        bottom.hand = [
            Card('Hearts', 'A'),  # Has Hearts
            Card('Spades', '7')
        ]
        right.hand = [Card('Hearts', 'K')]
        
        # Bottom leads with Hearts A
        game.current_turn = 0
        game.play_card(0, 0)  # Bottom plays Hearts A
        
        # Right plays Hearts K (legal)
        game.current_turn = 1
        game.play_card(1, 0)
        
        # Now Bottom plays again (trick continues)
        # Bottom should follow suit but doesn't (revokes)
        # Wait, this scenario doesn't make sense for a single trick.
        
        # Let me create a proper revoke scenario:
        # 1. Right leads Hearts
        # 2. Bottom has Hearts but plays Spades (illegal)
        
        # Reset
        game.table_cards = []
        game.current_turn = 1
        
        # Right leads Hearts K
        right.hand = [Card('Hearts', 'K')]
        game.play_card(1, 0)
        
        # Bottom has Hearts but plays Spades (REVOKE)
        game.current_turn = 0
        bottom.hand = [Card('Hearts', 'A'), Card('Spades', '7')]
        game.play_card(0, 1, metadata={'cardId': 'S7'})  # Plays Spades (illegal)
        
        # Check if Referee flagged it
        last_play = game.table_cards[-1]
        is_illegal = last_play.get('metadata', {}).get('is_illegal', False)
        print(f"[TEST] Bottom's Spades play flagged as illegal: {is_illegal}")
        
        # Trigger Qayd
        print(f"[TEST] Triggering Qayd...")
        result = game.trick_manager.propose_qayd(
            reporter_index=1,  # Right reports
            crime_card={'suit': 'Spades', 'rank': '7'},
            proof_card={'suit': 'Hearts', 'rank': 'A'},
            qayd_type='REVOKE'
        )
        
        print(f"[TEST] Qayd State: {game.trick_manager.qayd_state}")
        print(f"[TEST] Loser Team: {game.trick_manager.qayd_state.get('loser_team')}")
        print(f"[TEST] Penalty Points: {game.trick_manager.qayd_state.get('penalty_points')}")
        
        # Confirm Qayd
        game.trick_manager.confirm_qayd()
        
        # Check past_round_results
        if game.past_round_results:
            latest = game.past_round_results[-1]
            print(f"\n[TEST] Round Result:")
            print(f"  Us: {latest['us']['result']}")
            print(f"  Them: {latest['them']['result']}")
            print(f"  Winner: {latest['winner']}")
            print(f"  Reason: {latest['reason']}")
            
            # Assert correct scoring
            self.assertEqual(latest['us']['result'], 0, "Bottom (us) should get 0 for revoking")
            self.assertEqual(latest['them']['result'], 26, "Opponent (them) should get 26")
            self.assertEqual(latest['winner'], 'them', "Winner should be 'them'")
        else:
            self.fail("No round results found")

if __name__ == '__main__':
    unittest.main()
