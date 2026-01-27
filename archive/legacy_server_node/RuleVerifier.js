const { getCardStrength } = require('./gameLogic');
const { SUITS } = require('./constants');

/**
 * STRICT Rule Engine for Baloot
 */
class RuleVerifier {

    /**
     * Checks if a move is valid according to strict Baloot rules.
     * @param {object} card - The card attempting to be played {suit, rank}
     * @param {Array} hand - The player's current hand
     * @param {Array} tableCards - Cards currently on the table [{card, playedBy, ...}]
     * @param {string} mode - 'SUN' or 'HOKUM'
     * @param {string} trumpSuit - The trump suit (if HOKUM)
     * @param {string} playerTeam - 'us' or 'them'
     * @param {string} winningTeam - The team currently winning the trick ('us' or 'them' or null)
     * @returns {boolean}
     */
    static isValidMove(card, hand, tableCards, mode, trumpSuit, playerTeam, winningTeam) {
        if (tableCards.length === 0) return true; // Leading is always valid

        const leadCard = tableCards[0].card;
        const leadSuit = leadCard.suit;

        // 1. MUST FOLLOW SUIT
        const hasLeadSuit = hand.some(c => c.suit === leadSuit);
        if (hasLeadSuit) {
            if (card.suit !== leadSuit) return false;

            // Note: In Hokum, if following suit (Trump), must you overtrump?
            // Yes, if Trump is led, you must beat the current highest trump if possible.
            if (mode === 'HOKUM' && leadSuit === trumpSuit) {
                return RuleVerifier.checkOvertrump(card, hand, tableCards, mode, trumpSuit);
            }
            return true;
        }

        // 2. IF CANNOT FOLLOW SUIT:

        if (mode === 'SUN') {
            return true; // Use whatever you want in SUN if valid suit missing
        }

        // --- HOKUM LOGIC FROM HERE ---

        // If partner is winning (Locked), rules are relaxed
        // "Locked" here means my team is currently holding the trick.
        if (winningTeam === playerTeam) {
            // "Play whatever" (usually trash). You are NOT forced to trump.
            // But if you play trump, valid? Yes.
            return true;
        }

        // Opponent is winning
        // MUST TRUMP if possible
        const hasTrump = hand.some(c => c.suit === trumpSuit);
        if (hasTrump) {
            if (card.suit !== trumpSuit) return false; // Must play trump

            // OVERTRUMP / UNDERTRUMP LOGIC
            return RuleVerifier.checkOvertrump(card, hand, tableCards, mode, trumpSuit);
        }

        // No Lead Suit, No Trump -> Play anything
        return true;
    }

    /**
     * Checks if the played trump is valid regarding Overtrump/Undertrump rules
     */
    static checkOvertrump(card, hand, tableCards, mode, trumpSuit) {
        // Find current winning card strength
        let highestStrength = -1;
        let highestSuit = null;

        tableCards.forEach(play => {
            const s = getCardStrength(play.card, mode, trumpSuit);
            if (s > highestStrength) {
                highestStrength = s;
                highestSuit = play.card.suit;
            }
        });

        // If current winner is not trump, any trump wins.
        // If current winner IS trump, we must beat it.
        const isTrumpWinner = (highestSuit === trumpSuit);

        if (isTrumpWinner) {
            const myStrength = getCardStrength(card, mode, trumpSuit);

            // Can we beat it?
            const canBeat = hand.some(c => c.suit === trumpSuit && getCardStrength(c, mode, trumpSuit) > highestStrength);

            if (canBeat) {
                // Must play a card that beats it
                if (myStrength > highestStrength) return true;
                return false; // Penalty: You had a higher trump but played a lower one?
            } else {
                // CANNOT beat it (Undertrump)
                // Must still play trump (already checked in caller), but any trump is fine.
                // Wait, "Undertrump" rule: If you can't overtrump, you must play a low trump.
                // This is satisfied by nature of "canBeat=false" -> We are playing a trump.
                return true;
            }
        }

        return true;
    }

    /**
     * Helper to determine current winner of the partial trick
     */
    static getWinningTeam(tableCards, mode, trumpSuit, players) {
        if (tableCards.length === 0) return null;

        // Find winner index in tableCards
        let highestStrength = -1;
        let winnerPos = null;

        const leadSuit = tableCards[0].card.suit;

        tableCards.forEach(play => {
            const card = play.card;
            // Strength calc (simplified logic from gameLogic reused here or reimplemented?)
            // We should use the same source of truth.
            // gameLogic.getCardStrength handles strength value.
            // But we need to handle "Beat".

            let strength = -1;
            // Valid suits: Lead Suit OR Trump
            if (card.suit === leadSuit || (mode === 'HOKUM' && card.suit === trumpSuit)) {
                strength = getCardStrength(card, mode, trumpSuit);
            }

            if (strength > highestStrength) {
                highestStrength = strength;
                winnerPos = play.playedBy;
            }
        });

        // Map winnerPos to Team
        const winnerPlayer = players.find(p => p.position === winnerPos);
        return winnerPlayer ? winnerPlayer.team : null;
    }

    // Generator for bots
    static getValidMoves(hand, tableCards, mode, trumpSuit, playerTeam, players) {
        const winningTeam = RuleVerifier.getWinningTeam(tableCards, mode, trumpSuit, players);

        return hand.filter(card => RuleVerifier.isValidMove(card, hand, tableCards, mode, trumpSuit, playerTeam, winningTeam));
    }
}

module.exports = RuleVerifier;
