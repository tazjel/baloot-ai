
import os
import google.generativeai as genai
import logging
# from server.settings import GEMINI_API_KEY # Removed
from server.common import logger
from dotenv import load_dotenv

# Ensure env is loaded
if not os.environ.get("GEMINI_API_KEY"):
    load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))

# Configure API
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY not found in environment!")

class GeminiClient:
    def __init__(self, model_name="gemini-flash-latest"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        
    def analyze_image(self, image_bytes, mime_type="image/jpeg"):
        """Analyze an image byte stream."""
        try:
            prompt = "Analyze this screenshot of a Baloot game. Identify the cards on the table, the user's hand, the scores, and the current bid/trump. Return JSON."
            
            response = self.model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": image_bytes}
            ])
            return response.text
        except Exception as e:
            logger.error(f"Gemini Image Analysis Failed: {e}")
            return None

    def analyze_video(self, video_path, mime_type="video/mp4"):
        """Analyze a video file."""
        try:
            # File API upload is required for video
            video_file = genai.upload_file(path=video_path)
            
            # Wait for processing? Usually quick for small calls, but loop might be needed.
            # For now, simplistic implementation.
            
            prompt = "Analyze this video of a Baloot game. Describe the flow of the game, any mistakes made, and the final outcome."
            
            response = self.model.generate_content([prompt, video_file])
            return response.text
        except Exception as e:
            logger.error(f"Gemini Video Analysis Failed: {e}")
            return None

    def analyze_hand(self, context, examples=None):
        """
        Analyze a hand and recommend a move.
        context: Dict containing hand, table, scores, etc.
        examples: List of few-shot examples.
        """
        try:
            prompt_parts = []
            
            # System Prompt
            system_prompt = """You are a Baloot Grandmaster. Analyze the current game state and recommend the best move. 
            Consider:
            1. The Game Mode (Sun/Hokum).
            2. The Trump Suit (if Hokum).
            3. The cards on the table.
            4. Your hand.
            5. The scores and potential risks (eating lots of points).
            
            Response Format: JSON { "action": "PLAY", "card": "RankSuit", "reasoning": "..." }
            """
            prompt_parts.append(system_prompt)
            
            # Few-Shot Examples (RAG)
            if examples:
                prompt_parts.append("Here are some examples of correct play in similar situations:\n")
                for ex in examples:
                    prompt_parts.append(f"State: {ex['state']}\nCorrect Move: {ex['correct_move']}\nReasoning: {ex['reason']}\n---\n")
            
            # Current Context
            import json
            prompt_parts.append(f"Current Game State:\n{json.dumps(context, indent=2)}")
            
            response = self.model.generate_content(prompt_parts)
            return response.text
        except Exception as e:
            logger.error(f"Gemini Hand Analysis Failed: {e}")
            return None

    def generate_scenario_from_text(self, text):
        """Generate a Baloot game scenario JSON from natural language."""
        try:
            prompt = f"""Generate a valid Baloot Game State JSON from this description: "{text}".
            Include players, hands, table cards, bid, and trump.
            JSON:
            """
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini Scenario Generation Failed: {e}")
            return None

    def analyze_match_history(self, history):
        """Analyze a full match history."""
        try:
            import json
            history_str = json.dumps(history[:50]) # Truncate to avoid token limits if huge
            
            prompt = f"""Analyze this Baloot match history. Identify the turning point and any mistakes.
            Return a purely JSON response with this structure:
            {{
                "summary": "text summary",
                "moments": [
                    {{
                        "context_hash": "hash_if_available", 
                        "description": "Critical moment description",
                        "correct_move": "CardRank+Suit", 
                        "reasoning": "Why this was the mistake/turning point"
                    }}
                ]
            }}
            Do NOT use markdown code blocks. Just raw JSON.
            History: {history_str}
            """
             
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini Match Analysis Failed: {e}")
            return None
