/**
 * deckUtils.ts — Deck generation.
 * 
 * Creates a shuffled 32-card Baloot deck using Fisher-Yates shuffle.
 */
import { CardModel, Rank, Suit } from "../types";

export const generateDeck = (): CardModel[] => {
    const suits = Object.values(Suit);
    const ranks = Object.values(Rank);
    const deck: CardModel[] = [];

    let idCounter = 1;
    for (const suit of suits) {
        for (const rank of ranks) {
            deck.push({
                id: `${suit}-${rank}-${idCounter++}`,
                suit,
                rank,
                value: 0
            });
        }
    }

    // Fisher-Yates Shuffle
    for (let i = deck.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [deck[i], deck[j]] = [deck[j], deck[i]];
    }

    return deck;
};
