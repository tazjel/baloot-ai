
import sys
import os
import logging

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from game_engine.logic.game import Game
from game_engine.models.card import Card
from game_engine.models.player import Player
from game_engine.models.constants import GamePhase

# Setup Logging
logging.basicConfig(level=logging.INFO)

def test_revoke_detection():
    print("=== Debugging Revoke Detection ===")
    
    # 1. Setup Game
    game = Game("debug_room")
    game.phase = GamePhase.PLAYING.value
    game.game_mode = 'SUN' # Sun mode: Must follow suit
    
    # 2. Setup Players
    # P1 (Bottom) - Leads
    # P2 (Right) - Has Suit, but Revokes
    p1 = Player("P1", "Lead", 0, game)
    p2 = Player("P2", "Cheat", 1, game)
    game.players = [p1, p2, Player("P3", "Top", 2, game), Player("P4", "Left", 3, game)]
    
    # 3. Deal Hands
    # P1 has Heart A
    p1.hand = [Card('♥', 'A')]
    # P2 has Heart K and Spade 7
    p2.hand = [Card('♥', 'K'), Card('♠', '7')]
    
    # 4. P1 Plays Heart A (Lead)
    print(f"P1 leads with {p1.hand[0]}")
    game.current_turn = 0
    res = game.play_card(0, 0) # Index 0
    if "error" in res:
        print(f"P1 play failed: {res}")
        return
        
    # 5. P2 Plays Spade 7 (Revoke!)
    # Should be flagged as illegal
    print(f"P2 tries to play {p2.hand[1]} (Spades) while holding Hearts...")
    game.current_turn = 1
    # Card is at index 1 in hand
    res = game.play_card(1, 1) 
    
    # 6. Verify Result
    if "error" in res:
         print(f"P2 play rejected (Correct if strict, Incorrect if allowing illegal): {res}")
         return

    # Check Table Card Metadata
    last_play = game.table_cards[-1]
    print(f"P2 played: {last_play['card']}")
    metadata = last_play.get('metadata', {})
    print(f"Metadata: {metadata}")
    
    if metadata.get('is_illegal'):
        print("✅ SUCCESS: Illegal move flagged correctly.")
    else:
        print("❌ FAILURE: Illegal move NOT flagged.")
        
    # 7. Check is_valid_move direct call
    print("\n--- Direct Validation Check ---")
    card_played = Card('♠', '7')
    hand = [Card('♥', 'K'), Card('♠', '7')] # P2's hand BEFORE play
    # Note: play_card removes card from hand usually, so we reconstruct
    
    # Validation args: card, hand, table_cards
    # table_cards has P1's play
    # We must pass the hand AS IT WAS
    
    # Creating a temporary game or just calling validation helper if possible
    # accessing game.is_valid_move
    
    is_valid = game.is_valid_move(card_played, hand)
    print(f"game.is_valid_move result: {is_valid} (Expected: False)")

if __name__ == "__main__":
    test_revoke_detection()
