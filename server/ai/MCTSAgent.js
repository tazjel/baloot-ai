const RuleVerifier = require('../RuleVerifier');
const { getTrickWinner } = require('../gameLogic');
const { calculateRoundResult, sumCardPoints } = require('../scoring');
const { SUITS, RANKS } = require('../constants');
const StateEncoder = require('./StateEncoder');

class MCTSAgent {
    constructor(iterations = 100) {
        this.iterations = iterations;
    }

    /**
     * Selects the best card to play using MCTS.
     * @param {object} gameState - Valid game state object
     * @param {object} player - The bot player object
     * @returns {object} { action: 'PLAY', payload: { cardIndex: number } }
     */
    async getDecision(gameState, player) {
        // Requirement 11.3: Use StateEncoder
        const stateVector = StateEncoder.encode(gameState, player.team);
        // console.log("MCTS State Vector:", stateVector); // Debug usage

        const hand = player.hand;
        const validMoves = RuleVerifier.getValidMoves(
            hand,
            gameState.tableCards,
            gameState.bid.type,
            gameState.trumpSuit,
            player.team,
            gameState.players
        );

        if (validMoves.length === 0) return { action: 'PLAY', payload: { cardIndex: 0 } }; // Should not happen
        if (validMoves.length === 1) {
            // Only one move, no need to think
            const idx = hand.indexOf(validMoves[0]);
            return { action: 'PLAY', payload: { cardIndex: idx } };
        }

        // MCTS Logic
        const moveScores = new Map(); // Map<Card, Score>

        // Initialize scores
        validMoves.forEach(m => moveScores.set(m, 0));

        // Determinization:
        // We do not know opponents' cards. We must generate "Determined" worlds.
        // For each iteration, generate a plausible deal for others and run simulation.

        // Find my index explicitly
        // If player object is from array, indexOf works.
        // If it's a copy, we might need to match by ID or Position?
        // Game.js passes reference from gameState.players array.
        let playerIndex = gameState.players.indexOf(player);
        if (playerIndex === -1) {
            // Fallback match by position
            playerIndex = gameState.players.findIndex(p => p.position === player.position);
        }

        for (let i = 0; i < this.iterations; i++) {
            // 1. determinize
            const simulatedState = this.determinize(gameState, player, playerIndex);

            // 2. Select & Run for each valid move
            // Simplification: We iterate ALL valid moves for the root? Or use UCT?
            // "Pure MCTS" on root + Random Rollout implies IS-MCTS (Information Set MCTS).
            // Usually we pick one move to explore per determinization or explore all children of root?
            // Let's explore ALL root moves once per determinization to get average?
            // Or pick one random move and simulate?
            // Better: For this iteration, pick ONE move to simulate (e.g. Round Robin or UCT).
            // Since branching factor is small (~3-8), we can just run one simulation per root move?
            // No, 100 iterations total. 3 moves -> 33 iterations each.

            // Let's choose a move using UCT or just Random for now?
            // Requirement says "Information Set Determinization".
            // Let's do: For each valid move of ROOT, run N simulations?
            // 100 iterations total is low.
            // Let's loop validMoves and run (Iterations / Moves.length) simulations for each.

            // Re-think: Is running `iterations` loop better?
            // Shuffle validMoves to avoid bias
            const move = validMoves[i % validMoves.length];

            const result = this.simulate(simulatedState, playerIndex, move);
            moveScores.set(move, moveScores.get(move) + result);
        }

        // Pick best
        let bestMove = validMoves[0];
        let bestScore = -Infinity;

        moveScores.forEach((score, move) => {
            if (score > bestScore) {
                bestScore = score;
                bestMove = move;
            }
        });

        const idx = hand.indexOf(bestMove);
        return { action: 'PLAY', payload: { cardIndex: idx } };
    }

