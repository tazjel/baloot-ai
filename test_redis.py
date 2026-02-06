import redis
import sys

print("Testing Redis Connection...")
try:
    r = redis.Redis(
        host='127.0.0.1', 
        port=6379, 
        db=0, 
        decode_responses=True, 
        socket_timeout=5.0
    )
    r.ping()
    print("✅ Connection Successful!")
    info = r.info()
    print(f"Uptime: {info['uptime_in_seconds']}s")
except Exception as e:
    print(f"❌ Connection Failed: {e}")
    # Try localhost
    try:
        print("Retrying with 'localhost'...")
        r = redis.Redis(
            host='localhost', 
            port=6379, 
            db=0, 
            decode_responses=True, 
            socket_timeout=5.0
        )
        r.ping()
        print("✅ Connection Successful with 'localhost'!")
    except Exception as e2:
        print(f"❌ Connection Failed with 'localhost': {e2}")
