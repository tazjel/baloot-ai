import os
import random
import logging
import time
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional
from ai_worker.personality import PersonalityProfile, BALANCED

# Load env variables
# Assuming this runs from project root or server, we need to find .env.local
# Strategy: Look up 2 dirs from here
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.local')
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class DialogueSystem:
    def __init__(self):
        self.logger = logging.getLogger("DialogueSystem")
        self.model = None
        self._last_call_time = 0
        self._setup_model()

    def _setup_model(self):
        if not GEMINI_API_KEY:
            self.logger.warning("GEMINI_API_KEY not found. DialogueSystem disabled (fallback only).")
            return

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash',
                generation_config=genai.GenerationConfig(
                    temperature=1.1,
                    top_p=0.95,
                    max_output_tokens=40,
                )
            )
            self.logger.info("DialogueSystem initialized with Gemini 1.5 Flash")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini: {e}")

    def generate_reaction(self, player_name: str, personality: PersonalityProfile, context: str, game_state: dict = None) -> Optional[str]:
        """
        Generates a reaction line. Returns None if generation fails or is rate-limited.
        This method is BLOCKING and should be run in a thread.
        """
        # Rate Limit: Don't spam Gemini more than once every 2 seconds globally (simple check)
        # In a real system we'd rate limit per-bot.
        if time.time() - self._last_call_time < 2.0:
            return self._get_fallback_message(personality)

        # 50% Chance to just use fallback/silence to avoid noise?
        # Let's say for "Trash Talk" feature verification, we want high frequency: 100%
        
        if not self.model:
            return self._get_fallback_message(personality)

        prompt = self._construct_prompt(player_name, personality, context)

        try:
            self._last_call_time = time.time()
            response = self.model.generate_content(prompt)
            if response.text:
                text = response.text.strip().replace('"', '').replace("'", "")
                # remove prefixes like "Reaction:" if any
                if ":" in text:
                    text = text.split(":", 1)[1].strip()
                return text
            return self._get_fallback_message(personality)
        except Exception as e:
            self.logger.error(f"Gemini generation error: {e}")
            return self._get_fallback_message(personality)

    def _construct_prompt(self, player_name: str, personality: PersonalityProfile, context: str) -> str:
        return f"""
Roleplay: You are {player_name}, a Baloot card game player in Saudi Arabia.
Personality: {personality.description} (Key traits: {personality.name})
Language: Arabic (Saudi Hejazi/Najdi Dialect). Use terms like "Sira", "Hakam", "Kaboot", "Akal", "Ya Ghashim", "Bunt", "Ikka".
Current Situation: {context}

Task: Shout a short, reactive 1-sentence comment (max 6 words). 
- If you are winning/aggressive, trash talk in Arabic.
- If you are losing/conservative, complain or apply "Hasad" in Arabic.
- Be funny, authentic, and use common Saudi interjections (Wallah, Ya Akhi, etc.).
- OUTPUT ARABIC TEXT ONLY.
"""

    def _get_fallback_message(self, personality: PersonalityProfile) -> str:
        # Simple Arabic fallbacks
        fallbacks = ["يلا العب!", "وش ذا اللعب؟", "سرا!", "يا هووو", "بسرعة يا كابتن"]
        return random.choice(fallbacks)
