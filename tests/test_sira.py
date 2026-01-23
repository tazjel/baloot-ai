
import unittest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_logic import Game, Card, scan_hand_for_projects
# Make sure helper is available or use Game method if wrapper exists.
# scan_hand_for_projects is standalone in game_logic.py

class TestSiraLogic(unittest.TestCase):
    def test_sequence_7_cards(self):
        """Test a sequence of 7 cards (A..8) is identified as HUNDRED, not 7 Siras."""
        # 7 Cards: A, K, Q, J, 10, 9, 8
        hand = [
            Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), Card('♠', 'J'),
            Card('♠', '10'), Card('♠', '9'), Card('♠', '8')
        ]
        
        projects = scan_hand_for_projects(hand, 'SUN')
        print(f"Projects found: {projects}")
        
        # Should be ONE project of type HUNDRED
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]['type'], 'HUNDRED')
        self.assertEqual(len(projects[0]['cards']), 7)
        
    def test_sequence_broken(self):
        """Test A, K, Q (Sira) and 10, 9, 8 (Sira) - broken by Jack missing"""
        hand = [
            Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'),
            Card('♠', '10'), Card('♠', '9'), Card('♠', '8')
        ]
        
        projects = scan_hand_for_projects(hand, 'SUN')
        print(f"Projects found (broken): {projects}")
        
        # Should be TWO Siras
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]['type'], 'SIRA')
        self.assertEqual(projects[1]['type'], 'SIRA')

if __name__ == '__main__':
    unittest.main()
