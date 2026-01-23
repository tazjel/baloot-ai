
import sys
import os
import logging
from unittest.mock import MagicMock

# Setup environment to load local modules
sys.path.append(os.getcwd())

from game_logic import Game, Player, Card

# Mock SIO to avoid server dependencies
class MockSIO:
    def emit(self, *args, **kwargs): pass
    def start_background_task(self, *args, **kwargs): pass

# Setup Game
game = Game("test_room")
game.sio = MockSIO()

# Add Players
for i in range(4):
    game.add_player(f"p{i}", f"Player {i}")

game.start_game()

# --- TEST 1: ASHKAL BIDDING & SCORING ---
print("--- TEST 1: ASHKAL SCORING ---")
# Force Dealer to P0
game.dealer_index = 0
game.current_turn = 1
game.phase = "BIDDING"
game.bidding_round = 1

# P0 (Dealer) passes
game.handle_bid(1, "PASS") # P1
game.handle_bid(2, "PASS") # P2
game.handle_bid(3, "PASS") # P3

# P0 calls ASHKAL
print("P0 (Dealer) calling ASHKAL...")
res = game.handle_bid(0, "ASHKAL")
print(f"Bid Result: {res}")

if game.game_mode == "SUN" and game.bid['type'] == "SUN":
    print("SUCCESS: Game Mode set to SUN correctly for Ashkal.")
else:
    print(f"FAILURE: Game Mode is {game.game_mode}, Bid Type is {game.bid['type']}")

# Check Partner (P2) is bidder
if game.bid['bidder'] == game.players[2].position:
    print("SUCCESS: Partner (P2) became bidder.")
else:
    print(f"FAILURE: Bidder is {game.bid['bidder']}, expected {game.players[2].position}")

# --- TEST 2: PROJECT DEDUPLICATION ---
print("\n--- TEST 2: PROJECT DEDUPLICATION ---")
p2 = game.players[2]
# Give P2 a Sira: A, K, Q Spades
p2.hand = [
    Card('♠', 'A'), Card('♠', 'K'), Card('♠', 'Q'), 
    Card('♥', '7'), Card('♥', '8'), Card('♥', '9'), # Sira Hearts
    Card('♦', '7'), Card('♦', '8')
]
# Force turn to P2
game.current_turn = 2
game.phase = "PLAYING"

# Declare SIRA (Spades)
print("Declaring SIRA (First Time)...")
game.handle_declare_project(2, 'SIRA')
count_1 = len(game.trick_1_declarations.get(p2.position, []))
print(f"Count after 1st declare: {count_1}")

# Declare SIRA (Spades) AGAIN - Should be blocked
print("Declaring SIRA (Duplicate)...")
game.handle_declare_project(2, 'SIRA')
count_2 = len(game.trick_1_declarations.get(p2.position, []))
print(f"Count after 2nd declare: {count_2}")

if count_1 == 1 and count_2 == 1:
    print("SUCCESS: Duplicate rejected.")
else:
    print(f"FAILURE: Counts are {count_1} -> {count_2}")

# --- TEST 3: SCORING CALCULATION (Mock End Game) ---
print("\n--- TEST 3: SCORING CALCULATION (Ashkal/Sun) ---")
# Simulate P2 Team taking all tricks (Kaboot) in Sun
game.round_history = [{'winner': p2.position, 'points': 100}] * 8 # Fake
# This bypasses calculation logic, let's call end_round with manually set points?
# Better: Just check calculate_game_points_with_tiebreak for 26 pts

# Test logic: 130 points in Sun -> 26 Game Points
raw_us = 130  # Max raw in Sun
raw_them = 0
game.game_mode = 'SUN'
result = game.calculate_game_points_with_tiebreak(raw_us, raw_them, 'us')
print(f"Sun 130 pts -> Game Points: {result['game_points']}")

if result['game_points']['us'] == 26:
    print("SUCCESS: 130 raw points = 26 game points in Sun.")
else:
    print(f"FAILURE: Expected 26, got {result['game_points']['us']}")

print("\n--- TESTS COMPLETED ---")
