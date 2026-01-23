
const { SUITS, RANKS, POINT_VALUES_SUN, POINT_VALUES_HOKUM, ORDER_SUN, ORDER_HOKUM, ORDER_PROJECTS, PROJECT_TYPES, PROJECT_SCORES } = require('./constants');

// Strength Arrays
const STRENGTH_SUN = ['7', '8', '9', 'J', 'Q', 'K', '10', 'A'];
const STRENGTH_HOKUM_TRUMP = ['7', '8', 'Q', 'K', '10', 'A', '9', 'J'];
const STRENGTH_HOKUM_NORMAL = ['7', '8', '9', 'J', 'Q', 'K', '10', 'A'];

// Helpers
function getCardStrength(card, mode, trumpSuit) {
    if (mode === 'SUN') {
        const idx = STRENGTH_SUN.indexOf(card.rank);
        return idx; // Higher is better
    } else {
        if (card.suit === trumpSuit) {
            const idx = STRENGTH_HOKUM_TRUMP.indexOf(card.rank);
            return 100 + idx; // Trump beats non-trump
        }
        const idx = STRENGTH_HOKUM_NORMAL.indexOf(card.rank);
        return idx;
    }
}

function getTrickWinner(tableCards, mode, trumpSuit) {
    if (tableCards.length === 0) return -1;

    const leadSuit = tableCards[0].card.suit;
    let highestStrength = -1;
    let winnerIndex = 0;

    tableCards.forEach((play, index) => {
        const card = play.card;
        let strength = -1;

        if (card.suit === leadSuit || (mode === 'HOKUM' && card.suit === trumpSuit)) {
            strength = getCardStrength(card, mode, trumpSuit);
        }

        if (strength > highestStrength) {
            highestStrength = strength;
            winnerIndex = index;
        }
    });

    return winnerIndex;
}

function isValidMove(card, hand, tableCards, mode, trumpSuit, strictMode = true) {
    if (!strictMode) return true;

    if (tableCards.length === 0) {
        // Lead: Valid unless locked? (Simplified for now)
        return true;
    }

    const leadSuit = tableCards[0].card.suit;
    const hasLeadSuit = hand.some(c => c.suit === leadSuit);

    // 1. Follow Suit
    if (hasLeadSuit) {
        if (card.suit !== leadSuit) return false;
        return true;
    }

    // 2. Cut if can't follow (Hokum)
    if (mode === 'HOKUM' && trumpSuit) {
        const hasTrump = hand.some(c => c.suit === trumpSuit);
        // Simplified: If you have trump and opponent played non-trump, you MUST trump.
        // Or if opponent played trump... complex rules.
        // For Bot Implementation V1: Just check if you have trump and cut if possible.
        // Strictly: Baloot allows playing anything if you don't have lead suit AND don't have trump / don't want to over-trump?
        // Wait, rule: If you can't follow suit, you MUST play trump (if you have it) AND if you can beat the current winner (if current winner is opponent).
        // Let's stick to: "If you have trump and lead is non-trump, you MUST play trump."
        if (hasTrump && card.suit !== trumpSuit) return false;
    }

    return true;
}

function calculateHandPoints(hand, mode, trumpSuit) {
    let score = 0;
    hand.forEach(c => {
        if (mode === 'SUN') {
            score += POINT_VALUES_SUN[c.rank];
        } else {
            // Hokum
            if (c.suit === trumpSuit) {
                // J=20, 9=14...
                // Need specific map access.
                // CONSTANT keys match?
                // POINT_VALUES_HOKUM has 9=14, J=20.
                // What about A? POINT_VALUES_HOKUM A=11.
                // Non-trump: A=11, 10=10... J=0?
                // Wait, J is 0 in non-trump.
                score += POINT_VALUES_HOKUM[c.rank]; // This map assumes Trump.
            } else {
                score += POINT_VALUES_SUN[c.rank]; // Non-trump uses Sun values (Mostly).
                // Correction: J in Sun is 2. J in Non-Trump Hokum is 0.
                if (c.rank === 'J') score -= 2; // Hack fix? Or better map.
                // Let's rely on approximation or fix map.
                // Actually usually strict rule: Non-trump J=0. Sun J=2.
            }
        }
    });
    return score;
}

