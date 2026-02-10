/**
 * akkaUtils.ts — Akka (Boss Card) declaration and Kawesh logic.
 * 
 * Contains eligibility checks for Akka declarations, hand scanning
 * for available Akka cards, and Kawesh (redeal) eligibility.
 */
import { CardModel, Rank, Suit, TableCardMetadata } from "../types";
import { STRENGTH_ORDER } from "./scoringUtils";

/**
 * Extracts a consistent card key ("rank+suit" e.g. "A♠") from any card format.
 * Handles: CardModel objects, flat dicts {suit, rank}, and nested {card: ...} wrappers.
 */
export const cardKey = (card: any): string => {
    if (!card) return '';
    if (card.card) return cardKey(card.card);
    return `${card.rank}${card.suit}`;
};

/**
 * Builds a Set of all played card keys from round history.
 */
export const buildPlayedCardsSet = (
    currentRoundTricks: any[] = [],
    tableCards: any[] = []
): Set<string> => {
    const played = new Set<string>();

    for (const trick of currentRoundTricks) {
        const cards = trick.cards || [];
        for (const c of cards) {
            const key = cardKey(c);
            if (key) played.add(key);
        }
    }

    for (const tc of tableCards) {
        const key = cardKey(tc.card || tc);
        if (key) played.add(key);
    }

    return played;
};

/**
 * Checks if a specific card qualifies as an Akka (Boss Card) declaration.
 *
 * Rules (must match backend ProjectManager.check_akka_eligibility):
 *   1. Mode: HOKUM only.
 *   2. Table must be empty (player is leading).
 *   3. Card suit must NOT be trump.
 *   4. Card rank must NOT be Ace (self-evident boss).
 *   5. Card must be the highest remaining card of its suit.
 */
export const canDeclareAkka = (
    card: CardModel,
    hand: CardModel[],
    tableCards: { card: CardModel, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null,
    currentRoundTricks: any[] = []
): boolean => {
    if (mode !== 'HOKUM') return false;
    if (tableCards.length > 0) return false;
    if (trumpSuit && card.suit === trumpSuit) return false;
    if (card.rank === Rank.Ace) return false;

    const playedCards = buildPlayedCardsSet(currentRoundTricks, []);
    const order = STRENGTH_ORDER.HOKUM_NORMAL;
    const myRankIdx = order.indexOf(card.rank);
    if (myRankIdx === -1) return false;

    for (let i = myRankIdx + 1; i < order.length; i++) {
        const higherRank = order[i];
        const sig = `${higherRank}${card.suit}`;

        if (playedCards.has(sig)) continue;

        const weHoldIt = hand.some(c => c.rank === higherRank && c.suit === card.suit);
        if (weHoldIt) return false;

        return false;
    }

    return true;
};

/**
 * Scans the entire hand to check if ANY card is eligible for Akka.
 */
export const scanHandForAkka = (
    hand: CardModel[],
    tableCards: { card: CardModel, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null,
    currentRoundTricks: any[] = []
): boolean => {
    if (mode !== 'HOKUM') return false;
    if (tableCards.length > 0) return false;

    for (const card of hand) {
        if (canDeclareAkka(card, hand, tableCards, mode, trumpSuit, currentRoundTricks)) {
            return true;
        }
    }
    return false;
};

/**
 * Checks if a user can declare "Kawesh" (Redeal).
 * Rules: Hand must have NO Court Cards (A, K, Q, J, 10).
 */
export const canDeclareKawesh = (hand: CardModel[]): boolean => {
    const courtCards = [Rank.Ace, Rank.King, Rank.Queen, Rank.Jack, Rank.Ten];
    const hasPoints = hand.some(c => courtCards.includes(c.rank));
    return !hasPoints;
};
