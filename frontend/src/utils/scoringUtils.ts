/**
 * scoringUtils.ts — Card point values, strength rankings, and score calculation.
 * 
 * Contains POINT_VALUES, STRENGTH_ORDER, card strength computation,
 * and final score calculation with doubling/kaboot multipliers.
 */
import { CardModel, Rank, Suit } from "../types";

// Point values for scoring (abont)
export const POINT_VALUES = {
    SUN: { [Rank.Ace]: 11, [Rank.Ten]: 10, [Rank.King]: 4, [Rank.Queen]: 3, [Rank.Jack]: 2, [Rank.Nine]: 0, [Rank.Eight]: 0, [Rank.Seven]: 0 },
    HOKUM: { [Rank.Jack]: 20, [Rank.Nine]: 14, [Rank.Ace]: 11, [Rank.Ten]: 10, [Rank.King]: 4, [Rank.Queen]: 3, [Rank.Eight]: 0, [Rank.Seven]: 0 }
};

// Strength for winning tricks (higher index = stronger)
export const STRENGTH_ORDER = {
    SUN: [Rank.Seven, Rank.Eight, Rank.Nine, Rank.Jack, Rank.Queen, Rank.King, Rank.Ten, Rank.Ace],
    HOKUM_TRUMP: [Rank.Seven, Rank.Eight, Rank.Queen, Rank.King, Rank.Ten, Rank.Ace, Rank.Nine, Rank.Jack],
    HOKUM_NORMAL: [Rank.Seven, Rank.Eight, Rank.Nine, Rank.Jack, Rank.Queen, Rank.King, Rank.Ten, Rank.Ace]
};

export const getCardStrength = (card: CardModel, mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    if (mode === 'SUN') {
        return STRENGTH_ORDER.SUN.indexOf(card.rank);
    } else {
        if (trumpSuit && card.suit === trumpSuit) {
            return 100 + STRENGTH_ORDER.HOKUM_TRUMP.indexOf(card.rank);
        }
        return STRENGTH_ORDER.HOKUM_NORMAL.indexOf(card.rank);
    }
};

/**
 * Calculate Score with Multipliers (Doubling) and Kaboot.
 * Receives separate raw card points and project points.
 */
export const calculateFinalScore = (
    rawCardPoints: number,
    projectPoints: number,
    isKaboot: boolean,
    mode: 'SUN' | 'HOKUM',
    doublingLevel: number,
    isWinner: boolean
): number => {
    // Kaboot Logic
    if (isKaboot) {
        if (!isWinner) return 0;
        if (mode === 'HOKUM') return 25 + (projectPoints / 10);
        return 44;
    }

    // Standard Logic
    let gamePoints = 0;
    const totalRaw = rawCardPoints + projectPoints;

    if (mode === 'SUN') {
        gamePoints = Math.round((totalRaw * 2) / 10);
    } else {
        gamePoints = Math.round(totalRaw / 10);
    }

    // Doubling
    if (doublingLevel > 1) {
        gamePoints *= doublingLevel;
    }

    return gamePoints;
};
