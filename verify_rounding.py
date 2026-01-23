from game_logic import Game
import unittest

class TestScoring(unittest.TestCase):
    def test_hokum_rounding(self):
        # Mock class to access round_score method
        game = Game("test_room")
        game.game_mode = 'HOKUM'
        
        # Test 1.5 -> 1 (Round Down on 5)
        rounded, _ = game.round_score(15)
        self.assertEqual(rounded, 10, "Hokum 15 should round to 10")
        
        # Test 1.6 -> 2 (Round Up on 6)
        rounded, _ = game.round_score(16)
        self.assertEqual(rounded, 20, "Hokum 16 should round to 20")

        # Test 1.4 -> 1 (Round Down)
        rounded, _ = game.round_score(14)
        self.assertEqual(rounded, 10, "Hokum 14 should round to 10")

    def test_sun_rounding(self):
        game = Game("test_room")
        game.game_mode = 'SUN'
        
        # Test 1.5 -> 2 (Round Up on 5)
        rounded, _ = game.round_score(15)
        self.assertEqual(rounded, 20, "Sun 15 should round to 20")
        
        # Test 1.4 -> 1 (Round Down)
        rounded, _ = game.round_score(14)
        self.assertEqual(rounded, 10, "Sun 14 should round to 10")

if __name__ == '__main__':
    unittest.main()
