
import unittest
from unittest.mock import MagicMock
from game_engine.models.card import Card
from ai_worker.bot_context import BotContext
from ai_worker.strategies.playing import PlayingStrategy
from ai_worker.signals.manager import SignalManager
from ai_worker.signals.definitions import SignalType

class TestSignals(unittest.TestCase):
    def setUp(self):
        self.strategy = PlayingStrategy()
        self.ctx = MagicMock(spec=BotContext)
        self.ctx.mode = 'SUN'
        self.ctx.trump = None
        self.ctx.is_master_card = lambda c: c.rank == 'A' # Mock master check

    def test_manager_encourage_logic(self):
        mgr = SignalManager()
        
        # Case 1: Strong Hand (A, K, 10) -> Signal YES
        hand = [Card('♥', 'A'), Card('♥', 'K'), Card('♥', '10')]
        self.assertTrue(mgr.should_signal_encourage(hand, '♥'))
        
        # Case 2: Weak Hand (Q, 9, 7) -> Signal NO
        hand = [Card('♥', 'Q'), Card('♥', '9'), Card('♥', '7')]
        self.assertFalse(mgr.should_signal_encourage(hand, '♥'))
        
        # Case 3: Ace but weak (A, 7) -> Signal NO (Too risky to discard A or 7 isn't a signal)
        hand = [Card('♥', 'A'), Card('♥', '7')]
        # This depends on implementation details. A+7 might not trigger "Ten/King" signal logic.
        self.assertFalse(mgr.should_signal_encourage(hand, '♥'))

    def test_manager_select_signal_card(self):
        mgr = SignalManager()
        
        # Case 1: Standard Strong Hand (A, K, 10) -> Should Prioritize ACE (User Rule: "A means I have the rest")
        # Run: A, 10, K is a solid run.
        hand = [Card('♥', 'A'), Card('♥', 'K'), Card('♥', '10'), Card('♥', '7')]
        sig_card = mgr.get_discard_signal_card(hand, '♥')
        self.assertEqual(sig_card.rank, 'A')
        
        # Case 2: Good Hand but not "The Rest" (A, 10, 8) -> Should Prioritize 10
        # If we discard Ace here, we lose master and might not win tricks.
        # Run check: A, 10... no K, no Q. Not solid.
        hand2 = [Card('♥', 'A'), Card('♥', '10'), Card('♥', '8')]
        sig_card2 = mgr.get_discard_signal_card(hand2, '♥')
        self.assertEqual(sig_card2.rank, '10')

    def test_playing_strategy_emission(self):
        # Setup Context: Void in Spades (Lead), Strong in Hearts.
        # Hand: A H, 10 H, 7 H, 7 D.
        self.ctx.hand = [
            Card('♥', 'A'), 
            Card('♥', '10'), 
            Card('♥', '7'), 
            Card('♦', '7')
        ]
        self.ctx.lead_suit = '♠' # Spades led
        self.ctx.hand_suits = {'♥', '♦'} # No Spades
        
        # Mock _get_trash_card call (simulating void logic inside _play_sun_follow usually calls this)
        # But we can call _get_trash_card directly to test the hook.
        
        decision = self.strategy._get_trash_card(self.ctx)
        
        self.assertEqual(decision['action'], 'PLAY')
        # Expecting index 1 (10 H)
        # Card at 1 is 10 H.
        idx = decision['cardIndex']
        card = self.ctx.hand[idx]
        
        self.assertIn("Collaborative Signal", decision['reasoning'])
        self.assertEqual(card.rank, '10')
        self.assertEqual(card.suit, '♥')

    def test_detection_logic(self):
        # Setup: Bot is Player 0. Partner is Player 2.
        self.ctx.player_index = 0
        
        # Create a mock trick history
        # Trick 1: Lead Spades. Partner discards 10 Hearts (Signal!)
        mock_trick = {
            'leadSuit': '♠',
            'cards': [
                {'suit': '♠', 'rank': '7', 'playerIndex': 1}, # Right (Lead)
                {'suit': '♥', 'rank': '10', 'playerIndex': 2}, # Partner (Discard Signal)
                {'suit': '♠', 'rank': '9', 'playerIndex': 3}, # Left
                {'suit': '♠', 'rank': 'A', 'playerIndex': 0}  # Me (Win?)
            ],
            'winner': 0
        }
        
        self.ctx.raw_state = {'currentRoundTricks': [mock_trick]}
        
        # Test Detection
        signal = self.strategy._check_partner_signals(self.ctx)
        self.assertIsNotNone(signal)
        self.assertEqual(signal['type'], 'ENCOURAGE')
        self.assertEqual(signal['suit'], '♥')
        
    def test_detection_ignore_follow(self):
        # Setup: Partner follows suit (No signal)
        self.ctx.player_index = 0
        mock_trick = {
            'leadSuit': '♠',
            'cards': [
                {'suit': '♠', 'rank': '7', 'playerIndex': 1}, 
                {'suit': '♠', 'rank': '10', 'playerIndex': 2}, # Partner Follows Spades
                {'suit': '♠', 'rank': '9', 'playerIndex': 3}, 
                {'suit': '♠', 'rank': 'A', 'playerIndex': 0} 
            ],
            'winner': 0
        }
        self.ctx.raw_state = {'currentRoundTricks': [mock_trick]}
        
        signal = self.strategy._check_partner_signals(self.ctx)
        self.assertIsNone(signal)

    def test_reaction_to_signal(self):
        # Setup: Signal detected (Hearts), Bot has Hearts.
        # Ensure Bot leads Hearts.
        self.ctx.player_index = 0
        
        # Inject Mock Signal Detection (to avoid setting up full trick history again)
        self.strategy._check_partner_signals = MagicMock(return_value={'type': 'ENCOURAGE', 'suit': '♥'})
        
        # Hand has Hearts
        self.ctx.hand = [Card('♣', '7'), Card('♥', '7')]
        
        decision = self.strategy._get_sun_lead(self.ctx)
        
        self.assertEqual(decision['action'], 'PLAY')
        self.assertIn("Answering Partner", decision['reasoning'])
        self.assertEqual(decision['cardIndex'], 1) # Should pick the Heart (Index 1)

    def test_opposite_color_detection(self):
        # Setup: Partner discards 7 Hearts (Red) -> Signals interest in BLACK suits (Spades/Clubs)
        self.ctx.player_index = 0
        mock_trick = {
            'leadSuit': '♠',
            'cards': [
                {'suit': '♠', 'rank': 'A', 'playerIndex': 1}, # Enemy
                {'suit': '♥', 'rank': '7', 'playerIndex': 2}, # Partner discards 7H (Red Low) -> Signal Black
                {'suit': '♠', 'rank': '9', 'playerIndex': 3}, 
                {'suit': '♠', 'rank': '7', 'playerIndex': 0} 
            ],
            'winner': 0 # Assume we get lead next somehow, or just testing detection logic
        }
        self.ctx.raw_state = {'currentRoundTricks': [mock_trick]}
        
        # 1. Verify Detection
        signal = self.strategy._check_partner_signals(self.ctx)
        self.assertIsNotNone(signal)
        self.assertEqual(signal['type'], 'PREFER_OPPOSITE')
        self.assertIn('♠', signal['suits'])
        self.assertIn('♣', signal['suits'])
        self.assertNotIn('♥', signal['suits'])
        
        # 2. Verify Reaction (Lead)
        # Give bot a good Club (Black) and a good Heart (Red)
        self.ctx.hand = [Card('♣', '10'), Card('♥', 'A')]
        
        # Inject signal mock to persist state for lead check
        self.strategy._check_partner_signals = MagicMock(return_value=signal)
        
        decision = self.strategy._get_sun_lead(self.ctx)
        
        self.assertEqual(decision['action'], 'PLAY')
        self.assertEqual(decision['cardIndex'], 0) # Should pick Club 10 (Black)
        self.assertIn("Prefer Opposite Color", decision['reasoning'])

if __name__ == '__main__':
    unittest.main()
