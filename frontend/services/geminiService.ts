import { GameState, PlayerPosition, GamePhase } from "../types";

export const getBotDecision = async (gameState: GameState, playerPos: PlayerPosition): Promise<{ action: string, cardIndex?: number }> => {
  // Simulate "thinking" delay
  // await new Promise(resolve => setTimeout(resolve, 500)); 

  if (gameState.phase === GamePhase.Bidding) {
    // Simple Bidding Logic: 20% chance to buy SUN, 10% HOKUM, else PASS
    const rand = Math.random();
    if (rand < 0.2) return { action: 'SUN' };
    if (rand < 0.3) return { action: 'HOKUM' };
    return { action: 'PASS' };
  }

  if (gameState.phase === GamePhase.Playing) {
    const playerIndex = gameState.players.findIndex(p => p.position === playerPos);
    const hand = gameState.players[playerIndex].hand;

    // Simple Playing Logic: Play valid card (for now random valid)
    // In a real game, you'd check for suit following, etc.
    // Since validation happens in backend/state mostly, we just pick an index.

    const randomIndex = Math.floor(Math.random() * hand.length);
    return { action: 'PLAY', cardIndex: randomIndex };
  }

  return { action: 'PASS' };
};