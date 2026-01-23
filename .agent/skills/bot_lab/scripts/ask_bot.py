import argparse
import json
import sys
import os

# Ensure we can import bot_agent
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
sys.path.append(project_root)

try:
    from bot_agent import BotAgent
except ImportError as e:
    print(f"Error importing BotAgent: {e}")
    print(f"PYTHONPATH: {sys.path}")
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description='Ask the Bot what to do in a given state.')
    parser.add_argument('--state', type=str, help='Path to JSON game state file (optional)')
    parser.add_argument('--player', type=int, default=0, help='Player Index (0-3) to simulate')
    return parser.parse_args()

def interactive_mode():
    print("\n=== Interactive Bot Lab ===")
    print("Enter the game details to query the bot.\n")
    
    game_mode = input("Game Mode (SUN/HOKUM) [SUN]: ").strip().upper() or "SUN"
    
    print("\nEnter your hand (space separated, e.g., 'Ah Kh 10s'):")
    hand_input = input("> ").strip()
    hand_cards = []
    if hand_input:
        for c in hand_input.split():
            # Basic parsing: "Ah" -> rank=A, suit=h
            rank = c[:-1]
            suit_char = c[-1].lower()
            suit_map = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}
            suit = suit_map.get(suit_char, '♥') # Default to hearts if invalid char
            hand_cards.append({"rank": rank, "suit": suit})
            
    print("\nPhase (BIDDING/PLAYING) [PLAYING]:")
    phase = input("> ").strip().upper() or "PLAYING"
    
    played_cards = []
    if phase == "PLAYING":
        print("\nCards currently on table (space separated, or empty):")
        table_input = input("> ").strip()
        if table_input:
             for c in table_input.split():
                rank = c[:-1]
                suit_char = c[-1].lower()
                suit_map = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}
                suit = suit_map.get(suit_char, '♥')
                played_cards.append({"rank": rank, "suit": suit})

    # Construct minimal state
    state = {
        "phase": phase,
        "gameMode": game_mode,
        "trumpSuit": "D" if game_mode == "HOKUM" else None, # Simplified
        "players": [
            { "index": 0, "hand": hand_cards, "position": "Bottom" },
             { "index": 1, "hand": [], "position": "Right" },
              { "index": 2, "hand": [], "position": "Top" },
               { "index": 3, "hand": [], "position": "Left" }
        ],
        "tableCards": played_cards, # Assuming this is current trick
        "playedCards": [], # History
        "currentRoundTricks": []
    }
    return state

def main():
    args = parse_args()
    
    game_state = None
    
    if args.state:
        try:
            with open(args.state, 'r') as f:
                game_state = json.load(f)
        except FileNotFoundError:
            print(f"Error: State file {args.state} not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {args.state}")
            sys.exit(1)
    else:
        game_state = interactive_mode()
        
    print(f"\n--- Analysis (Player {args.player}) ---")
    print(f"Mode: {game_state.get('gameMode', 'Unknown')}")
    print(f"Phase: {game_state.get('phase', 'Unknown')}")
    
    bot = BotAgent()
    try:
        decision = bot.get_decision(game_state, args.player)
        print("\n>>> BOT DECISION <<<")
        print(json.dumps(decision, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\nError getting decision: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
