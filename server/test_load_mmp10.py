import asyncio
import socketio
import time
import random
import uuid

SERVER_URL = "https://baloot-server-1076165534376.me-central1.run.app"
NUM_CLIENTS = 40  # Simulate 40 players to test 10 full matches forming

async def simulate_client(client_id):
    sio = socketio.AsyncClient(reconnection=True, reconnection_attempts=5)
    
    match_event = asyncio.Event()
    stats = {
        "client_id": client_id,
        "join_latency": None,
        "match_latency": None,
        "matched": False,
        "error": None
    }
    
    join_time = 0

    @sio.event
    async def connect():
        print(f"[{client_id}] Connected")

    @sio.event
    async def disconnect():
        print(f"[{client_id}] Disconnected")
        
    @sio.event
    async def connect_error(err):
        stats["error"] = f"Connect Error: {err}"
        match_event.set()

    @sio.on("match_found")
    async def on_match_found(data):
        latency = time.time() - join_time
        stats["match_latency"] = latency
        stats["matched"] = True
        print(f"[{client_id}] MATCH FOUND in {latency:.2f}s! Data: {data}")
        match_event.set()

    try:
        await sio.connect(SERVER_URL, transports=['websocket'])
        
        # Jitter start time a bit
        await asyncio.sleep(random.uniform(0.1, 2.0))
        
        join_start = time.time()
        print(f"[{client_id}] Joining queue...")
        
        # Rate limit test for first client: send 6 joins rapidly
        if int(client_id.split('_')[-1]) == 0:
            for _ in range(6):
                await sio.emit("queue_join", {"playerName": f"Player_{client_id}"})
                await asyncio.sleep(0.1)

        # Normal join
        response = await sio.call("queue_join", {"playerName": f"Player_{client_id}"})
        join_time = time.time()
        stats["join_latency"] = join_time - join_start
        print(f"[{client_id}] Queue Join Response: {response} in {stats['join_latency']:.4f}s")
        
        # Wait for match
        try:
            await asyncio.wait_for(match_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            stats["error"] = "Timeout waiting for match"
            print(f"[{client_id}] TIMEOUT")
            
        await sio.disconnect()
    except Exception as e:
        stats["error"] = str(e)
        print(f"[{client_id}] Exception: {e}")
        
    return stats

async def main():
    print(f"Starting M-MP10 Load Test with {NUM_CLIENTS} clients...")
    start_time = time.time()
    
    tasks = []
    for i in range(NUM_CLIENTS):
        client_id = f"tester_{uuid.uuid4().hex[:6]}_{i}"
        tasks.append(simulate_client(client_id))
        
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    print("\n" + "="*40)
    print("LOAD TEST RESULTS")
    print("="*40)
    
    successful_joins = [r for r in results if r['join_latency'] is not None]
    matches = [r for r in results if r['matched']]
    errors = [r for r in results if r['error']]
    
    if successful_joins:
        avg_join = sum(r['join_latency'] for r in successful_joins) / len(successful_joins)
        print(f"Successful Queue Joins: {len(successful_joins)}/{NUM_CLIENTS}")
        print(f"Average Join Latency: {avg_join:.4f}s")
        
    if matches:
        avg_match = sum(r['match_latency'] for r in matches) / len(matches)
        print(f"Matches Formed (Players placed): {len(matches)}")
        print(f"Average Match Formation Latency: {avg_match:.4f}s")
        
    if errors:
        print(f"Errors Encountered: {len(errors)}")
        for e in errors[:5]:
            print(f" - {e['error']}")
            
    print(f"Total Test Time: {total_time:.2f}s")
    
if __name__ == "__main__":
    asyncio.run(main())
