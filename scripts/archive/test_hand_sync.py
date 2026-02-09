
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_engine.logic.game import Game, GamePhase
from game_engine.models.card import Card
from game_engine.models.player import Player

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HandSyncTest")

def test_hand_sync():
    logger.info("=== STARTING HAND SYNC TEST ===")
    
    # 1. Initialize Game
    game = Game("test_room")
    p1 = game.add_player("p1", "Player 1")
    game.add_player("p2", "Player 2")
    game.add_player("p3", "Player 3")
    game.add_player("p4", "Player 4")
    
    # Mock Phase
    game.phase = GamePhase.PLAYING.value
    game.current_turn = 0 # Player 1's turn
    
    # 2. Mock Hand for Player 1
    # Server Hand: [7H, AS, KD]
    c1 = Card('♥', '7', '7♥')
    c2 = Card('♠', 'A', 'A♠')
    c3 = Card('♦', 'K', 'K♦')
    p1.hand = [c1, c2, c3]
    
    logger.info(f"Initial Server Hand: {[c.id for c in p1.hand]}")
    
    # --- TEST 1: Normal Play (Aligned) ---
    logger.info("\n--- Test 1: Normal Play (7H at Index 0) ---")
    # Client plays 7H at index 0
    res = game.play_card(0, 0, metadata={'cardId': '7♥'})
    
    if res.get('success'):
        logger.info("PASS: Normal play successful.")
    else:
        logger.error(f"FAIL: Normal play failed: {res}")
        return

    # Verify Hand: [AS, KD]
    current_ids = [c.id for c in p1.hand]
    logger.info(f"Hand after T1: {current_ids}")
    if current_ids == ['A♠', 'K♦']:
        logger.info("PASS: Hand state correct.")
    else:
         logger.error("FAIL: Hand state incorrect.")

    # --- TEST 2: Index Drift / Desync ---
    logger.info("\n--- Test 2: Index Drift (Play K♦) ---")
    # Scenario: Client thinks K♦ is at index 0 (maybe it sorted differently), but Server has it at index 1.
    # Server Hand: [A♠ (0), K♦ (1)]
    # Client sends: index=0 (pointing to A♠), but cardId='K♦'
    
    # Note: reset turn logic for test
    game.current_turn = 0 
    
    res = game.play_card(0, 0, metadata={'cardId': 'K♦'})
    
    if res.get('success'):
        # Verify that K♦ was played, NOT A♠
        played_card = game.table_cards[-1]['card']
        logger.info(f"Played Card: {played_card.id}")
        
        if played_card.id == 'K♦':
            logger.info("PASS: Server corrected index and played K♦.")
        else:
            logger.error(f"FAIL: Server played wrong card {played_card.id} (Expected K♦).")
    else:
        logger.error(f"FAIL: Desync play failed: {res}")

    # Verify Hand: [A♠]
    current_ids = [c.id for c in p1.hand]
    logger.info(f"Hand after T2: {current_ids}")
    if current_ids == ['A♠']:
        logger.info("PASS: Hand state correct.")

    # --- TEST 3: Ghost Card ---
    logger.info("\n--- Test 3: Ghost Card (Card Not In Hand) ---")
    game.current_turn = 0
    # Try to play Q♣ (ID: Q♣)
    res = game.play_card(0, 0, metadata={'cardId': 'Q♣'})
    
    if res.get('error') == "Card Not Found in Hand (ID Mismatch)":
        logger.info("PASS: Server rejected ghost card.")
    else:
        logger.error(f"FAIL: Server did not reject ghost card correctly. Result: {res}")

if __name__ == "__main__":
    test_hand_sync()
