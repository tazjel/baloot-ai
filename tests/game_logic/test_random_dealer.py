import random
from game_logic import Game

def test_random_dealer_distribution():
    """Run start_game 100 times and check dealer distribution"""
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for _ in range(100):
        g = Game("test")
        g.add_player("p1", "P1")
        g.add_player("p2", "P2")
        g.add_player("p3", "P3")
        g.add_player("p4", "P4")
        g.start_game()
        counts[g.dealer_index] += 1
        
    print("Dealer Distribution:", counts)
    
    # Assert reasonable distribution (each > 10)
    for i in range(4):
        assert counts[i] > 10, f"Dealer {i} appeared too few times: {counts[i]}"

if __name__ == "__main__":
    test_random_dealer_distribution()
