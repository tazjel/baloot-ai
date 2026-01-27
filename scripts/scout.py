
import json
import os
import sys
import logging
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.logging_utils import LOG_FILE
from ai_worker.llm_client import GeminiClient
from server.common import logger # Use common logger

# Configuration
# Ensuring backend/data/training exists
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_worker", "data", "training"))
MISTAKES_FILE = os.path.join(DATA_DIR, "mistakes_extracted.json")
os.makedirs(DATA_DIR, exist_ok=True)

def parse_logs(log_file_path):
    """Parses the log file and groups events by game_id."""
    games = {}
    
    if not os.path.exists(log_file_path):
        print(f"Log file not found: {log_file_path}")
        return games

    print(f"Parsing logs from: {log_file_path}")
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "[EVENT]" in line:
                try:
                    # Extract JSON payload after [EVENT]
                    json_str = line.split("[EVENT]", 1)[1].strip()
                    event = json.loads(json_str)
                    
                    game_id = event.get("game_id")
                    if not game_id or game_id == "GLOBAL":
                        continue
                        
                    if game_id not in games:
                        games[game_id] = {
                            "events": [], 
                            "start_time": event.get("timestamp"),
                            "is_complete": False,
                            "winner": None,
                            "scores": {"us": 0, "them": 0}
                        }
                    
                    games[game_id]["events"].append(event)
                    
                    if event.get("event") == "GAME_END":
                        games[game_id]["is_complete"] = True
                        games[game_id]["winner"] = event.get("details", {}).get("winner")
                        games[game_id]["scores"] = event.get("details", {}).get("final_score", {})

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    # print(f"Error parsing line: {e}")
                    continue
    
    return games

def reconstruct_game(game_data):
    """
    Reconstructs the game state from events. 
    This is complex; for now, we just pass the raw event stream or 
    key snapshots if available.
    """
    # TODO: Implement full state reconstruction replay if needed.
    return game_data["events"]

def identify_mistakes(games):
    """
    Identifies games worth analyzing (e.g., User losses).
    """
    candidates = []
    for game_id, data in games.items():
        if data["is_complete"]:
            # Simple heuristic: Analyze lost games (Assuming User is team 'us' or 0/2)
            # Adjust heuristic as needed.
            # detailed criteria can be added here.
            candidates.append(data)
    return candidates

def main():
    print("Starting Scout...")
    print(f"Analysis Output Dir: {DATA_DIR}")
    
    # 1. Parse Logs
    games = parse_logs(LOG_FILE)
    print(f"Found {len(games)} games in logs.")
    
    # 2. Filter Candidates
    candidates = identify_mistakes(games)
    print(f"Identified {len(candidates)} completed games for analysis.")
    
    if not candidates:
        print("No candidates found. Exiting.")
        return

    # 3. Analyze with Gemini (Simulated or Real)
    gemini = GeminiClient()
    
    extracted_mistakes = []
    
    # Limit to 5 most recent for now to save tokens/time
    for game in candidates[-5:]: 
        game_id = game["events"][0]["game_id"]
        print(f"Analyzing Game: {game_id}...")
        
        # In a real implementation, we would replay the game state-by-state 
        # and ask Gemini to critique specific moves. 
        # For now, we assume we want to analyze the whole match or identifying 
        # a specific 'blunder' via LLM is the goal.
        
        # Converting event stream to a text summary for the LLM
        # This is a simplification.
        
        analysis = gemini.analyze_match_history(game["events"])
        if analysis:
            print(f"Analysis for {game_id}: Received.")
            import re
            match = re.search(r'\{.*\}', analysis, re.DOTALL)
            if match:
                json_candidate = match.group(0)
                try:
                    analysis_json = json.loads(json_candidate)
                    extracted_mistakes.append({
                        "game_id": game_id,
                        "analysis": analysis_json
                    })
                except json.JSONDecodeError:
                     print(f"Failed to parse JSON from analysis for {game_id}")
                     extracted_mistakes.append({
                        "game_id": game_id,
                        "analysis_raw": analysis
                     })
            else:
                 print(f"No JSON found in analysis for {game_id}")
                 extracted_mistakes.append({
                    "game_id": game_id,
                    "analysis_raw": analysis
                 })
        else:
            print(f"Skipping {game_id} (Analysis failed).")
            
    # 4. Save Results
    with open(MISTAKES_FILE, 'w', encoding='utf-8') as f:
        json.dump(extracted_mistakes, f, indent=2)
        
    print(f"Saved {len(extracted_mistakes)} analyses to {MISTAKES_FILE}")

if __name__ == "__main__":
    main()