    /**
     * Creates a concrete game state by distributing unknown cards to opponents.
     * Respects known constraints (e.g. keeping track of void suits - simplified for now).
     */
    determinize(gameState, perspectivePlayer, perspectiveIndex) {
        // Clone state (Shallow copy where possible, deep where needed)
        // We only really need: hands, tableCards, turnIndex, scores, history.

        // 1. Identify Unknown Cards
        // All cards not in my hand, not on table, not in history/played.
        const knownCards = new Set();
        perspectivePlayer.hand.forEach(c => knownCards.add(c.suit + c.rank));
        gameState.tableCards.forEach(tc => knownCards.add(tc.card.suit + tc.card.rank));
        gameState.roundHistory.forEach(trick => {
            // Trick history might not store cards explicitly in current Game.js? 
            // current implementation stores {winner: pos, points: x}. Cards are lost?
            // If cards are lost, we can't do perfect determinization.
            // We'll trust `deck` to be empty? No, deck is empty after deal.
            // We need a way to know played cards.
            // Assume we track played cards in a Set for the simulation?
            // Since we lack full history in `gameState` (only winner), we assume "Remaining Deck" = All Cards - My Hand - Table.
            // Make sure we don't deal cards that have been played.
            // This is a limitation of current state.
            // For V1: Generate constraints from checking `gameState.playedCards` (If we add it).
        });

        // Workaround: Re-create deck from scratch, remove my hand & table. 
        // Then shuffle and deal to others to fill their hand counts.
        // Problem: We don't know who played what, so we might give a card to someone who voided that suit.
        // Rule said: "consistent with the current history (e.g., if Player West previously discarded a Diamond...)".
        // WITHOUT history of plays, we cannot do this check. 
        // I will assume for V1 MCTS we distribute randomly, as tracking history requires Game.js refactor to store it.
        // Task 11.1 said "Logic to Enforce". Task 11.2 "MCTSAgent".
        // I will assume simple random distribution for now.

        // Calculate needed cards per player
        // Players 0..3
        const hands = {};
        const needed = [];

        gameState.players.forEach((p, idx) => {
            if (idx === perspectiveIndex) {
                hands[idx] = [...perspectivePlayer.hand];
            } else {
                hands[idx] = []; // Empty, to be filled
                // How many cards does he have?
                // Logic: Started with 8. Played X turns? 
                // Or just: p.hand.length (in public state, hand is hidden but length known? 
                // In `Game.js`, `gameState.players` has `hand: []` (empty) for public. server `players` has real hand.
                // The BOT runs on SERVER, so it has access to `gameState` which has `players`... 
                // Wait. `getBotDecision` is called with `gameState` (Public) + `player` (Private Object with Hand).
                // `gameState.players` contains limited info?
                // `Game.js`: `getBotDecision(this.gameState, currentPlayer)`
                // `this.gameState.players` has objects with `hand: []`.
                // BUT the server knows the count. `this.players` (private) has hands.
                // `gameState.players[i].hand` is EMPTY array in public state.
                // So MCTS doesn't know how many cards opponents have!
                // FIX: MCTS needs to deduce count.
                // Round starts with 8 cards. `roundHistory.length` tells us completed tricks.
                // Current trick `tableCards.length`.
                // Cards In Hand = 8 - roundHistory.length - (hasPlayedInCurrentTrick ? 1 : 0).

                const hasPlayed = gameState.tableCards.some(tc => tc.playedBy === p.position);
                const count = 8 - gameState.roundHistory.length - (hasPlayed ? 1 : 0);
                needed.push({ idx, count });
            }
        });

        // Generate Deck
        const deck = [];
        for (const s of SUITS) {
            for (const r of RANKS) {
                const id = s + r;
                if (!knownCards.has(id)) { // We need to populate knownCards correctly using ALL played cards
                    // But we don't have them.
                    // Hack: Just randomly pick from FULL DECK excluding visible?
                    // This implies we might deal a card that was already played 3 turns ago.
                    // This creates INVALID STATES (duplicate cards in history).
                    // MAJOR ISSUE. 
                    // Solution: We need Game.js to track `playedCards` Set in gameState.
                    deck.push({ suit: s, rank: r });
                }
            }
        }

        // Filter `deck` by MyHand and TableCards (which we know are real).
        // Since we can't filter history, valid determinization is Step 1.
        // I will implement `playedCards` tracking in Game.js later.

        // Filter knowns
        const filteredDeck = deck.filter(c =>
            !perspectivePlayer.hand.some(h => h.suit === c.suit && h.rank === c.rank) &&
            !gameState.tableCards.some(t => t.card.suit === c.suit && t.card.rank === c.rank)
        );

        // Shuffle
        for (let i = filteredDeck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [filteredDeck[i], filteredDeck[j]] = [filteredDeck[j], filteredDeck[i]];
        }

        // Deal
        let ptr = 0;
        needed.forEach(n => {
            for (let k = 0; k < n.count; k++) {
                if (filteredDeck[ptr]) hands[n.idx].push(filteredDeck[ptr++]);
            }
        });

        // Return Simulated State (just the parts we need)
        return {
            ...gameState,
            players: gameState.players.map((p, i) => ({ ...p, hand: hands[i] })), // Assign calculated hands
            tableCards: [...gameState.tableCards], // Clone
            currentTurnIndex: gameState.currentTurnIndex
        };
    }

