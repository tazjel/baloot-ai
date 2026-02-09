import { GoogleGenAI } from "@google/genai";
import { GameState, PlayerPosition } from "../types";

// Initialize with a fallback to avoid crash if env is missing during init
const apiKey = process.env.API_KEY || 'DUMMY_KEY'; 
const ai = new GoogleGenAI({ apiKey });

// Using Flash for faster responses in a game loop
const MODEL_NAME = 'gemini-2.5-flash';

export const getBotDecision = async (gameState: GameState, playerPos: PlayerPosition): Promise<{ action: string, cardIndex?: number }> => {
  // Silent fallback if no key is present to allow gameplay without AI
  if (!process.env.API_KEY) {
    console.warn("No API Key available for bot decision. Using random fallback.");
    return { action: 'PASS' };
  }

  try {
    const prompt = `
      You are playing a game of Baloot (Saudi Arabian card game).
      Current Game State:
      - Phase: ${gameState.phase}
      - My Position: ${playerPos}
      - Current Floor Card (if bidding): ${gameState.floorCard ? `${gameState.floorCard.rank}${gameState.floorCard.suit}` : 'None'}
      - Current Bid: ${gameState.bid.type || 'None'}
      - Cards on Table: ${gameState.tableCards.map(c => `${c.card.rank}${c.card.suit}`).join(', ')}
      
      Your hand contains valid Baloot cards.
      
      If Phase is BIDDING:
      Return a JSON object with "action" being one of: "SUN", "HOKUM", "PASS".
      Prioritize "PASS" unless you have high cards (Ace, Ten, King).
      
      If Phase is PLAYING:
      Return a JSON object with "action": "PLAY" and "cardIndex" (0-based index of the card to play from hand).
      Pick a valid card to win the trick or follow suit.
      
      Return ONLY valid JSON.
    `;

    const response = await ai.models.generateContent({
      model: MODEL_NAME,
      contents: prompt,
      config: {
        responseMimeType: "application/json"
      }
    });

    const text = response.text;
    if (!text) throw new Error("Empty response");
    
    return JSON.parse(text);

  } catch (error) {
    // Catch 403 Permission Denied or other API errors
    console.error("Gemini API Error (falling back to simple logic):", error);
    return { action: 'PASS', cardIndex: 0 };
  }
};