import json
import sys
import argparse

def print_tree(data, indent=0, key="Root"):
    space = "  " * indent
    if isinstance(data, dict):
        print(f"{space}📂 {key}")
        for k, v in data.items():
            print_tree(v, indent + 1, k)
    elif isinstance(data, list):
        print(f"{space}📂 {key} (List[{len(data)}])")
        for i, item in enumerate(data):
            print_tree(item, indent + 1, f"Item {i}")
    else:
        # Leaf
        print(f"{space}🔹 {key}: {data}")

def visualize_game_state(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
            
        print(f"🎨 Visualizing Game State from: {file_path}")
        print("="*40)
        
        # Custom "Baloot" View for easier reading
        if "players" in state:
            print(f"🏠 Room: {state.get('roomId')} | Phase: {state.get('phase')}")
            print(f"🏆 Scores - Us: {state.get('teamScores', {}).get('us')} | Them: {state.get('teamScores', {}).get('them')}")
            print(f"🃏 Trump: {state.get('trumpSuit')} | Mode: {state.get('gameMode')}")
            print("-" * 20)
            
            for p in state['players']:
                idx = p.get('index')
                pos = p.get('position')
                tm = p.get('team')
                hand_len = len(p.get('hand', []))
                print(f"👤 [{idx}] {pos} ({tm}) - Hand: {hand_len} cards")
                # Print Hand compact
                cards = [f"{c['rank']}{c['suit']}" for c in p.get('hand', [])]
                print(f"    Cards: {', '.join(cards)}")
                
        else:
            # Fallback to generic tree
            print_tree(state)
            
    except Exception as e:
        print(f"❌ Error reading/parsing file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help="Path to JSON state dump")
    args = parser.parse_args()
    
    visualize_game_state(args.file)
