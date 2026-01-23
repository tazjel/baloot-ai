import os
import sys
import json
import logging
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

# Load Environment Variables (e.g. GEMINI_API_KEY)
# Try standard .env and .env.local
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env.local'))

from ai_worker.llm_client import GeminiClient

# Configuration
LOG_FILE = os.path.join("logs", "server_manual.log")
API_URL = "http://localhost:8000/submit_training"
TARGET_TEAM = "us" # Analyze mistakes for "us" (Bottom/Top) in simulated games? 
# Actually, in simulations, we usually want to analyze the LOSING team.
# But for now, let's focus on finding mistakes for "Bottom" (Player 0) or generic analysis.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - Scout - %(levelname)s - %(message)s')
logger = logging.getLogger("Scout")

class Scout:
    def __init__(self):
        self.gemini = GeminiClient()
        self.processed_games = set()

    def parse_logs(self, filepath):
        """
        Parse the log file and group events by game_id.
        Returns a dict: { game_id: [event_dict, ...] }
        """
        logger.info(f"Parsing log file: {filepath}")
        if not os.path.exists(filepath):
            logger.error("Log file not found.")
            return {}

        games = {}
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if "[EVENT]" in line:
                    try:
                        # Extract JSON part after [EVENT]
                        json_str = line.split("[EVENT]", 1)[1].strip()
                        event = json.loads(json_str)
                        
                        game_id = event.get('game_id')
                        if game_id and game_id != "GLOBAL":
                            if game_id not in games:
                                games[game_id] = []
                            games[game_id].append(event)
                    except Exception as e:
                        continue 
        
        logger.info(f"Found {len(games)} games in logs.")
        return games

    def identify_lost_matches(self, games):
        """
        Filter for Completed matches where we (or a specific team) lost.
        For simulation purpose, we might just look for CLOSE games or ANY loss.
        """
        candidates = []
        for game_id, events in games.items():
            # Check for GAME_END or ROUND_END
            is_complete = any(e['event'] == 'GAME_END' or e['event'] == 'ROUND_END' for e in events)
            
            if is_complete:
                # Naive check: did we log the winner?
                # Let's assume we analyze ALL complete games for now to find bad moves.
                candidates.append((game_id, events))
        
        return candidates

    def analyze_match(self, game_id, events):
        """
        Send match history to Gemini to find a CRITICAL mistake.
        """
        logger.info(f"Analyzing Match: {game_id} ({len(events)} events)")
        
        # 1. Construct History String
        history_summary = []
        for e in events:
            # Simplify event for token efficiency
            details = e.get('details', {})
            evt_type = e.get('event')
            timestamp = datetime.fromtimestamp(e.get('timestamp', 0)).strftime('%H:%M:%S')
            
            if evt_type == "CARD_PLAYED":
                summary = f"[{timestamp}] P{e.get('player_index')} played {details.get('card')}"
            elif evt_type == "BID_PLACED":
                summary = f"[{timestamp}] P{e.get('player_index')} bid {details.get('bid_name')}"
            elif evt_type == "TRICK_WIN":
                summary = f"[{timestamp}] P{details.get('winner')} won trick (Runs: {details.get('points')})"
            elif evt_type == "ROUND_END":
                summary = f"[{timestamp}] ROUND END. Score: {details}"     
            else:
                summary = f"[{timestamp}] {evt_type}: {details}"
                
            history_summary.append(summary)
            
        full_text = "\n".join(history_summary)
        
        # 2. Ask Gemini
        prompt = f"""
        You are 'The Scout', an AI analyzing Baloot game logs to find training data.
        
        Analyze this match log. Find ONE critical mistake made by 'Me' (Player 0) or 'Partner' (Player 2).
        The mistake could be a bad bid or a bad card play that cost the team points or the game.
        
        Match Log:
        {full_text}
        
        Output JSON Format suitable for training:
        {{
            "found_mistake": true,
            "contextHash": "{game_id}_analysis",
            "gameState": {{
                "description": "Reconstruct the approximate game state at the moment of the mistake.",
                "players": [
                    {{ "name": "Me", "position": "Bottom", "hand": [] }}, 
                    {{ "name": "Right", "position": "Right", "hand": [] }},
                    {{ "name": "Partner", "position": "Top", "hand": [] }},
                    {{ "name": "Left", "position": "Left", "hand": [] }}
                ],
                "bid": {{ "type": "SUN", "suit": null }} 
            }},
            "badMove": {{ "action": "Played 7-S" }},
            "correctMove": {{ "action": "Play A-S" }},
            "reason": "Expert explanation of why the move was bad and what should have been done."
        }}
        
        If no obvious mistake found, return {{ "found_mistake": false }}.
        """
        
        try:
            # We use the raw model access here since we have a custom prompt
            response = self.gemini.model.generate_content(prompt)
            result_text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(result_text)
            return result
        except Exception as e:
            logger.error(f"Gemini Analysis Failed: {e}")
            return None

    def submit_training_example(self, data):
        """
        POST the finding to the API.
        """
        logger.info("Submitting training example...")
        try:
            # Need to stringify internal JSONs because the API expects JSON strings for some fields
            payload = {
                "contextHash": data.get("contextHash", f"scout_{int(time.time())}"),
                "gameState": json.dumps(data.get("gameState")),
                "badMove": json.dumps(data.get("badMove")),
                "correctMove": json.dumps(data.get("correctMove")),
                "reason": data.get("reason"),
                "imageFilename": "scout_generated" # Marker
            }
            
            res = requests.post(API_URL, json=payload)
            if res.status_code == 200:
                logger.info("Successfully submitted training example!")
            else:
                logger.error(f"API Error: {res.text}")
                
        except Exception as e:
            logger.error(f"Submission failed: {e}")

    def run(self):
        games = self.parse_logs(LOG_FILE)
        candidates = self.identify_lost_matches(games)
        
        logger.info(f"Identified {len(candidates)} candidate matches for analysis.")
        
        for game_id, events in candidates:
            analysis = self.analyze_match(game_id, events)
            if analysis and analysis.get('found_mistake'):
                logger.info(f"Mistake found in Game {game_id}: {analysis.get('reason')}")
                self.submit_training_example(analysis)
            else:
                logger.info(f"No clear mistake found in Game {game_id}")

if __name__ == "__main__":
    scout = Scout()
    scout.run()
