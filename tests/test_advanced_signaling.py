import unittest
from ai_worker.signals.manager import SignalManager
from ai_worker.signals.definitions import SignalType
from ai_worker.strategies.playing import PlayingStrategy
from ai_worker.bot_context import BotContext
from game_engine.models.card import Card

# Mock Context and Card helpers
def create_card(rank, suit):
    return Card(suit, rank)

class TestAdvancedSignaling(unittest.TestCase):
    def setUp(self):
        self.mgr = SignalManager()
        self.strategy = PlayingStrategy()

    def test_tahreeb_negative_signal_partner_winning(self):
        """
        Tahreeb: Partner is winning.
        Condition: Bot discards a card.
        Expectation: NEGATIVE Signal (Don't want) -> Implies PREFER_SAME_COLOR.
        """
        # Scenario: Partner plays Play Ace of Hearts (Winner).
        # Bot discards 7 of Spades.
        # Logic: Bot does NOT want Spades.
        # Inference: Bot likely wants CLUBS (Same Color = Black).
        
        card = create_card('7', '♠')
        is_partner_winning = True
        
        signal = self.mgr.get_signal_for_card(card, is_partner_winning)
        self.assertEqual(signal, SignalType.NEGATIVE_DISCARD)
        
    def test_tanfeer_positive_signal_enemy_winning(self):
        """
        Tanfeer: Enemy is winning.
        Condition: Bot discards a high card.
        Expectation: POSITIVE Signal (Encourage).
        """
        # Scenario: Enemy plays Ace of Hearts (Winner).
        # Bot discards 10 of Spades (Strong Call).
        # Logic: Bot WANTS Spades.
        
        card = create_card('10', '♠')
        is_partner_winning = False # Enemy winning
        
        signal = self.mgr.get_signal_for_card(card, is_partner_winning)
        self.assertEqual(signal, SignalType.ENCOURAGE)

    def test_barqiya_urgency_signal(self):
        """
        Barqiya: Enemy is winning (usually).
        Condition: Bot discards ACE.
        Expectation: URGENT_CALL.
        """
        card = create_card('A', '♠')
        is_partner_winning = False
        
        signal = self.mgr.get_signal_for_card(card, is_partner_winning)
        self.assertEqual(signal, SignalType.URGENT_CALL)

    def test_playing_strategy_tahreeb_interpretation(self):
        """
        Integration: Verify PlayingStrategy interprets Tahreeb correctly using Mock Context.
        """
        # 1. Setup Context mock
        # We need a context where:
        # - Mode is Sun
        # - Previous trick: Partner won with Ace Hearts. Bot discarded 7 Spades.
        # - Current Hand: Bot has King Clubs (Same Color as Spades).
        
        # Mock Context
        class MockCtx:
            player_index = 0
            position = 'Bottom'
            mode = 'SUN'
            hand = [create_card('K', '♣'), create_card('7', '♦')] # King Clubs, 7 Diamonds
            lead_suit = None # Checks signal first logic usually
            table_cards = [] # Leading
            trumps = None
            def _compare_ranks(self, r1, r2, mode): return True # Dummy
            def is_master_card(self, c): return False # Dummy

            # Raw State for _check_partner_signals
            raw_state = {
                'currentRoundTricks': [
                    {
                        'winner': 2, # Top (Partner of Bottom 0)
                        'leadSuit': '♥',
                        'cards': [
                            {'suit': '♥', 'rank': 'A', 'playerIndex': 3}, # Left led? No, winner 2. Let's say 2 led.
                            {'suit': '♥', 'rank': 'A', 'playerIndex': 2}, # Top (Partner) played A♥ (Led & Won)
                            {'suit': '♥', 'rank': '7', 'playerIndex': 1}, # Right
                            {'suit': '♠', 'rank': '7', 'playerIndex': 0}, # Bottom (Us) - Discarded 7♠? 
                                                                          # Wait, this test checks REACTION to PARTNER's discard.
                                                                          # So Partner (Top, 2) must have discarded!
                        ]
                    }
                ]
            }
            
            # Memory Mock for Directional Check
            class MockMem:
                discards = {} 
            memory = MockMem()
        
        # Correct Scenario:
        # We are Player 0 (Bottom). Partner is Player 2 (Top).
        # Last Trick: Enemy (Right, 1) Won.
        # Partner (Top, 2) Discarded 7♠.
        # Context: Enemy Winning -> Tanfeer (Positive). Partner wants Spades.
        # WAIT, let's test TAHREEB (Negative).
        # Need Partner Winning? No, Tahreeb means DISCARDER's partner is winning.
        # If Partner (2) discards, then *I* (0) must have been winning?
        # Yes. If I (0) won the trick, and Partner (2) discarded 7♠.
        # Then Partner says "I don't want Spades".
        
        ctx = MockCtx()
        
        # Scenario: I (0) won the trick. Partner (2) discarded 7♠.
        ctx.raw_state['currentRoundTricks'] = [
             {
                'winner': 0, # I won
                'leadSuit': '♥',
                'cards': [
                    {'suit': '♥', 'rank': 'A', 'playerIndex': 0}, # I played A♥
                    {'suit': '♥', 'rank': '7', 'playerIndex': 1}, # Right
                    {'suit': '♠', 'rank': '7', 'playerIndex': 2}, # Partner Discarded 7♠
                    {'suit': '♥', 'rank': 'K', 'playerIndex': 3}, # Left
                ]
             }
        ]
        
        # Signal Check
        # My implementation of _check_partner_signals calls signal_mgr.get_signal_for_card(partner_card, is_partner_winning)
        # partner_card is 7♠.
        # is_partner_winning: Was Partner winning? 
        # Trick winner is 0 (Me).
        # Partner is 2.
        # So "is_partner_winning" (from perspective of Partner who played the card?)
        # Logic in playing.py: 
        # winner_idx = last_trick.get('winner')
        # partner_idx = (ctx.player_index + 2) % 4  <-- Only correct if we are analyzing previous trick's signal?
        # In `_check_partner_signals`, we are looking at *Last Trick*.
        # We are checking if *my partner* signaled.
        # So `partner_idx` is indeed my partner.
        # `is_partner_winner_of_trick` checks if *my partner* won the trick.
        # If *my partner* won the trick, he wouldn't be discarding (he led or followed).
        # Wait. Tahreeb definition: "Tahreeb occurs when the player's partner is in a position of strength... specifically when the partner is guaranteed to win".
        # If Partner P2 discards, it means HIS partner (P0 - Me) is winning.
        # So `is_partner_winning` logic in Manager depends on perspective.
        # Manager `get_signal_for_card(card, is_partner_winning)`
        # `is_partner_winning` means "Is the Partner of the Discarder Winning?"
        # In playing.py, `_check_partner_signals` receives `ctx`.
        # It calculates `is_partner_winner_of_trick` = (winner == partner_pos).
        # This checks if *My Partner* won.
        # If *My Partner* won, then *My Partner* didn't discard (usually). 
        # Exception: He led, everyone followed? No discard.
        # Discard happens when you are void.
        # You can only discard if you are NOT leading.
        # So if Partner Won, he likely Led and won. Or he followed and won.
        # If he followed and won, he didn't discard.
        # So if Partner Won, no signal from Partner?
        # Unless I led, and Partner discarded?? But if Partner discarded (failed to follow suit), he cannot win the trick (unless it's Trump, but discard implies non-trump/non-suit).
        # If Partner discards (plays off-suit), he CANNOT win.
        # So `is_partner_winner_of_trick` will ALWAYS be False if Partner discarded?
        # Implication: `get_signal_for_card` logic in `playing.py` might be flawed if it relies on Partner Winning *the trick*.
        # Tahreeb: "Tahreeb occurs when the player's partner is in a position of strength".
        # Meaning: The DISCARDER's Partner (Me) is winning.
        # So when I check `_check_partner_signals` (looking for MY Partner's signal):
        # I need to check if *I* (The Discarder's Partner) won the trick.
        # So `is_partner_winning` passed to manager should be `True` if *I* won the trick.
        # Let's check my implementation in `playing.py`.
        
        # Current Code in playing.py:
        # winner_idx = last_trick.get('winner')
        # partner_idx = (ctx.player_index + 2) % 4
        # is_partner_winner_of_trick = (winner_idx == partner_idx)  <-- Checks if Partner won.
        # sig_type = signal_mgr.get_signal_for_card(partner_card, is_partner_winner_of_trick)
        
        # If I (Self) won the trick: `winner_idx == ctx.player_index`.
        # `partner_idx != winner_idx`.
        # So `is_partner_winner_of_trick` is False.
        # Manager receives False.
        # Manager logic: `if is_partner_winning: Tahreeb`.
        # So it treats it as TANFEER (Enemy Winning).
        # BUT I (The Discarder's Partner) WON!
        # Context mismatch.
        # Manager expects "Is the Discarder's Partner winning?".
        # Calling code passes "Is the Discarder winning?". (Actually "Is the Bot's Partner winning?").
        
        # CORRECTION NEEDED in `playing.py`:
        # We are analyzing Partner's Discard.
        # Discarder = Partner.
        # Discarder's Partner = Me.
        # So we should pass `True` if `winner_idx == My_Index`.
        
        # Test the FIX:
        # ctx.player_index = 0.
        # winner = 0.
        # So is_tahreeb_context should be True.
        
        signal = self.strategy._check_partner_signals(ctx)
        
        # Expectation:
        # Partner (2) Discarded 7♠.
        # Context: Tahreeb (I won).
        # Signal: NEGATIVE_DISCARD (Don't want Spades).
        # Reaction: PREFER_SAME_COLOR (Want Clubs).
        
        self.assertIsNotNone(signal)
        self.assertEqual(signal['type'], 'PREFER_SAME_COLOR')
        self.assertEqual(signal['negated'], '♠')
        self.assertIn('♣', signal['suits'])

    def test_directional_signal_positive(self):
        """
        Sequence: Small (7) -> Big (9).
        Expectation: CONFIRMED_POSITIVE.
        """
        # Mock Discards (trick 1 then trick 2)
        discards = [
            {'rank': '7', 'suit': '♠', 'trick_idx': 1}, # Small
            {'rank': '9', 'suit': '♠', 'trick_idx': 2}  # Big
        ]
        
        signal = self.mgr.analyze_directional_signal(discards, '♠')
        self.assertEqual(signal, SignalType.CONFIRMED_POSITIVE)

    def test_directional_signal_negative(self):
        """
        Sequence: Big (J) -> Small (7).
        Expectation: CONFIRMED_NEGATIVE.
        """
        # J (Index 4) -> 7 (Index 7).
        # Val 4 -> Val 7.
        # Val1 < Val2 (Strong -> Weak)
        
        discards = [
            {'rank': 'J', 'suit': '♠', 'trick_idx': 1}, 
            {'rank': '7', 'suit': '♠', 'trick_idx': 2}  
        ]
        
        signal = self.mgr.analyze_directional_signal(discards, '♠')
        self.assertEqual(signal, SignalType.CONFIRMED_NEGATIVE)

    def test_asset_protection_lone_10(self):
        """
        Scenario: Partner signals Encourage. Bot has Lone 10.
        Expectation: Bot MUST play 10.
        """
        # Mock Context with Signal ENC Spades
        class MockCtx:
            hand = [create_card('10', '♠'), create_card('7', '♥')] # Lone 10 in S
            lead_suit = None
            table_cards = []
            trump = None
            mode = 'SUN'
            # Fake signal helper
            def _check_partner_signals(self, ctx):
                 return {'type': 'ENCOURAGE', 'suit': '♠'}
            
            # Helper methods required by PlayingLogic... or we can instantiate Strategy
            player_index = 0
            position = 'Bottom'
        
        ctx = MockCtx()
        # Bind helper to strategy instance to override logic for test
        # Actually easier: strategy._get_sun_lead calls self._check_partner_signals
        # We can mock strategy._check_partner_signals
        
        original_check = self.strategy._check_partner_signals
        self.strategy._check_partner_signals = lambda c: {'type': 'ENCOURAGE', 'suit': '♠'}
        
        decision = self.strategy._get_sun_lead(ctx)
        
        self.assertEqual(decision['action'], 'PLAY')
        # Should pick index 0 (10 Spades)
        self.assertEqual(ctx.hand[decision['cardIndex']].rank, '10')
        self.assertIn("Lone 10", decision['reasoning'])
        
        # Restore
        self.strategy._check_partner_signals = original_check

    def test_asset_protection_sequence(self):
        """
        Scenario: Partner signals Encourage Spades.
        Bot has 10, 9, 8 of Spades.
        Expectation: Bot leads 8 (Protector), NOT 10.
        """
        class MockCtx:
            hand = [
                create_card('10', '♠'), 
                create_card('9', '♠'), 
                create_card('8', '♠'),
                create_card('A', '♥')
            ]
            lead_suit = None
            table_cards = []
            mode = 'SUN'
            player_index = 0
            position = 'Bottom'
            trump = None
            team = 'MyTeam'
            def _compare_ranks(self, r1, r2, mode): return False 
            def is_master_card(self, c): return False
            def get_legal_moves(self): return [0, 1, 2, 3] # All legal 
            def is_player_void(self, p, s): return False

        ctx = MockCtx()
        
        # We need to ensure _find_lowest_rank_card_sun works.
        # It relies on ORDER_SUN imported in playing.py.
        
        original_check = self.strategy._check_partner_signals
        self.strategy._check_partner_signals = lambda c: {'type': 'ENCOURAGE', 'suit': '♠'}
        
        decision = self.strategy._get_sun_lead(ctx)
        
        # Should play 8 (Index 2)
        self.assertEqual(decision['action'], 'PLAY')
        played_card = ctx.hand[decision['cardIndex']]
        self.assertEqual(played_card.rank, '8')
        self.assertIn("Sequence Guard", decision['reasoning'])
        
        self.strategy._check_partner_signals = original_check

if __name__ == '__main__':
    unittest.main()
