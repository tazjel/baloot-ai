
import sys
sys.path.append('c:\\Users\\MiEXCITE\\Projects\\baloot-ai')
from game_engine.logic.game import Game

try:
    g = Game("room")
    print(f"Has qayd_state: {hasattr(g, 'qayd_state')}")
    if hasattr(g, 'qayd_state'):
        print(f"qayd_state: {g.qayd_state}")
except Exception as e:
    print(f"Error: {e}")