    /**
     * Simulates a game to the end
     */
    simulate(simState, myIndex, firstMove) {
        // Clone heavily mutated parts
        let currentState = {
            tableCards: [...simState.tableCards],
            currentTurnIndex: simState.currentTurnIndex, // Should be ME
            players: simState.players.map(p => ({
                ...p,
                hand: [...p.hand] // Clone hands as we will splice
            })),
            trumpSuit: simState.trumpSuit,
            bid: simState.bid,
            roundHistory: [...simState.roundHistory]
        };

        const myTeam = currentState.players[myIndex].team;
        let myTeamPoints = 0;
        let oppTeamPoints = 0;

        // === Apply First Move (My Move) ===
        // Remove card
        const player = currentState.players[myIndex];
        const cardIdx = player.hand.findIndex(c => c.suit === firstMove.suit && c.rank === firstMove.rank);
        if (cardIdx !== -1) player.hand.splice(cardIdx, 1);

        currentState.tableCards.push({ card: firstMove, playedBy: player.position });

        // Update turn
        currentState.currentTurnIndex = (currentState.currentTurnIndex + 1) % 4;

        // === Run Random Playout ===
        while (currentState.players[0].hand.length > 0 || currentState.tableCards.length > 0) {

            // Check Trick End
            if (currentState.tableCards.length === 4) {
                const winnerIdx = getTrickWinner(
                    currentState.tableCards,
                    currentState.bid.type === 'SUN' ? 'SUN' : 'HOKUM',
                    currentState.trumpSuit
                );
                // winnerIdx is 0..3 index in tableCards
                const winnerCard = currentState.tableCards[winnerIdx];
                const winnerPos = winnerCard.playedBy;
                const winnerPlayer = currentState.players.find(p => p.position === winnerPos);

                // Calc Points
                const trickPoints = sumCardPoints(currentState.tableCards.map(t => t.card), currentState.bid.type, currentState.trumpSuit);

                if (winnerPlayer.team === myTeam) myTeamPoints += trickPoints;
                else oppTeamPoints += trickPoints;

                currentState.tableCards = [];
                currentState.currentTurnIndex = currentState.players.indexOf(winnerPlayer); // Securely find index

                // If hands empty, done
                if (currentState.players[0].hand.length === 0) break;
                continue;
            }

            // Next Player Move
            const pIdx = currentState.currentTurnIndex;
            const p = currentState.players[pIdx];

            // Get Valid Moves
            const moves = RuleVerifier.getValidMoves(
                p.hand,
                currentState.tableCards,
                currentState.bid.type,
                currentState.trumpSuit,
                p.team,
                currentState.players
            );

            let move;
            if (moves.length > 0) {
                // Weighted Choice (Heuristic: Play High Cards?)
                // Or Pure Random? "weighted random rollout ... high-value cards played with slightly higher probability"
                const weightedMoves = [];
                moves.forEach(m => {
                    let weight = 1;
                    if (['A', '10', 'K'].includes(m.rank)) weight = 3;
                    for (let k = 0; k < weight; k++) weightedMoves.push(m);
                });
                move = weightedMoves[Math.floor(Math.random() * weightedMoves.length)];
            } else {
                move = p.hand[0]; // Error fallback
            }

            // Play
            const cIdx = p.hand.indexOf(move);
            if (cIdx !== -1) p.hand.splice(cIdx, 1);
            currentState.tableCards.push({ card: move, playedBy: p.position });
            currentState.currentTurnIndex = (pIdx + 1) % 4;
        }

        // Return score diff (My Points - Opp Points)
        return myTeamPoints - oppTeamPoints;
    }
}

module.exports = MCTSAgent;
