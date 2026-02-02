import sys
import os

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from game_engine.logic.validation import is_move_legal
from game_engine.models.card import Card

def test_validation_logic():
    print("=== Testing Validation Logic (is_move_legal) ===")

    # 1. Setup Common Objects
    # Hand has Hearts and Spades
    hand = [Card('H', 'K'), Card('H', '9'), Card('S', 'A')]
    
    # Table: Partner led Hearts
    table_cards = [{'card': Card('H', '7'), 'playedBy': 'Top'}]
    
    # Players Map
    players_team_map = {'Bottom': 'us', 'Right': 'them', 'Top': 'us', 'Left': 'them'}
    
    # 2. Test Case A: Revoke in SUN (Has suit, plays different)
    # Player (Bottom) has Hearts (K, 9). Plays Spades (A).
    # Expected: False (Illegal)
    print("\nTest A: SUN - Revoke (Have H, Play S, Lead H)")
    card_played = Card('S', 'A') 
    
    is_legal = is_move_legal(
        card=card_played,
        hand=hand,
        table_cards=table_cards,
        game_mode='SUN',
        trump_suit='D', # Irrelevant in Sun
        my_team='us',
        players_team_map=players_team_map
    )
    
    if is_legal:
         print(f"❌ FAILED: Algorithm says {card_played} is LEGAL (Should be Illegal/Revoke)")
    else:
         print(f"✅ PASSED: Algorithm says {card_played} is ILLEGAL")

    # 3. Test Case B: Revoke in HOKUM (Trump=D)
    # Lead H. Have H. Play S.
    # Expected: False
    print("\nTest B: HOKUM - Revoke (Have H, Play S, Lead H)")
    is_legal = is_move_legal(
        card=card_played,
        hand=hand,
        table_cards=table_cards,
        game_mode='HOKUM',
        trump_suit='D', 
        my_team='us',
        players_team_map=players_team_map
    )
    
    if is_legal:
         print(f"❌ FAILED: Algorithm says {card_played} is LEGAL (Should be Illegal/Revoke)")
    else:
         print(f"✅ PASSED: Algorithm says {card_played} is ILLEGAL")
         
    # 4. Test Case C: Eating Check (Hokum)
    # Enemy is winning with Ace of Hearts. We have H King. We play H King. (Legal)
    # Enemy is winning with Ace of Trump. We have 9 Trump (Menel). We play 7 Trump. (Illegal if we have King? No, must beat if possible)
    
    # Let's focus on the User Report: "Wrong suit card". likely Revoke.
    
    # Test Case D: Lead is Trump (H). We have Trump. We play non-Trump.
    print("\nTest D: HOKUM - Revoke (Lead Trump H, Have Trump H, Play S)")
    table_trump_lead = [{'card': Card('H', '7'), 'playedBy': 'Right'}] # Enemy Led
    is_legal = is_move_legal(
        card=Card('S', 'A'),
        hand=hand, # Has H K, H 9
        table_cards=table_trump_lead,
        game_mode='HOKUM',
        trump_suit='H',
        my_team='us',
        players_team_map=players_team_map
    )
    if is_legal:
         print(f"❌ FAILED: Algorithm says S A is LEGAL (Should be Illegal/Revoke vs Trump Lead)")
    else:
         print(f"✅ PASSED: Algorithm says S A is ILLEGAL")


if __name__ == "__main__":
    test_validation_logic()
