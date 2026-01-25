import redis
import sys

print("Pinging Redis at redis://localhost:6379/0...")
try:
    r = redis.from_url("redis://localhost:6379/0", socket_timeout=5)
    r.ping()
    print("✅ Success! (localhost)")
except Exception as e:
    print(f"❌ Failed (localhost): {e}")

print("Pinging Redis at redis://127.0.0.1:6379/0...")
try:
    r = redis.from_url("redis://127.0.0.1:6379/0", socket_timeout=5)
    r.ping()
    print("✅ Success! (127.0.0.1)")
except Exception as e:
    print(f"❌ Failed (127.0.0.1): {e}")
