import sys
import os
import time
import cProfile
import pstats
import logging
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_engine.logic.game import Game
from game_engine.models.player import Player
from bot_agent import BotAgent
from server.bidding_engine import BidType

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Profiler")

class HeadlessGame(Game):
    """Subclass of Game that mocks socket interactions."""
    def __init__(self, room_id):
        super().__init__(room_id)
        # Mocking generic socket/timer interactions if any
        self.timer = MagicMock()
    
    # Override emit to do nothing
    def emit(self, event, data):
        pass

def run_simulation():
    game = HeadlessGame("test_room")
    
    # Add 4 Bot Players
    bot_agent = BotAgent()
    game.add_player("p1", "Saad (Bot)")
    game.add_player("p2", "Khalid (Bot)")
    game.add_player("p3", "Noura (Bot)")
    game.add_player("p4", "Abu Fahad (Bot)")
    
    # Start Round (Manually triggering state)
    game.players[0].hand = [] # Logic populates this
    # We need to simulate the distribution.
    # Actually, Game logic has dealing.
    
    game.deck.shuffle()
    # Deal 5 cards
    for p in game.players:
        # Deal 5 cards. deal(n) returns a list of n cards.
        p.hand = game.deck.deal(5)
    
    # Force bidding phase
    game.phase = "BIDDING"
    game.current_turn = 0
    game.dealer_index = 3
    
    print("Starting Profiling Loop...")
    
    start_time = time.time()
    decisions = 0
    
    # Simulate 100 decisions
    profiler = cProfile.Profile()
    profiler.enable()
    
    for _ in range(100):
        # Fake a turn for player 0
        state = game.get_game_state()
        
        # Measure Bot Decision
        try:
            decision = bot_agent.get_decision(state, 0)
            decisions += 1
        except Exception as e:
            print(f"Error in decision: {e}")
            break
            
    profiler.disable()
    end_time = time.time()
    
    print(f"\nCompleted {decisions} decisions in {end_time - start_time:.4f}s")
    print(f"Average: {(end_time - start_time)/decisions*1000:.2f}ms per decision")
    
    # Stats
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats(20)

if __name__ == "__main__":
    run_simulation()
