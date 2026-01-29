import sys
import os
import time

# Setup Path
sys.path.append(os.getcwd())

from game_engine.logic.game import Game
# Import models to register tables!
import server.models 
from server.common import db
from server.services.archiver import archive_match

def test_archival():
    print("--- Testing Match Archival ---")
    
    # 1. Create Game
    game = Game("test_archive_" + str(int(time.time())))
    game.add_player("p1", "Player 1")
    game.add_player("p2", "Player 2")
    game.add_player("p3", "Player 3")
    game.add_player("p4", "Player 4")
    game.start_game()
    
    print(f"Game Created: {game.room_id}")
    
    # 2. Force Win Condition & Inject Fake History
    game.match_scores['us'] = 152
    game.match_scores['them'] = 100
    
    # Inject dummy history so archiver has something to save
    game.full_match_history = [{
        'round': 1, 
        'scores': {'us': 20, 'them': 0},
        'tricks': [],
        'initialHands': {} 
    }]
    
    # 3. Trigger End Round (which should check condition and archive)
    print("Triggering End Round (Win)...")
    game.end_round(skip_scoring=True) # Skip scoring engine, just process state
    
    if game.phase != "GAMEOVER":
        print(f"❌ Game Phase is {game.phase}, expected GAMEOVER")
        return
        
    print("✅ Game Phase is GAMEOVER")
    
    # 4. Check DB
    print("Checking Database...")
    record = db.match_archive(game_id=game.room_id)
    
    if record:
        print(f"✅ Archive Found! ID: {record.id}")
        print(f"   Scores: Us={record.final_score_us}, Them={record.final_score_them}")
        print(f"   History Length: {len(str(record.history_json))} chars")
        # cleanup
        db(db.match_archive.id == record.id).delete()
        db.commit()
        print("   (Cleaned up test record)")
    else:
        print("❌ Archive NOT Found in DB")
        
    print("Checking Log File...")
    found_event = False
    with open("logs/server_manual.log", "r", encoding="utf-8") as f:
        for line in f:
            if "MATCH_ARCHIVED" in line and game.room_id in line:
                if "history_stats" in line:
                    found_event = True
                    print(f"✅ Found Structured Log Event: {line.strip()[:100]}...")
                    break
    
    if not found_event:
        print("❌ MATCH_ARCHIVED Log Event NOT Found")

if __name__ == "__main__":
    test_archival()
