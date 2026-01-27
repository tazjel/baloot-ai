
import time
import sys
import os
sys.path.append(os.getcwd())

from game_engine.models.card import Card
from ai_worker.mcts.fast_game import FastGame
from ai_worker.mcts.mcts import MCTSSolver

def run_solver_benchmark():
    print("--- BENCHMARKING MCTS SOLVER ---")
    
    # Setup: 2 Cards left (Endgame trivial)
    # Bottom: [AS, KS]
    # Right: [QS, JS]
    # Top: [9S, 8S]
    # Left: [7S, AD] 
    
    # Logic: Bottom should play AS first to win securely.
    
    hands = [
        [Card('S','A'), Card('S','K')],
        [Card('S','Q'), Card('S','J')],
        [Card('S','9'), Card('S','8')],
        [Card('S','7'), Card('D','A')] 
    ]
    
    game = FastGame(hands, trump='S', mode='HOKUM', current_turn=0, dealer_index=0)
    
    solver = MCTSSolver()
    
    start = time.time()
    best_move_idx = solver.search(game, timeout_ms=200) # 200ms budget
    end = time.time()
    
    print(f"Time Taken: {(end-start)*1000:.2f}ms")
    print(f"Best Move Index: {best_move_idx}")
    
    # Index 0 is AS, Index 1 is KS. Both are winning, but let's see stats.
    # (Actually in MCTS stats printing handles debugging usually)
    
    print("MCTS Solver completed.")

if __name__ == "__main__":
    run_solver_benchmark()