function validateProject(hand, type, mode) {
    if (!hand || hand.length < 3) return { valid: false };

    // Sort hand by Suit then Rank (Order Projects)
    const sortedHand = [...hand].sort((a, b) => {
        if (a.suit !== b.suit) return a.suit.localeCompare(b.suit);
        return ORDER_PROJECTS.indexOf(a.rank) - ORDER_PROJECTS.indexOf(b.rank);
    });

    // Check 4 of a Kind (100 or 400)
    if (type === 'HUNDRED' || type === 'FOUR_HUNDRED') {
        const rankCounts = {};
        hand.forEach(c => rankCounts[c.rank] = (rankCounts[c.rank] || 0) + 1);

        for (const rank in rankCounts) {
            if (rankCounts[rank] === 4) {
                // Check allowed ranks
                if (['A', 'K', 'Q', 'J', '10'].includes(rank)) {
                    if (rank === 'A' && type === 'FOUR_HUNDRED' && mode === 'SUN') {
                        return { valid: true, score: 400, rank: 'A', type: 'FOUR_HUNDRED' };
                    }
                    if (type === 'HUNDRED') {
                        return { valid: true, score: 100, rank, type: 'HUNDRED' };
                    }
                }
            }
        }
    }

    // Check Sequences
    // Helper to find longest sequence in same suit
    let bestSeq = 0;
    let currentSeq = 1;
    let highRank = '';

    for (let i = 0; i < sortedHand.length - 1; i++) {
        const curr = sortedHand[i];
        const next = sortedHand[i + 1];

        const idxCurr = ORDER_PROJECTS.indexOf(curr.rank);
        const idxNext = ORDER_PROJECTS.indexOf(next.rank);

        // Check adjacency: same suit and next rank is current + 1
        if (curr.suit === next.suit && idxNext === idxCurr + 1) {
            currentSeq++;
        } else {
            // Check if this block was best
            if (currentSeq > bestSeq) {
                bestSeq = currentSeq;
                // High rank is the start of the sequence (which is index i - (currentSeq-1)?? No, sorted Ascending or Descending?)
                // ORDER_PROJECTS is ['A', 'K'...] (Descending strength).
                // Sort logic: a - b (indexOf). So 'A' (0) comes before 'K' (1).
                // So sortedHand is A, K, Q...
                // So top of sequence is the first card of the block.
                highRank = sortedHand[i - currentSeq + 1].rank;

            }
            currentSeq = 1;
        }
    }
    // Final check
    if (currentSeq > bestSeq) {
        bestSeq = currentSeq;
        highRank = sortedHand[sortedHand.length - currentSeq].rank;
    }

    // Recalculate High Rank precisely
    // If sorted is A, K, Q. i=0(A), i+1(K). adj. seq=2. i=1(K), i+2(Q). adj. seq=3.
    // Top card is at index [EndIndex - SequenceLength + 1] ?
    // Actually simplicity: Iterating. If seq valid, the top rank is the rank of the first card in that group.

    // Strict Check for requested type
    if (type === 'SIRA' && bestSeq >= 3 && bestSeq < 4) return { valid: true, score: 20, rank: highRank, type: 'SIRA' }; // Or allow declaring SIRA if you have 4? Usually you declare highest.
    // Actually player says "Sira" if they have 3.
    // If they have 50 (4), they say "50".

    // Allow >= checks? 
    if (type === 'SIRA' && bestSeq >= 3) return { valid: true, score: 20, rank: highRank, type: 'SIRA' };
    if (type === 'FIFTY' && bestSeq >= 4) return { valid: true, score: 50, rank: highRank, type: 'FIFTY' };
    if (type === 'HUNDRED' && bestSeq >= 5) return { valid: true, score: 100, rank: highRank, type: 'HUNDRED' };

    return { valid: false };
}

module.exports = {
    isValidMove,
    getTrickWinner,
    getCardStrength,
    calculateHandPoints,
    validateProject
};
