
import unittest
from ai_worker.bot_context import BotContext
from ai_worker.agent import bot_agent
from game_engine.models.card import Card

class TestSawaLogic(unittest.TestCase):
    def setUp(self):
        pass
        
    def _create_context(self, hand_strs, mode, trump=None, played_cards=None, sawa_claimer='Left'):
        # Construct Mock State
        if played_cards is None: played_cards = []
        
        # Determine Claimer Index vs My Index
        # Me = 0 (Bottom)
        # Left = 3
        claimer_idx = 3 # Left
        
        state = {
            'players': [
                {'hand': [], 'position': 'Bottom', 'team': 'us', 'name': 'Bot'},
                {'hand': [], 'position': 'Right', 'team': 'them', 'name': 'P2'},
                {'hand': [], 'position': 'Top', 'team': 'us', 'name': 'P3'},
                {'hand': [], 'position': 'Left', 'team': 'them', 'name': 'P4'}
            ],
            'phase': 'PLAYING',
            'gameMode': mode,
            'trumpSuit': trump,
            'dealerIndex': 0,
            'currentRoundTricks': [], # We'll mock played_cards via context override or raw state
            'tableCards': [],
            'sawaState': {
                'active': True,
                'status': 'PENDING',
                'claimer': sawa_claimer,
                'responses': {} # I haven't responded
            }
        }
        
        # Populate my hand
        hand_dicts = []
        for s in hand_strs:
            hand_dicts.append({'rank': s[:-1], 'suit': s[-1]})
        state['players'][0]['hand'] = hand_dicts
        
        # Create Context
        ctx = BotContext(state, 0)
        
        # Inject Played Cards for is_master_card logic
        # BotContext derives this from 'currentRoundTricks' and 'tableCards'.
        # We can just override the set for testing.
        ctx.played_cards = set(played_cards)
        
        return ctx

    def test_sawa_acceptance_weak_hand(self):
        """I have weak cards. Should ACCEPT."""
        # SUN Mode. Hand: 7H, 8D.
        # Played: A, 10, K, Q of H and D are GONE.
        # So 7 and 8 are masters? No. 
        # Wait, if all higher cards are played, then 7 IS Master.
        # Sawa Claim means THEY claim to win everything.
        # If I have a Master, I win.
        # So for ACCEPTANCE, I must NOT have a master.
        # This implies higher cards are Still IN PLAY (held by others).
        # e.g. I have 7H. Ace H is NOT played.
        
        ctx = self._create_context(['7♥', '8♦'], 'SUN', played_cards=[])
        # A♥ is unplayed. So 7♥ is NOT master.
        
        decision = bot_agent._evaluate_sawa_refusal(ctx)
        self.assertEqual(decision['response'], 'ACCEPT')

    def test_sawa_refusal_master_sun(self):
        """I have Ace in Sun. Should REFUSE."""
        ctx = self._create_context(['A♥', '7♦'], 'SUN', played_cards=[])
        # A♥ is Master.
        
        decision = bot_agent._evaluate_sawa_refusal(ctx)
        self.assertEqual(decision['response'], 'REFUSE')
        self.assertIn('Master', decision['reasoning'])

    def test_sawa_refusal_master_hokum_trump(self):
        """I have Jack of Trump in Hokum. Should REFUSE."""
        ctx = self._create_context(['J♠', '7♦'], 'HOKUM', trump='♠', played_cards=[])
        # J♠ is Master Trump.
        
        decision = bot_agent._evaluate_sawa_refusal(ctx)
        self.assertEqual(decision['response'], 'REFUSE')

    def test_sawa_refusal_master_hokum_nontrump(self):
        """I have Ace of Hearts (Non-Trump) in Hokum. Should REFUSE (Safe Strategy)."""
        ctx = self._create_context(['A♥', '7♦'], 'HOKUM', trump='♠', played_cards=[])
        # A♥ is Master Non-Trump.
        
        decision = bot_agent._evaluate_sawa_refusal(ctx)
        self.assertEqual(decision['response'], 'REFUSE')

    def test_integration_sawa_response(self):
        """Test the full get_decision flow"""
        # Mock Sawa State
        hand = ['A♥']
        ctx = self._create_context(hand, 'SUN')
        
        # Inject context into bot call?
        # bot_agent.get_decision takes (game_state, player_index).
        # We need to construct the state.
        
        state = ctx.raw_state
        idx = 0
        
        # Bot Agent creates its own context. We need to ensure logic holds.
        # Since logic depends on is_master_card which depends on played_cards...
        # We need to populate currentRoundTricks in state to match played_cards logic?
        # Default create_context leaves played_cards empty. 
        # A♥ is Master if played_cards empty.
        
        decision = bot_agent.get_decision(state, idx)
        
        self.assertEqual(decision['action'], 'SAWA_RESPONSE')
        self.assertEqual(decision['response'], 'REFUSE')

if __name__ == '__main__':
    unittest.main()
