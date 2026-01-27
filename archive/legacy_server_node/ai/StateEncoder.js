const { SUITS } = require('../constants');

class StateEncoder {

    /**
     * Encodes the game state into a numeric vector.
     * @param {object} gameState 
     * @param {string} playerTeam ('us' or 'them')
     * @returns {Array} Vector representation
     */
    static encode(gameState, playerTeam) {
        const vector = [];

        // 1. Current Trump Suit (One-hot: 4)
        // Order: Spades, Hearts, Diamonds, Clubs
        const trump = gameState.trumpSuit;
        SUITS.forEach(s => {
            vector.push(s === trump ? 1 : 0);
        });

        // 2. Is Sun Mode (Binary)
        vector.push(gameState.bid.type === 'SUN' ? 1 : 0);

        // 3. Score Difference (Scalar: Us - Them)
        const diff = gameState.matchScores.us - gameState.matchScores.them;
        // Normalize? Prompt says "Scalar".
        // Perspective: From 'playerTeam' perspective?
        if (playerTeam === 'us') vector.push(diff);
        else vector.push(-diff); // Them perspective

        // 4. Project Points Declared (Scalar)
        // Total points in current round from projects
        let totalProjects = 0;
        Object.values(gameState.declarations).forEach(arr => {
            arr.forEach(d => totalProjects += d.score);
        });
        vector.push(totalProjects);

        return vector;
    }
}

module.exports = StateEncoder;
