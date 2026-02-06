import unittest
from unittest.mock import MagicMock
from ai_worker.strategies.sherlock import SherlockStrategy

class TestSherlockStrategy(unittest.TestCase):
    def test_sherlock_init(self):
        agent = MagicMock()
        sherlock = SherlockStrategy(agent)
        self.assertIsNotNone(sherlock)
        self.assertFalse(sherlock.pending_qayd_trigger)

    def test_check_crime_logic(self):
        agent = MagicMock()
        sherlock = SherlockStrategy(agent)
        
        # Mock Context
        ctx = MagicMock()
        ctx.team = 'us'
        ctx.position = 'Bottom'
        ctx.players_team_map = {'Right': 'them'}
        
        # Mock Memory Contradiction
        ctx.memory.check_contradiction.return_value = "Must Follow Suit"
        
        # Test Case: Enemy plays contradicting card
        card = {'suit': 'S', 'rank': 'A'}
        result = sherlock._check_crime_logic(ctx, card, 'Right', "Table")
        
        self.assertEqual(result, "QAYD_TRIGGER")
        
    def test_check_crime_logic_omerta(self):
        """Team Loyalty Check"""
        agent = MagicMock()
        sherlock = SherlockStrategy(agent)
        
        ctx = MagicMock()
        ctx.team = 'us'
        ctx.players_team_map = {'Top': 'us'} # Partner
        
        ctx.memory.check_contradiction.return_value = "Must Follow Suit"
        
        # Test Case: Partner plays contradicting card -> Ignore
        card = {'suit': 'S', 'rank': 'A'}
        result = sherlock._check_crime_logic(ctx, card, 'Top', "Table")
        
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
