const { POINT_VALUES_SUN, POINT_VALUES_HOKUM } = require('./constants');

/**
 * rounds a score according to Baloot rules
 * @param {number} score - Raw point sum
 * @param {string} mode - 'SUN' or 'HOKUM'
 * @returns {number} - Calculated game points
 */
function calculateScorePoints(score, mode) {
    if (mode === 'SUN') {
        // Sun: Round to nearest 10, multiply by 2, divide by 10.
        // Equivalent to: Round(score / 10) * 2
        // Example: 14 -> 1.4 -> 1 -> 2
        // Example: 15 -> 1.5 -> 2 -> 4
        // Example: 130 -> 13 -> 26

        // Note: JS Math.round(1.5) is 2.
        const rounded = Math.round(score / 10);
        return rounded * 2;
    } else {
        // Hokum: Sum / 10, rounded.
        // Example: 152 -> 15.2 -> 15
        // Example: 16 -> 2
        return Math.round(score / 10);
    }
}

/**
 * Calculates the raw points of a list of cards
 * @param {Array} cards - Array of card objects {suit, rank}
 * @param {string} mode - 'SUN' or 'HOKUM'
 * @param {string} trumpSuit - The trump suit (required for Hokum)
 * @returns {number} - Raw sum of card points
 */
function sumCardPoints(cards, mode, trumpSuit) {
    let score = 0;
    cards.forEach(card => {
        if (mode === 'SUN') {
            score += POINT_VALUES_SUN[card.rank] || 0;
        } else {
            // Hokum: Check if card is trump
            if (card.suit === trumpSuit) {
                // Use Hokum values which include J=20, 9=14
                score += POINT_VALUES_HOKUM[card.rank] || 0;
            } else {
                // Non-trump cards in Hokum use SUN values (A=11, 10=10, K=4, Q=3)
                // BUT J is 0, 9 is 0, 8 is 0, 7 is 0.
                // POINT_VALUES_SUN has J=2. We need to handle this.
                if (card.rank === 'J') {
                    score += 0; // J is 0 in non-trump Hokum
                } else {
                    score += POINT_VALUES_SUN[card.rank] || 0;
                }
            }
        }
    });
    return score;
}

/**
 * Calculates the final round score including Projects and Khusara logic.
 * @param {number} usRawPoints - Raw points captured by 'us' team (including last trick bonus)
 * @param {number} themRawPoints - Raw points captured by 'them' team (including last trick bonus)
 * @param {number} usProjectPoints - Project points declared by 'us'
 * @param {number} themProjectPoints - Project points declared by 'them'
 * @param {string} mode - 'SUN' or 'HOKUM'
 * @param {string} bidderTeam - Who bought the bid ('us' or 'them')
 * @returns {object} - { us: finalScore, them: finalScore }
 */
function calculateRoundResult(usRawPoints, themRawPoints, usProjectPoints, themProjectPoints, mode, bidderTeam) {
    let usScore = calculateScorePoints(usRawPoints, mode);
    let themScore = calculateScorePoints(themRawPoints, mode);

    // Total Pot Size check (Standardize)
    // Sun total is 26. Hokum is 16.
    const MAX_SCORE = mode === 'SUN' ? 26 : 16;

    // Safety clamp? Sometimes rounding makes it 27/17 if sloppy?
    // 130 -> 26. 156 -> 16. 
    // If floating point errors, we might strictly distribute.

    // Add Projects
    let usTotal = usScore + usProjectPoints;
    let themTotal = themScore + themProjectPoints;

    // Check Winner of the deal (Bidder must win)
    // Khusara Condition: Bidder's points < Opponent's points?
    // Actually rule: Bidder must get > half the points? 
    // Simplified: Bidder score must be > Opponent score? Or Bidder + Projects > Opponent + Projects?

    // Basic Khusara Check:
    // If Bidder is 'us' and (usScore + usProjectPoints) <= (themScore + themProjectPoints)
    // Then 'them' gets EVERYTHING.
    // Wait, exact rule: if Bidder points < Opponent points.
    // What if tie? Khusara usually.

    // Let's implement strict Khusara.

    let bidderTotal = bidderTeam === 'us' ? usTotal : themTotal;
    let opponentTotal = bidderTeam === 'us' ? themTotal : usTotal;

    // If bidder loses (Khusara)
    if (bidderTotal <= opponentTotal) { // Tie usually goes to opponent
        // Winning team (Opponent) gets EVERYTHING.
        const totalPot = MAX_SCORE + usProjectPoints + themProjectPoints;

        if (bidderTeam === 'us') {
            return { us: 0, them: totalPot };
        } else {
            return { us: totalPot, them: 0 };
        }
    }

    return { us: usTotal, them: themTotal };
}

module.exports = {
    calculateScorePoints,
    sumCardPoints,
    calculateRoundResult
};
