
import sys
import os
import redis
import json
import logging

try:
    from game_engine.core.recorder import TimelineRecorder
except ImportError:
    # Fix path
    sys.path.append(os.getcwd())
    from game_engine.core.recorder import TimelineRecorder

# Setup Logging
logging.basicConfig(level=logging.INFO)

def test_recorder_crash():
    print("Connecting to Redis...")
    r = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)
    
    try:
        r.ping()
        print("Redis connected.")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return

    recorder = TimelineRecorder(r)
    
    print("Listing streams...")
    keys = r.keys("game:*:timeline")
    print(f"Found keys: {keys}")
    
    if not keys:
        print("No timeline keys found. Creating dummy data...")
        stream_key = "game:crash_repro:timeline"
        r.xadd(stream_key, {"event": "TEST", "details": "Dummy", "state": "{}"})
        keys = [stream_key]
        
    for k in keys:
        room_id = k.split(":")[1]
        print(f"Testing room: {room_id}")
        try:
            history = recorder.get_history(room_id, count=100)
            print(f"Success! Got {len(history)} entries.")
        except Exception as e:
            print(f"CRASH DETECTED for room {room_id}:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_recorder_crash()
