const Game = require('./Game');
const { SUITS, RANKS } = require('./constants');

// Mock Random Agent
function getRandomMove(hand, tableCards, mode, trumpSuit, team, players) {
    const RuleVerifier = require('./RuleVerifier');
    const valid = RuleVerifier.getValidMoves(hand, tableCards, mode, trumpSuit, team, players);
    if (valid.length === 0) return hand[0];
    return valid[Math.floor(Math.random() * valid.length)];
}

async function runSimulation() {
    console.log("--- Starting Simulation: MCTS Bot vs Random ---");

    let botWins = 0;
    let randomWins = 0;

    const TOTAL_HANDS = 20; // 20 hands for quick verification

    for (let i = 0; i < TOTAL_HANDS; i++) {
        const game = new Game('sim_room');

        // Add Players
        game.addPlayer({ id: 'bot1', name: 'Bot 1', isBot: true }); // 0 (Us)
        game.addPlayer({ id: 'rnd1', name: 'Random 1', isBot: false }); // 1 (Them)
        game.addPlayer({ id: 'bot2', name: 'Bot 2', isBot: true }); // 2 (Us)
        game.addPlayer({ id: 'rnd2', name: 'Random 2', isBot: false }); // 3 (Them)

        // Start Game
        game.start();
        game.gameState.settings.isDebug = true; // Speed up bots


        // Force Bid
        const mode = i % 2 === 0 ? 'SUN' : 'HOKUM';
        game.handleBid(0, mode); // Bot 1 bids

        let isRoundOver = false;

        // Mock IO
        const mockIo = {
            to: () => ({
                emit: (event, data) => {
                    if (event === 'game_update') {
                        const state = data.gameState;
                        if (state.roundHistory.length === 8 && state.tableCards.length === 0) {
                            isRoundOver = true;
                        }
                    }
                }
            })
        };
        game.setIo(mockIo);

        // Play Loop
        let safety = 0;
        while (!isRoundOver && safety < 200) {
            safety++;
            const turnIdx = game.gameState.currentTurnIndex;

            // Check if game ended prematurely or loop stuck
            if (turnIdx === -1) { await new Promise(r => setTimeout(r, 10)); continue; }

            const privateP = game.gameState.players[turnIdx]; // Use gameState players which has hands

            if (turnIdx === 0 || turnIdx === 2) {
                // BOT TEAM
                await game.checkBotTurn(mockIo);
            } else {
                // RANDOM TEAM
                if (!privateP || privateP.hand.length === 0) break;

                const move = getRandomMove(
                    privateP.hand,
                    game.gameState.tableCards,
                    game.gameState.bid.type,
                    game.gameState.trumpSuit,
                    privateP.team,
                    game.gameState.players
                );

                const cardIdx = privateP.hand.indexOf(move);
                game.handlePlay(turnIdx, { cardIndex: cardIdx });
            }
            await new Promise(r => setTimeout(r, 10));
        }

        const usScore = game.gameState.matchScores.us;
        const themScore = game.gameState.matchScores.them;

        if (usScore > themScore) botWins++;
        else if (themScore > usScore) randomWins++;
    }

    console.log(`\nSimulation Results (${TOTAL_HANDS} hands):`);
    console.log(`Bot Wins: ${botWins}`);
    console.log(`Random Wins: ${randomWins}`);
    console.log(`Win Rate: ${((botWins / TOTAL_HANDS) * 100).toFixed(1)}%`);
}

runSimulation();
