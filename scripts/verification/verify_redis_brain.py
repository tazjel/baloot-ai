import sys
import os
import time
import json
import logging

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import redis
except ImportError:
    print("Error: 'redis' package not installed. Run 'pip install redis'")
    sys.exit(1)

from settings import REDIS_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

def test_redis():
    logger.info(f"Connecting to Redis at {REDIS_URL}...")
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        logger.info("✅ Redis Connected Successfully!")
        
        # Test Queue Write
        test_payload = {"context_hash": "TEST_HASH", "game_context": {"data": "test"}, "heuristic_decision": {"action": "PASS"}}
        r.lpush("bot:analyze_queue", json.dumps(test_payload))
        logger.info("✅ Pushed test task to 'bot:analyze_queue'")
        
        # Test Cache Write/Read
        r.set("bot:move:TEST_HASH", json.dumps({"rank": "A", "suit": "♠", "reason": "Test Move"}))
        val = r.get("bot:move:TEST_HASH")
        if val:
             logger.info(f"✅ Cache Read Verified: {val}")
        else:
             logger.error("❌ Cache Read Failed!")
             
        # Cleanup
        r.delete("bot:move:TEST_HASH")
        # Pop the test task (might be picked up by worker if running)
        # r.rpop("bot:analyze_queue") 
        
        print("\nSUMMARY: Redis is ready for the Brain.")
        
    except redis.exceptions.ConnectionError:
        logger.error("❌ Could not connect to Redis. Is it running?")
        print("Tip: Run 'docker run --name baloot-redis -p 6379:6379 -d redis'")
    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    test_redis()
