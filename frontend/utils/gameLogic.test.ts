
import { describe, it, expect } from 'vitest';
import { canDeclareAkka } from './gameLogic';
import { CardModel, Suit, Rank } from '../types';

// Helper to create card
const createCard = (suit: Suit, rank: Rank): CardModel => ({
    id: `${suit}-${rank}`,
    suit,
    rank,
    value: 0
});

describe('canDeclareAkka', () => {
    const tableEmpty: { card: CardModel }[] = [];
    const currentRoundTricksEmpty: { cards: CardModel[] }[] = [];
    const modeHokum = 'HOKUM';
    const modeSun = 'SUN';
    const trumpSpades = Suit.Spades;

    it('should return false if not HOKUM', () => {
        const card = createCard(Suit.Hearts, Rank.Ace);
        expect(canDeclareAkka(card, [card], tableEmpty, modeSun, null, currentRoundTricksEmpty)).toBe(false);
    });

    it('should return false if not leading (table not empty)', () => {
        const card = createCard(Suit.Hearts, Rank.Ace);
        const table = [{ card: createCard(Suit.Clubs, Rank.Ten) }];
        expect(canDeclareAkka(card, [card], table, modeHokum, trumpSpades, currentRoundTricksEmpty)).toBe(false);
    });

    it('should return false if card is Trump', () => {
        const card = createCard(Suit.Spades, Rank.Ace);
        expect(canDeclareAkka(card, [card], tableEmpty, modeHokum, trumpSpades, currentRoundTricksEmpty)).toBe(false);
    });

    it('should return false for absolute master (Ace of non-trump) as per exclusion rule', () => {
        const card = createCard(Suit.Hearts, Rank.Ace);
        expect(canDeclareAkka(card, [card], tableEmpty, modeHokum, trumpSpades, currentRoundTricksEmpty)).toBe(false);
    });

    it('should return true for King if Ace and Ten are played (Graveyard)', () => {
        const card = createCard(Suit.Hearts, Rank.King);
        // Ace and Ten played
        const tricks = [{ cards: [createCard(Suit.Hearts, Rank.Ace), createCard(Suit.Hearts, Rank.Ten)] }];

        expect(canDeclareAkka(card, [card], tableEmpty, modeHokum, trumpSpades, tricks)).toBe(true);
    });

    it('should return false for King if Ace is played but Ten is missing', () => {
        const card = createCard(Suit.Hearts, Rank.King);
        const tricks = [{ cards: [createCard(Suit.Hearts, Rank.Ace)] }]; // Ten is missing
        expect(canDeclareAkka(card, [card], tableEmpty, modeHokum, trumpSpades, tricks)).toBe(false);
    });

    it('should return false for King if Ace is suspected (not played and not in hand)', () => {
        const card = createCard(Suit.Hearts, Rank.King);
        // Ace is missing (opponent has it presumably)
        expect(canDeclareAkka(card, [card], tableEmpty, modeHokum, trumpSpades, currentRoundTricksEmpty)).toBe(false);
    });

    it('should return false for King if I hold the Ace (I should play Ace first)', () => {
        const king = createCard(Suit.Hearts, Rank.King);
        const ace = createCard(Suit.Hearts, Rank.Ace);
        const hand = [king, ace];

        expect(canDeclareAkka(king, hand, tableEmpty, modeHokum, trumpSpades, currentRoundTricksEmpty)).toBe(false);
    });

    it('should return true for 10 if A and K are played', () => {
        // In Hokum Non-Trump: A > 10 > K > Q ... 
        // Wait, Strength Order for Non-Trump Hokum?
        // GameLogic: STRENGTH_ORDER.HOKUM_NORMAL = [7, 8, 9, J, Q, K, 10, A]
        // So 10 is stronger than K.
        // So if I have 10, I only need to check Ace.

        const ten = createCard(Suit.Hearts, Rank.Ten);
        // Ace played.
        const tricks = [{ cards: [createCard(Suit.Hearts, Rank.Ace)] }];
        // I have K and Q in hand.
        const hand = [ten, createCard(Suit.Hearts, Rank.King)];

        // 10 is 2nd strongest. Ace played. 10 is now master.
        expect(canDeclareAkka(ten, hand, tableEmpty, modeHokum, trumpSpades, tricks)).toBe(true);
    });
});
