/**
 * sortUtils.ts — Hand sorting logic.
 * 
 * Sorts cards by suit grouping with color alternation and
 * power-based internal ordering (mode-aware).
 */
import { CardModel, Rank, Suit } from "../types";
import { STRENGTH_ORDER } from "./scoringUtils";
import { SEQUENCE_ORDER } from "./projectUtils";

/**
 * Returns a numeric rank for sorting.
 * Higher number = Higher priority (appears first in hand).
 */
export const getSortRank = (card: CardModel, mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    if (mode === 'SUN') {
        return STRENGTH_ORDER.SUN.indexOf(card.rank);
    } else {
        if (trumpSuit && card.suit === trumpSuit) {
            return STRENGTH_ORDER.HOKUM_TRUMP.indexOf(card.rank);
        } else {
            return STRENGTH_ORDER.HOKUM_NORMAL.indexOf(card.rank);
        }
    }
};

/**
 * Sorts the hand according to the current game rules.
 * 1. Groups by Suit.
 * 2. Alternates Colors (Red/Black): Spades, Diamonds, Clubs, Hearts.
 * 3. Sorts internal cards by Natural Sequence (A, K, Q, J, 10, 9, 8, 7).
 */
export const sortHand = (hand: CardModel[], mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): CardModel[] => {
    if (!hand) return [];

    const spades = hand.filter(c => c.suit === Suit.Spades);
    const hearts = hand.filter(c => c.suit === Suit.Hearts);
    const clubs = hand.filter(c => c.suit === Suit.Clubs);
    const diamonds = hand.filter(c => c.suit === Suit.Diamonds);

    const sorter = (a: CardModel, b: CardModel) => {
        const idxA = SEQUENCE_ORDER.indexOf(a.rank);
        const idxB = SEQUENCE_ORDER.indexOf(b.rank);
        return idxA - idxB;
    };

    spades.sort(sorter);
    hearts.sort(sorter);
    clubs.sort(sorter);
    diamonds.sort(sorter);

    return [
        ...spades,
        ...diamonds,
        ...clubs,
        ...hearts
    ];
};
