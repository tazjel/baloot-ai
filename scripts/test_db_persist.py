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
    print(f"Tables: {db.tables}")
    
    if 'match_archive' not in db.tables:
        print("ERROR: match_archive table NOT found!")
        sys.exit(1)
        
    print("Found match_archive. Attempting insert...")
    
    dummy_id = f"test_{int(datetime.datetime.now().timestamp())}"
    dummy_history = [{"test": "data"}]
    
    ret = db.match_archive.insert(
        game_id=dummy_id,
        user_email='test_script',
        history_json=json.dumps(dummy_history),
        final_score_us=100,
        final_score_them=50
    )
    db.commit()
    print(f"Insert Successful. ID: {ret}")
    
    # Verify Read
    row = db(db.match_archive.game_id == dummy_id).select().first()
    if row:
        print("Read Verification Successful.")
        print(row.as_dict())
    else:
        print("ERROR: Read Verification Failed!")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
