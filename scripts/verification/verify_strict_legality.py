
import sys
import os
import unittest

# Setup Path
sys.path.append(os.getcwd())

from ai_worker.bot_context import BotContext
from game_engine.models.card import Card

def create_mock_context(hand, table_cards, mode='HOKUM', trump='♠', my_team='us'):
    # Mock Raw State
    raw_state = {
        'players': [
            {'position': 'Bottom', 'team': 'us', 'hand': [c.to_dict() for c in hand], 'name': 'Bot'},
            {'position': 'Right', 'team': 'them', 'hand': [], 'name': 'Right'},
            {'position': 'Top', 'team': 'us', 'hand': [], 'name': 'Top'},
            {'position': 'Left', 'team': 'them', 'hand': [], 'name': 'Left'}
        ],
        'phase': 'PLAYING',
        'gameMode': mode,
        'trumpSuit': trump,
        'tableCards': table_cards,
        'dealerIndex': 1,
        'bid': {'type': mode, 'suit': trump, 'bidder': 'Right'}
    }
    
    return BotContext(raw_state, 0)

class TestStrictLegality(unittest.TestCase):
    
    def test_must_follow_suit_hokum(self):
        print("\n--- TEST: Must Follow Suit (Hokum) ---")
        # I have [7♠ (Trump), K♥].
        # Lead is 8♠ (Trump).
        # Must play 7♠. K♥ is illegal.
        
        hand = [Card('♠', '7'), Card('♥', 'K')]
        # Lead: 8♠ (Enemy)
        table = [{'card': {'suit': '♠', 'rank': '8'}, 'playedBy': 'Right'}]
        
        ctx = create_mock_context(hand, table, mode='HOKUM', trump='♠')
        legal_indices = ctx.get_legal_moves()
        
        print(f"Hand: {hand}")
        print(f"Legal Indices: {legal_indices}")
        
        self.assertIn(0, legal_indices) # 7♠ is legal
        self.assertNotIn(1, legal_indices) # K♥ is illegal (Revoke)
        print("SUCCESS: Forced to follow Trump.")

    def test_must_trump_if_void(self):
        print("\n--- TEST: Must Trump if Void (Hokum) ---")
        # Lead: 7♦.
        # Hand: [K♥, 7♠ (Trump)]. Void in Diamonds.
        # Enemy Winning? Yes (7♦ by Right).
        # Must Trump.
        
        hand = [Card('♥', 'K'), Card('♠', '7')]
        table = [{'card': {'suit': '♦', 'rank': '7'}, 'playedBy': 'Right'}]
        
        ctx = create_mock_context(hand, table, mode='HOKUM', trump='♠')
        legal_indices = ctx.get_legal_moves()
        
        print(f"Hand: {hand}")
        print(f"Legal Indices: {legal_indices}")
        
        self.assertIn(1, legal_indices) # 7♠ (Trump) is legal
        self.assertNotIn(0, legal_indices) # K♥ is illegal (Refusing to trump)
        print("SUCCESS: Forced to Trump.")

    def test_partner_winning_exception(self):
        print("\n--- TEST: Partner Winning Exception (Hokum) ---")
        # Lead: 7♦. Winner: Top (Partner) with A♦.
        # Hand: [K♥, 7♠ (Trump)]. Void in Diamonds.
        # Partner winning -> No need to trump. Can play K♥ (Trash).
        
        hand = [Card('♥', 'K'), Card('♠', '7')]
        table = [
             {'card': {'suit': '♦', 'rank': '7'}, 'playedBy': 'Right'}, 
             {'card': {'suit': '♦', 'rank': 'A'}, 'playedBy': 'Top'}
        ] 
        
        ctx = create_mock_context(hand, table, mode='HOKUM', trump='♠')
        legal_indices = ctx.get_legal_moves()
        
        print(f"Hand: {hand}")
        print(f"Legal Indices: {legal_indices}")
        
        self.assertIn(0, legal_indices) # K♥ is legal
        self.assertIn(1, legal_indices) # 7♠ is legal (Can trump if I want, but not forced)
        print("SUCCESS: Partner winning allows played non-trump.")

    def test_must_overtrump(self):
        print("\n--- TEST: Must Over-Trump (Hokum) ---")
        # Lead: 7♦.
        # Right Trumps with 7♠.
        # I have [8♠ (Higher Trump), 9♦ (Match Suit?? No void), K♥].
        # Wait, if I have 9♦, I MUST follow suit.
        # Scenario: Void in Diamonds.
        # Hand: [8♠ (Trump), 7♣].
        # Right (Enemy) played 7♠ (Trump).
        # I Must Overtrump with 8♠? Or can I play 7♣?
        # Rule: If enemy trumps, you must overtrump if possible. If not possible, play any card?
        # Usually: Must overtrump. If cannot overtrump, play any card (even small trump allowed? Or any suit?)
        # Let's check logic: (is_move_legal lines 114-121)
        
        hand = [Card('♠', '8'), Card('♣', '7')]
        table = [
             {'card': {'suit': '♦', 'rank': '7'}, 'playedBy': 'Left'}, # Lead
             {'card': {'suit': '♠', 'rank': '7'}, 'playedBy': 'Right'} # Enemy Trumped
        ]
        
        ctx = create_mock_context(hand, table, mode='HOKUM', trump='♠')
        legal_indices = ctx.get_legal_moves()
        
        print(f"Hand: {hand}")
        print(f"Legal Indices: {legal_indices}")
        
        self.assertIn(0, legal_indices) # 8♠ (Overtrump) is legal
        self.assertNotIn(1, legal_indices) # 7♣ (undertrumping/escaping when overtrump valid) -> Illegal?
        # Logic line 110: if card.suit != trump: return False.
        # So I MUST play trump if I have it.
        # So 7♣ is illegal.
        print("SUCCESS: Forced to Over-Trump.")

if __name__ == "__main__":
    unittest.main()
