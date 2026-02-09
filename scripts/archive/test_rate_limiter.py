import time
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from ai_worker.rate_limiter import TokenBucketRateLimiter

def test_rate_limiter():
    print("=== Testing TokenBucketRateLimiter ===")
    
    # Configure: 5 burst, 60 RPM (1 per sec) for faster testing
    # Actually let's use the production settings to be sure: 10 burst, 10 RPM
    limiter = TokenBucketRateLimiter(capacity=10, refill_rate_per_minute=10)
    
    print(f"Initial Tokens: {limiter.get_status()['tokens']}")
    
    # 1. Burst Test
    print("\n--- Burst Test (Expect 10 successes) ---")
    successes = 0
    start = time.time()
    for i in range(15):
        if limiter.acquire(blocking=False):
            print(f"Request {i+1}: Allowed")
            successes += 1
        else:
            print(f"Request {i+1}: Throttled")
            
    print(f"Total Successes: {successes}")
    if successes == 10:
        print("✅ Burst capacity verified (10).")
    else:
        print(f"❌ Burst failed. Expected 10, got {successes}.")
        
    # 2. Refill Test
    print("\n--- Refill Test (Wait 6s for 1 token) ---")
    time.sleep(6.1)
    
    if limiter.acquire(blocking=False):
        print("✅ Refill verified (Acquired 1 token after wait).")
    else:
        print("❌ Refill failed. Still throttled.")
        
    status = limiter.get_status()
    print(f"\nFinal Status: {status}")

if __name__ == "__main__":
    test_rate_limiter()
