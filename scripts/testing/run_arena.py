import time
import json
import os
import sys

# Add root to python path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create environment variable to disable Redis in bot_agent
# os.environ["OFFLINE_MODE"] = "true" # Commented out for Production Mode check


from game_engine.arena import Arena
# from bot_agent import bot_agent # No longer needed to import just to patch



def run_batch(num_games=100):
    arena = Arena()
    results = []
    
    start_time = time.time()
    wins = {"us": 0, "them": 0}
    errors = 0
    
    print(f"Starting Batch Simulation of {num_games} games...")
    
    for i in range(num_games):
        match_id = f"sim_{int(time.time())}_{i}"
        try:
            res = arena.run_match(match_id)
            results.append(res)
            
            w = res.get('winner')
            if w: wins[w] += 1
            
            # Progress bar
            if (i+1) % 10 == 0:
                print(f"Completed {i+1}/{num_games} games. Wins: {wins}")
                
        except Exception as e:
            print(f"Match {i} Failed: {e}")
            errors += 1

    total_time = time.time() - start_time
    print(f"\n--- Batch Finished in {total_time:.2f}s ---")
    print(f"Total Games: {num_games}")
    print(f"Win Rate (US): {wins['us']/num_games:.1%}")
    print(f"Win Rate (THEM): {wins['them']/num_games:.1%}")
    print(f"Draws/Incomplete: {num_games - wins['us'] - wins['them']}")
    print(f"Errors: {errors}")
    print(f"Avg Time/Game: {total_time/num_games:.3f}s")
    
    # Save Results
    os.makedirs("candidates", exist_ok=True)
    with open("candidates/arena_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to candidates/arena_results.json")

if __name__ == "__main__":
    count = 100
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    run_batch(count)
