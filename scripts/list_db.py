import sys
import os
import json
import datetime

# Add project root to path
sys.path.append(os.getcwd())

# Setup DB
try:
    from server.common import db
    import server.models # Ensure tables are defined
    
    print("DB Connected.")
    
    if 'match_archive' not in db.tables:
        print("ERROR: match_archive table NOT found!")
        sys.exit(1)
        
    print("Querying match_archive...")
    
    rows = db(db.match_archive.id > 0).select()
    print(f"Total Records: {len(rows)}")
    
    for r in rows:
        print(f"ID: {r.id}, GameID: {r.game_id}, Score: {r.final_score_us}-{r.final_score_them}, Time: {r.timestamp}")
        
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
