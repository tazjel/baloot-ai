import sys
import os
import re
import argparse
from datetime import datetime

def analyze_log(log_path):
    if not os.path.exists(log_path):
        print(f"❌ Log file not found: {log_path}")
        return

    print(f"🔍 Analyzing {log_path}...")
    
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    errors = []
    suspicious = []
    game_starts = 0
    game_ends = 0
    
    # regex for timestamps if needed: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}
    
    for i, line in enumerate(lines):
        line = line.strip()
        if "ERROR" in line:
            errors.append((i+1, line))
        elif "Exception" in line or "Traceback" in line:
            errors.append((i+1, line))
        elif "CRITICAL" in line:
             errors.append((i+1, line))
             
        if "GAME START" in line:
            game_starts += 1
        if "GAME_END" in line or "GamePhase.GAMEOVER" in line:
            game_ends += 1
            
        # Detect Lag (heuristic)
        if "Latency" in line:
             # Extract duration
             # Auto-Play Decision Latency for Bot: 0.1234s
             match = re.search(r'Latency.*:\s*([\d\.]+)s', line)
             if match:
                  dur = float(match.group(1))
                  if dur > 1.0:
                       suspicious.append((i+1, f"High Latency: {dur}s - {line}"))

    print(f"\n📊 Summary:")
    print(f"   Lines Read: {len(lines)}")
    print(f"   Game Starts: {game_starts}")
    print(f"   Game Ends: {game_ends}")
    print(f"   Errors Found: {len(errors)}")
    print(f"   Suspicious Events: {len(suspicious)}")

    if errors:
        print("\n❌ Errors:")
        for ln, msg in errors[-5:]: # Show last 5
            print(f"   [L{ln}] {msg}")
            
    if suspicious:
        print("\n⚠️ Suspicious (High Latency > 1.0s):")
        for ln, msg in suspicious[-5:]:
             print(f"   [L{ln}] {msg}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?', default='logs/server_manual.log')
    args = parser.parse_args()
    
    analyze_log(args.file)
