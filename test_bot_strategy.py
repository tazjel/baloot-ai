
import unittest
from bot_agent import BotAgent, BotContext
from game_engine.models.card import Card
from game_engine.models.constants import SUITS

# SUITS = ['♠', '♥', '♦', '♣']
S, H, D, C = SUITS

class TestBotRefactor(unittest.TestCase):
    def test_calculate_sun_strength(self):
        bot = BotAgent()
        # Hand: A, 10, K, Q (Strong Sun)
        hand = [
            Card(S, 'A'), Card(S, '10'), Card(S, 'K'), Card(S, 'Q'),
            Card(H, '7'), Card(D, '8'), Card(C, '9'), Card(C, 'J')
        ]
        
        score = bot.calculate_sun_strength(hand)
        print(f"Sun Score: {score}")
        # Base: A(10)+10(5)+K(3)+Q(2) = 20.
        # Long Suit (S): 4 cards. (4-3)*2 = +2.
        # Total: 22.
        self.assertGreater(score, 20)

    def test_calculate_hokum_strength(self):
        bot = BotAgent()
        # Hand: J, 9, 7 of Trump (S)
        hand = [
            Card(S, 'J'), Card(S, '9'), Card(S, '7'),
            Card(H, 'A'), Card(D, 'K')
        ]
        score = bot.calculate_hokum_strength(hand, S)
        print(f"Hokum Score: {score}")
        
        # Base: J(12) + 9(10) + 7(1) = 23.
        # Non-Trump: A(5) + K(1) = 6.
        # Trump Count (3) * 2 = 6.
        # Dist: H(1)->+1, D(1)->+1, C(0)->+3. Total +5.
        # Grand Total: 23+6+6+5 = 40.
        
        self.assertEqual(score, 40)

    def test_bot_context_init(self):
        game_state = {
            'phase': 'BIDDING',
            'gameMode': 'SUN',
            'trumpSuit': None,
            'dealerIndex': 0,
            'biddingRound': 1,
            'floorCard': {'suit': H, 'rank': 'A'},
            'tableCards': [],
            'players': [
                {'hand': [{'suit': S, 'rank': 'A'}], 'position': 'Bottom', 'name': 'P1', 'team': 'us'},
                {'hand': [], 'position': 'Right', 'name': 'P2', 'team': 'them'},
                {'hand': [], 'position': 'Top', 'name': 'P3', 'team': 'us'},
                {'hand': [], 'position': 'Left', 'name': 'P4', 'team': 'them'},
            ]
        }
        ctx = BotContext(game_state, 0)
        self.assertEqual(len(ctx.hand), 1)
        self.assertEqual(ctx.hand[0].rank, 'A')
        self.assertEqual(ctx.floor_card.suit, H)
        self.assertTrue(ctx.is_dealer)

    def test_playing_decision_with_declaration(self):
        bot = BotAgent()
        # Hand with Project: K, Q, J of Hearts (Sira)
        hand = [
            {'suit': H, 'rank': 'K'}, {'suit': H, 'rank': 'Q'}, {'suit': H, 'rank': 'J'},
            {'suit': S, 'rank': '7'}
        ]
        
        game_state = {
            'phase': 'PLAYING',
            'gameMode': 'SUN',
            'trumpSuit': None,
            'dealerIndex': 0,
            'currentRoundTricks': [], # Trick 1
            'tableCards': [],
            'players': [
                {'hand': hand, 'position': 'Bottom', 'name': 'P1', 'team': 'us', 'index': 0},
                {'hand': [], 'position': 'Right', 'name': 'P2', 'team': 'them', 'index': 1},
                {'hand': [], 'position': 'Top', 'name': 'P3', 'team': 'us', 'index': 2},
                {'hand': [], 'position': 'Left', 'name': 'P4', 'team': 'them', 'index': 3},
            ]
        }
        
        # Mock memory sync? 
        # bot.sync_memory handles failures gracefully?
        # It relies on game_state props.
        
        decision = bot.get_playing_decision(game_state, game_state['players'][0])
        print(f"Playing Decision: {decision}")
        
        self.assertEqual(decision['action'], 'PLAY')
        # Check declaration
        self.assertIn('declarations', decision)
        # Verify it found the Sira
        # Expected project: {'type': 'SIRA', 'suit': H, 'master': 'K'} (approx)
        self.assertTrue(len(decision['declarations']) > 0)

if __name__ == '__main__':
    unittest.main()
