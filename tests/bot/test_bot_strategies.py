
import unittest
from ai_worker.bot_context import BotContext
from ai_worker.strategies.playing import PlayingStrategy
from ai_worker.strategies.bidding import BiddingStrategy
from ai_worker.personality import BALANCED

class MockCard:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.points = 0 # Simplified
    def to_dict(self):
        return {'rank': self.rank, 'suit': self.suit}
    def __repr__(self):
        return f"{self.rank}{self.suit}"

class TestBotStrategies(unittest.TestCase):
    def setUp(self):
        self.playing_strategy = PlayingStrategy()
        self.bidding_strategy = BiddingStrategy()
        
    def _create_ctx(self, phase, hand_strs, raw_state_extras=None):
        hand = []
        for s in hand_strs:
            rank = s[:-1]
            suit = s[-1]
            hand.append(MockCard(rank, suit))
            
        raw_state = {
            'bid': {},
            'floorCard': {'rank': '7', 'suit': '♥'}, # Heart Floor
            'roundHistory': [],
            'matchScores': {'us': 0, 'them': 0},
            'biddingPhase': phase,
            'players': [
                {'position': 'Bottom', 'team': 'us', 'hand': [], 'name': 'Me'},
                {'position': 'Right', 'team': 'them', 'hand': [], 'name': 'Bot1'},
                {'position': 'Top', 'team': 'us', 'hand': [], 'name': 'Partner'},
                {'position': 'Left', 'team': 'them', 'hand': [], 'name': 'Bot2'}
            ]
        }
        if raw_state_extras:
            raw_state.update(raw_state_extras)
            
        # Mock Context
        class MockCtx(BotContext):
            def __init__(self, raw, h):
                self.raw_state = raw
                self.hand = h
                self.phase = phase
                self.mode = 'SUN' # Default
                self.table_cards = []
                self.player_index = 0
                self.dealer_index = 0 # I am dealer?
                self.position = 'Bottom'
                self.team = 'us'
                self.memory = None # Mock Memory
                self.personality = BALANCED
                self.floor_card = MockCard(raw['floorCard']['rank'], raw['floorCard']['suit']) if raw.get('floorCard') else None
                # Check Dealer logic
                self.is_dealer = (self.player_index == self.dealer_index)
                self.bidding_round = 1 if phase == 'ROUND_1' else 2 # approx
                self.trump = None
                self.bidding_round_history = []
                # Mission 9 additions: position + score awareness
                self.is_first_player = False
                self.partner_is_first = False
                self.is_offensive = False
                self.is_desperate = False
                self.is_protecting = False
                self.match_score_us = raw.get('matchScores', {}).get('us', 0)
                self.match_score_them = raw.get('matchScores', {}).get('them', 0)
                
            def is_master_card(self, c): return False # MOCK

        return MockCtx(raw_state, hand)

    def test_ashkal_response_round_1(self):
        """Round 1 Ashkal: Partner (Bidder) wants SAME COLOR (Red). Floor=Hearts."""
        # My Hand: Spades (Black), Clubs (Black), Diamonds (Red)
        # Should play Diamond.
        hand = ['7♠', '8♣', '10♦', 'K♦']
        
        # Ashkal Bid by Partner
        bid_state = {
            'isAshkal': True,
            'round': 1,
            'bidder': 'Top', # Partner
            'type': 'SUN'
        }
        
        ctx = self._create_ctx('PLAYING', hand, {'bid': bid_state})
        decision = self.playing_strategy.get_decision(ctx)
        
        self.assertEqual(decision['action'], 'PLAY')
        # Check played card is Diamond (Red)
        played_idx = decision['cardIndex']
        played_card = ctx.hand[played_idx]
        self.assertEqual(played_card.suit, '♦', f"Round 1 Ashkal (Floor Heart) -> Should play Diamond (Same Color). Got {played_card}")
        self.assertIn("Ashkal", decision['reasoning'])

    def test_ashkal_response_round_2(self):
        """Round 2 Ashkal: Partner wants OPPOSITE COLOR (Black). Floor=Hearts."""
        # My Hand: Spades (Black), Clubs (Black), Diamonds (Red)
        # Should play Spade or Club.
        hand = ['7♠', '8♣', '10♦', 'K♦']
        
        bid_state = {
            'isAshkal': True,
            'round': 2,
            'bidder': 'Top',
            'type': 'SUN'
        }
        
        ctx = self._create_ctx('PLAYING', hand, {'bid': bid_state})
        decision = self.playing_strategy.get_decision(ctx)
        
        self.assertEqual(decision['action'], 'PLAY')
        played_idx = decision['cardIndex']
        played_card = ctx.hand[played_idx]
        self.assertIn(played_card.suit, ['♠', '♣'], f"Round 2 Ashkal (Floor Heart) -> Should play Black. Got {played_card}")

    def test_strong_project_ashkal_bid(self):
        """Should Force Ashkal if holding 4 Aces"""
        hand = ['A♠', 'A♣', 'A♦', 'A♥', '7♠', '8♠', '9♠', '10♠'] # 4 Aces
        
        # Dealer Position (Eligible for Ashkal)
        ctx = self._create_ctx('ROUND_1', hand, {'biddingPhase': 'ROUND_1'})
        ctx.dealer_index = 0
        ctx.player_index = 0 # Dealer
        ctx.is_dealer = True
        # Floor not Ace
        ctx.floor_card = MockCard('7', '♦')
        ctx.ctx_floor_card = ctx.floor_card # Hack for Mock
        
        decision = self.bidding_strategy.get_decision(ctx)
        
        self.assertEqual(decision['action'], 'ASHKAL')
        self.assertIn("Strong Project", decision['reasoning'])

    def test_strong_project_ashkal_banned_on_ace(self):
        """Should NOT force Ashkal if Floor is Ace"""
        hand = ['A♠', 'A♣', 'A♦', 'A♥', '7♠', '8♠', '9♠', '10♠'] # 4 Aces
        
        ctx = self._create_ctx('ROUND_1', hand)
        ctx.dealer_index = 0
        ctx.player_index = 0
        ctx.is_dealer = True
        ctx.floor_card = MockCard('A', '♦') # Ace Floor
        
        decision = self.bidding_strategy.get_decision(ctx)
        
        # Should fall back to SUN or PASS (Sun Score is high, so likely SUN)
        self.assertNotEqual(decision['action'], 'ASHKAL', "Ashkal banned on Ace floor")
        self.assertEqual(decision['action'], 'SUN') # Normal Sun logic takes over

if __name__ == '__main__':
    unittest.main()
