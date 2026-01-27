
const { isValidMove, getCardStrength, getTrickWinner, calculateHandPoints } = require('./gameLogic');
const { SUITS } = require('./constants');

async function getBotDecision(gameState, player) {
    // 1. Simulate Delay (make it feel human)
    await new Promise(r => setTimeout(r, 1000 + Math.random() * 500));

    const hand = player.hand;

    // --- BIDDING ---
    if (gameState.phase === 'BIDDING') {
        // Simple Logic: > 20 points SUN?
        let sunPoints = 0;
        hand.forEach(c => {
            if (['A', '10', 'K', 'Q'].includes(c.rank)) sunPoints += 5;
        });

        if (sunPoints > 25) return { action: 'BID', payload: 'SUN' };

        return { action: 'BID', payload: 'PASS' };
    }

    // --- PLAYING ---
    if (gameState.phase === 'PLAYING') {
        const mode = gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
        let trumpSuit = null;
        if (mode === 'HOKUM') {
            // Use stored trumpSuit if available, else fallback (e.g. first round logic before nulling floor)
            trumpSuit = gameState.trumpSuit || (gameState.floorCard ? gameState.floorCard.suit : '♠');
        }

        // Get Legal Moves
        const legalMoves = hand.map((card, index) => ({ card, index }))
            .filter(item => isValidMove(item.card, hand, gameState.tableCards, mode, trumpSuit));

        if (legalMoves.length === 0) return { action: 'PLAY', payload: { cardIndex: 0 } }; // Fallback

        // Sort by strength (Ascending)
        legalMoves.sort((a, b) => getCardStrength(a.card, mode, trumpSuit) - getCardStrength(b.card, mode, trumpSuit));

        // Strategy
        if (gameState.tableCards.length === 0) {
            // LEAD: Play Strongest (Simple)
            return { action: 'PLAY', payload: { cardIndex: legalMoves[legalMoves.length - 1].index } };
        } else {
            // FOLLOW: Play Lowest legal card.
            return { action: 'PLAY', payload: { cardIndex: legalMoves[0].index } };
        }
    }

    return { action: 'BID', payload: 'PASS' }; // Default
}

module.exports = { getBotDecision };
