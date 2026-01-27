const { calculateHandPoints } = require('../gameLogic'); // Reusing or refactoring?
const { POINT_VALUES_SUN, POINT_VALUES_HOKUM, SUITS } = require('../constants');
const { sumCardPoints } = require('../scoring');

class BiddingEvaluator {

    /**
     * Decides whether to bid or pass.
     * @param {Array} hand - Player's hand
     * @param {object} gameState - Current game state
     * @param {string} playerPosition - 'Bottom', 'Right', etc.
     * @returns {object} { action: 'BID', payload: 'SUN'/'HOKUM'/'PASS' }
     */
    static evaluateBid(hand, gameState, playerPosition) {
        // 1. Check SUN
        const sunScore = sumCardPoints(hand, 'SUN');
        // Threshold: > 20 points
        // Note: A=11, 10=10. Two aces > 20. A+10 > 20.
        // Rule said: Hand Value > 20.
        if (sunScore > 20) {
            return { action: 'BID', payload: 'SUN' };
        }

        // 2. Check HOKUM
        // Iterate suits to find a good trump suit
        for (const suit of SUITS) {
            const hasTrumpJ = hand.some(c => c.suit === suit && c.rank === 'J');
            const hasTrump9 = hand.some(c => c.suit === suit && c.rank === '9');
            const acesCount = hand.filter(c => c.rank === 'A').length;

            // Rule: "Hand contains J or 9 of trump + 1 Ace"
            if ((hasTrumpJ || hasTrump9) && acesCount >= 1) {
                // Also check if we already have a floor card matching this suit?
                // If this is second round (Buy), we can choose any suit.
                // If first round, we can only buy the floor suit.

                if (gameState.biddingRound === 1) {
                    const floorSuit = gameState.floorCard ? gameState.floorCard.suit : null;
                    if (floorSuit === suit) {
                        return { action: 'BID', payload: 'HOKUM' };
                    }
                } else {
                    // Round 2: Can buy any suit (except floor suit usually? Or just any?)
                    // Usually Round 2 allows any suit except the one passed in Round 1 (floor suit).
                    // Simplified: Logic just bids Hokum on this suit.
                    // Implementation of Game.js doesn't enforce "not floor suit" strictly yet.
                    return { action: 'BID', payload: 'HOKUM' };
                }
            }
        }

        return { action: 'BID', payload: 'PASS' };
    }
}

module.exports = BiddingEvaluator;
