/**
 * trickUtils.ts — Trick resolution and move validation.
 * 
 * Contains trick winner determination, move validity checks, and
 * invalid move reason explanations (for Qayd disputes).
 */
import { CardModel, Rank, Suit, TableCardMetadata } from "../types";
import { getCardStrength } from "./scoringUtils";

export const getTrickWinner = (
    tableCards: { card: CardModel, playedBy: string, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null
): number => {
    if (tableCards.length === 0) return -1;

    const leadSuit = tableCards[0].card.suit;
    let highestStrength = -1;
    let winnerIndex = 0;

    tableCards.forEach((play, index) => {
        const card = play.card;
        let strength = 0;

        if (card.suit === leadSuit || (mode === 'HOKUM' && card.suit === trumpSuit)) {
            strength = getCardStrength(card, mode, trumpSuit);
        } else {
            strength = -1;
        }

        if (strength > highestStrength) {
            highestStrength = strength;
            winnerIndex = index;
        }
    });

    return winnerIndex;
};

export const isValidMove = (
    card: CardModel,
    hand: CardModel[],
    tableCards: { card: CardModel, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null,
    isLocked: boolean = false,
    strictMode: boolean = true
): boolean => {
    if (!strictMode) return true;

    // Lead player
    if (tableCards.length === 0) {
        if (isLocked && mode === 'HOKUM' && trumpSuit && card.suit === trumpSuit) {
            const hasNonTrump = hand.some(c => c.suit !== trumpSuit);
            if (hasNonTrump) return false;
        }
        return true;
    }

    const leadSuit = tableCards[0].card.suit;
    const hasLeadSuit = hand.some(c => c.suit === leadSuit);

    // Rule 1: Must follow suit
    if (hasLeadSuit) {
        if (card.suit !== leadSuit) return false;
        return true;
    }

    // Rule 2: Must cut with trump in Hokum if possible
    if (mode === 'HOKUM' && trumpSuit) {
        const hasTrump = hand.some(c => c.suit === trumpSuit);
        if (hasTrump && card.suit !== trumpSuit) return false;
    }

    return true;
};

/**
 * Explain WHY a move is invalid (for Disputes/Qayd).
 */
export const getInvalidMoveReason = (
    card: CardModel,
    hand: CardModel[],
    tableCards: { card: CardModel, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null,
    isLocked: boolean = false
): string | null => {
    if (tableCards.length === 0) {
        if (isLocked && mode === 'HOKUM' && trumpSuit && card.suit === trumpSuit) {
            const hasNonTrump = hand.some(c => c.suit !== trumpSuit);
            if (hasNonTrump) return "You cannot help (lead trump) when the game is Locked (Doubled)!";
        }
        return null;
    }

    const leadSuit = tableCards[0].card.suit;
    const hasLeadSuit = hand.some(c => c.suit === leadSuit);

    if (hasLeadSuit) {
        if (card.suit !== leadSuit) return `You have ${leadSuit} in your hand! You must follow suit (Renounce).`;
        return null;
    }

    if (mode === 'HOKUM' && trumpSuit) {
        const hasTrump = hand.some(c => c.suit === trumpSuit);
        if (hasTrump && card.suit !== trumpSuit) return `You have Trump (${trumpSuit})! You must Cut the trick since you cannot follow suit.`;
    }

    return null;
};
