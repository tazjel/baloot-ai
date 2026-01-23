import time
import json
import os
import logging
from game_engine.arena import Arena

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutoPlay")

def run_campaign(num_games=10):
    arena = Arena()
    results = []
    
    os.makedirs("matches", exist_ok=True)
    
    logger.info(f"Starting Campaign of {num_games} matches...")
    start_time = time.time()
    
    wins = {"us": 0, "them": 0, "draw": 0}
    
    for i in range(num_games):
        match_id = f"sim_{int(time.time())}_{i}"
        try:
            res = arena.run_match(match_id)
            
            winner = res.get('winner')
            if winner == 'us': wins['us'] += 1
            elif winner == 'them': wins['them'] += 1
            else: wins['draw'] += 1
            
            # Save Match Log
            match_file = f"matches/{match_id}.json"
            with open(match_file, "w") as f:
                json.dump(res, f, indent=2)
                
            logger.info(f"Match {i+1}/{num_games} - Winner: {winner} - Steps: {res.get('steps')}")
            
        except Exception as e:
            logger.error(f"Match {i} failed: {e}")
            
    duration = time.time() - start_time
    logger.info(f"Campaign Finished in {duration:.2f}s")
    logger.info(f"Results: {wins}")
    
if __name__ == "__main__":
    run_campaign(5) # Run small batch first
