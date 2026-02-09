
import os
import sys
import json
import logging
import uuid
import time

# Setup Paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.common import db
# Ensure tables
import server.models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedPuzzles")

def seed_puzzles():
    logger.info("Seeding database with manual Golden Puzzles...")

    # Puzzle 1: Don't eat your partner's ace (Sun)
    # Scenario: Partner plays Ace Sun. You have King. Do not play King if you have a small card.
    state_1 = {
        "players": [
            {"position": "Bottom", "hand": [{"suit": "S", "rank": "K"}, {"suit": "S", "rank": "7"}, {"suit": "H", "rank": "10"}], "name": "Me"},
            {"position": "Right", "hand": [], "name": "Bot"},
            {"position": "Top", "hand": [], "name": "Partner"},
            {"position": "Left", "hand": [], "name": "Bot"}
        ],
        "bid": {"type": "SUN", "bidder": "Top"},
        "currentTurnIndex": 0,
        "playedCards": {
            "2": {"suit": "S", "rank": "A", "playedBy": "Top"}, # Partner Played Ace
            "3": {"suit": "H", "rank": "7", "playedBy": "Left"}  # Left played garbage
        },
        "floorCard": None
    }
    
    correct_1 = {"suit": "S", "rank": "7"}
    bad_1 = {"suit": "S", "rank": "K"}
    reason_1 = "Your partner has already captured the trick with the Ace of Spades. Playing your King (10 points) is a waste because the Ace is the highest. Save your King for a future trick or throw 10/K on a winning trick to add points."

    # Puzzle 2: Cut the trick (Hokum)
    # Scenario: Opponent plays big Ace. You have no suit, but have Trump.
    state_2 = {
         "players": [
            {"position": "Bottom", "hand": [{"suit": "D", "rank": "7"}, {"suit": "C", "rank": "J"}], "name": "Me"}, # Diamond is Trump
            {"position": "Right", "hand": [], "name": "Bot"},
            {"position": "Top", "hand": [], "name": "Partner"},
            {"position": "Left", "hand": [], "name": "Bot"}
        ],
        "bid": {"type": "HOKUM", "suit": "D", "bidder": "Right"},
        "currentTurnIndex": 0,
        "playedCards": {
            "1": {"suit": "S", "rank": "A", "playedBy": "Right"} # Opponent Ace
        },
        "floorCard": {"suit": "D", "rank": "7"}
    }
    correct_2 = {"suit": "D", "rank": "7"} # Cut
    bad_2 = {"suit": "C", "rank": "J"} # Throw random
    reason_2 = "The opponent is winning with an Ace. You have a Trump (Diamond). You should 'cut' the trick to win it for your team."

    # Insert
    puzzles = [
        (state_1, bad_1, correct_1, reason_1),
        (state_2, bad_2, correct_2, reason_2)
    ]
    
    count = 0
    for s, b, c, r in puzzles:
        # Check uniqueness
        chash = f"seed-{uuid.uuid4().hex[:8]}"
        
        db.bot_training_data.insert(
            context_hash=chash,
            game_state_json=json.dumps(s),
            bad_move_json=json.dumps(b),
            correct_move_json=json.dumps(c),
            reason=r,
            created_on=datetime.datetime.now() if 'datetime' in globals() else None
        )
        count += 1
        
    db.commit()
    logger.info(f"Seeded {count} puzzles.")

import datetime
if __name__ == "__main__":
    seed_puzzles()
