import redis
import sys

print("Testing Redis...")
try:
    r = redis.from_url("redis://localhost:6379/0", decode_responses=True, socket_timeout=2.0)
    print("Connected object created.")
    val = r.ping()
    print(f"PING: {val}")
    
    val = r.get("brain:move:FORCE_OVERRIDE_TEST")
    print(f"Key Value: {val}")
    
except Exception as e:
    print(f"Redis Error: {e}")
