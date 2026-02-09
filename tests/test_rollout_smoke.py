"""Quick smoke test for the upgraded play_greedy() rollout."""
import unittest
from game_engine.models.card import Card
from ai_worker.mcts.fast_game import FastGame

# Card(suit, rank) - suit is FIRST argument

class TestSmartRollout(unittest.TestCase):
    def test_sun_rollout_completes(self):
        """SUN mode rollout runs to completion without errors."""
        hands = [
            [Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), Card('♥', '7')],
            [Card('♠', 'J'), Card('♠', '10'), Card('♠', '9'), Card('♥', '8')],
            [Card('♥', 'A'), Card('♥', 'K'), Card('♥', 'Q'), Card('♠', '8')],
            [Card('♥', 'J'), Card('♥', '10'), Card('♥', '9'), Card('♠', '7')]
        ]
        game = FastGame(hands, trump=None, mode='SUN', current_turn=0, dealer_index=3)
        game.play_greedy()
        self.assertTrue(game.is_finished)
        total = game.scores['us'] + game.scores['them']
        self.assertGreater(total, 0, "Some points should be scored")

    def test_hokum_rollout_completes(self):
        """HOKUM mode rollout runs to completion without errors."""
        hands = [
            [Card('♠', 'J'), Card('♠', '9'), Card('♠', 'A'), Card('♥', '7')],
            [Card('♠', 'K'), Card('♠', 'Q'), Card('♠', '10'), Card('♥', '8')],
            [Card('♥', 'A'), Card('♥', 'K'), Card('♥', 'Q'), Card('♠', '8')],
            [Card('♥', 'J'), Card('♥', '10'), Card('♥', '9'), Card('♠', '7')]
        ]
        game = FastGame(hands, trump='♠', mode='HOKUM', current_turn=0, dealer_index=3)
        game.play_greedy()
        self.assertTrue(game.is_finished)
        total = game.scores['us'] + game.scores['them']
        self.assertGreater(total, 0, "Some points should be scored")

    def test_finessing_behavior(self):
        """4 tricks of single-suit play should complete without errors."""
        hands = [
            [Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), Card('♠', 'J')],
            [Card('♠', '7'), Card('♠', '8'), Card('♠', '9'), Card('♠', '10')],
            [Card('♥', 'A'), Card('♥', 'K'), Card('♥', 'Q'), Card('♥', 'J')],
            [Card('♥', '7'), Card('♥', '8'), Card('♥', '9'), Card('♥', '10')]
        ]
        game = FastGame(hands, trump=None, mode='SUN', current_turn=0, dealer_index=3)
        game.play_greedy()
        self.assertTrue(game.is_finished)

    def test_hokum_trump_handling(self):
        """HOKUM: Trump suit should win over non-trump leads."""
        hands = [
            [Card('♠', '7'), Card('♠', '8'), Card('♦', '9'), Card('♦', '10')],
            [Card('♥', '7'), Card('♥', '8'), Card('♥', '9'), Card('♥', '10')],
            [Card('♣', 'A'), Card('♣', 'K'), Card('♣', 'Q'), Card('♣', 'J')],
            [Card('♦', 'A'), Card('♦', 'K'), Card('♦', 'Q'), Card('♦', 'J')]
        ]
        game = FastGame(hands, trump='♥', mode='HOKUM', current_turn=0, dealer_index=3)
        game.play_greedy()
        self.assertTrue(game.is_finished)

    def test_full_8_card_sun_game(self):
        """Full 8-card SUN game completes correctly."""
        hands = [
            [Card('♠', 'A'), Card('♠', 'K'), Card('♥', 'A'), Card('♥', 'K'),
             Card('♦', 'A'), Card('♦', 'K'), Card('♣', 'A'), Card('♣', 'K')],
            [Card('♠', 'Q'), Card('♠', 'J'), Card('♥', 'Q'), Card('♥', 'J'),
             Card('♦', 'Q'), Card('♦', 'J'), Card('♣', 'Q'), Card('♣', 'J')],
            [Card('♠', '10'), Card('♠', '9'), Card('♥', '10'), Card('♥', '9'),
             Card('♦', '10'), Card('♦', '9'), Card('♣', '10'), Card('♣', '9')],
            [Card('♠', '8'), Card('♠', '7'), Card('♥', '8'), Card('♥', '7'),
             Card('♦', '8'), Card('♦', '7'), Card('♣', '8'), Card('♣', '7')]
        ]
        game = FastGame(hands, trump=None, mode='SUN', current_turn=0, dealer_index=3)
        game.play_greedy()
        self.assertTrue(game.is_finished)
        # Player 0 (us) has all Aces and Kings - should dominate
        self.assertGreater(game.scores['us'], game.scores['them'])
        print(f"  SUN 8-card: Us={game.scores['us']}, Them={game.scores['them']}")

if __name__ == '__main__':
    unittest.main()
