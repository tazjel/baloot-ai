const { getBotDecision } = require('./botLogic'); // Keeping for legacy or removing? Plan says replace.
// const { getTrickWinner, validateProject, getCardStrength, calculateHandPoints } = require('./gameLogic'); // Replaced by modules
const { getTrickWinner, validateProject, getCardStrength } = require('./gameLogic'); // Keeping some helpers
const { SUITS, RANKS } = require('./constants');
const RuleVerifier = require('./RuleVerifier');
const { calculateRoundResult, calculateScorePoints } = require('./scoring');
const MCTSAgent = require('./ai/MCTSAgent');
const BiddingEvaluator = require('./ai/BiddingEvaluator');

const mctsAgent = new MCTSAgent(50); // 50 iterations for speed/responsiveness

class Game {
    constructor(roomId) {
        this.roomId = roomId;
        this.players = [];
        this.gameState = {
            phase: 'WAITING',
            currentTurnIndex: 0,
            players: [],
            floorCard: null,
            bid: { type: null, bidder: null, doubled: false },
            tableCards: [],
            teamScores: { us: 0, them: 0 },
            matchScores: { us: 0, them: 0 },
            roundHistory: [],
            settings: { turnDuration: 30, strictMode: true },
            deck: [],
            dealerIndex: 0,
            biddingRound: 1,
            declarations: {},
            doublingLevel: 1,
            isLocked: false,
            isRoundTransitioning: false,
            isTrickTransitioning: false,
            isProjectRevealing: false
        };
        this.deck = [];
        this.dealerIndex = 0;
    }

    addPlayer(player) {
        // Same as before...
        if (this.players.length >= 4) return false;

        const newPlayer = {
            ...player,
            index: this.players.length,
            team: this.players.length % 2 === 0 ? 'us' : 'them',
            isBot: player.isBot || false
        };
        this.players.push(newPlayer);

        // Initialize player in PUBLIC gameState
        this.gameState.players.push({
            id: newPlayer.id,
            name: newPlayer.name,
            hand: [],
            team: newPlayer.team,
            avatar: newPlayer.avatar || '👤',
            position: this.getPosition(newPlayer.index),
            score: 0,
            isDealer: newPlayer.index === this.dealerIndex,
            isActive: false,
            actionText: '',
            isBot: newPlayer.isBot || false
        });

        return newPlayer;
    }

    addBot() {
        if (this.players.length >= 4) return false;
        const botNames = ['Saad', 'Fahad', 'Khalid', 'Nasser'];
        // Ensure unique name
        const existingNames = this.players.map(p => p.name);
        let nameChoice = botNames.find(n => !existingNames.includes(n + " (Bot)")) || "Bot " + Math.floor(Math.random() * 100);

        const name = nameChoice.includes("Bot") ? nameChoice : nameChoice + " (Bot)";

        return this.addPlayer({
            id: 'bot_' + Date.now() + Math.random(),
            name: name,
            socketId: null, // No socket
            isBot: true,
            avatar: '🤖'
        });
    }

    replaceWithBot(socketId) {
        const playerIndex = this.players.findIndex(p => p.socketId === socketId);
        if (playerIndex === -1) return null;

        const player = this.players[playerIndex];
        player.isBot = true;
        player.socketId = null;
        player.name = player.name + " (Bot)";
        player.avatar = '🤖'; // Update avatar

        // Update public state
        const publicPlayer = this.gameState.players.find(p => p.position === this.getPosition(playerIndex));
        if (publicPlayer) {
            publicPlayer.isBot = true;
            publicPlayer.name = player.name;
            publicPlayer.avatar = '🤖';
        }

        return player;
    }

    removePlayer(socketId) {
        const index = this.players.findIndex(p => p.socketId === socketId);
        if (index !== -1) {
            this.players.splice(index, 1);
            this.gameState.players.splice(index, 1);
            // Re-index remaining players? 
            // If waiting, simple remove is okay.
            this.players.forEach((p, i) => {
                p.index = i;
                // Update public state mappings if needed? 
                // For WAITING phase, we rebuild state often or just list.
                // But for robust implementation, we should sync gameState.players completely.
            });
            // Re-sync gameState players to match (keeping structure)
            // Actually gameState.players is array. splice works.
            // But 'position' mapping logic (getPosition) relies on index.
            // If we remove, indices shift. existing players shift.
            // We should update their positions in gameState.
            this.gameState.players.forEach((p, i) => {
                p.position = this.getPosition(i);
                p.isDealer = (i === this.dealerIndex);
            });
        }
    }

    getPosition(index) {
        // Simple mapping: 0=Bottom, 1=Right, 2=Top, 3=Left
        const positions = ['Bottom', 'Right', 'Top', 'Left'];
        return positions[index];
    }

    isFull() {
        return this.players.length === 4;
    }

    start() {
        if (this.players.length < 4) return false;

        // RESET STATE COMPLETELY
        this.gameState.phase = 'BIDDING';
        this.gameState.currentTurnIndex = (this.dealerIndex + 1) % 4;
        this.gameState.tableCards = [];
        this.gameState.bid = { type: null, bidder: null, doubled: false };
        this.gameState.declarations = {};
        this.gameState.biddingRound = 1;
        this.gameState.doublingLevel = 1;
        this.gameState.floorCard = null;
        this.gameState.isLocked = false;
        this.gameState.isTrickTransitioning = false;
        this.gameState.isProjectRevealing = false;

        // Clear Hands & Reset Player State
        this.gameState.players.forEach(p => {
            p.hand = [];
            p.active = false; // or isActive?
            p.actionText = '';
            p.isDealer = (p.index === this.dealerIndex);
        });
        // Set active player
        this.gameState.players[this.gameState.currentTurnIndex].isActive = true;

        this.generateDeck();
        this.dealCards();

        // Broadcast New State
        if (this.io) {
            this.io.to(this.roomId).emit('game_update', { gameState: this.gameState });
            this.io.to(this.roomId).emit('system_message', { text: 'New Round Started' });
        }

        return true;
    }

    generateDeck() {
        this.deck = [];
        for (const s of SUITS) {
            for (const r of RANKS) {
                this.deck.push({ suit: s, rank: r, projectValue: 0, scoreValue: 0 }); // Values calculated dynamically
            }
        }
        // Shuffle
        for (let i = this.deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.deck[i], this.deck[j]] = [this.deck[j], this.deck[i]];
        }
    }

    dealCards() {
        // Deal 5 cards to each player initially (Baloot rules)
        // 3-2 dealing style usually

        this.deck.forEach((card, i) => {
            if (i < 20) {
                const playerIdx = Math.floor(i / 5);
                this.gameState.players[playerIdx].hand.push(card);
            } else if (i === 20) {
                this.gameState.floorCard = card;
            }
        });

        // Remaining cards stay in deck for Phase 2 dealing
    }

    handleAction(socketId, action, payload) {
        console.log(`[ACTION] ${action} from ${socketId}`, payload);
        // Find player index
        const playerIndex = this.players.findIndex(p => p.socketId === socketId);
        if (playerIndex === -1) {
            console.error(`[ACTION ERROR] Player not found for socket ${socketId}`);
            return { error: 'Player not found' };
        }

        if (playerIndex !== this.gameState.currentTurnIndex) {
            console.warn(`[ACTION WARN] Not turn for ${playerIndex}. Current: ${this.gameState.currentTurnIndex}`);
            return { error: 'Not your turn' };
        }

        const result = this.handleActionInternal(playerIndex, action, payload);
        console.log(`[ACTION RESULT]`, result);
        return result;
    }

    handleActionInternal(playerIndex, action, payload) {
        let result = { error: 'Unknown action' };
        if (action === 'BID') {
            result = this.handleBid(playerIndex, payload);
        } else if (action === 'PLAY') {
            result = this.handlePlay(playerIndex, payload);
        } else if (action === 'DECLARE_PROJECT') {
            result = this.handleDeclareProject(playerIndex, payload);
        } else if (action === 'CHALLENGE') {
            // Placeholder for Taqyeed or Dispute
            console.log(`Player ${playerIndex} challenged:`, payload);
            return { success: true, message: 'Challenge logged' };
        }

        return result;
    }

    async checkBotTurn(io) {
        const currentPlayer = this.gameState.players[this.gameState.currentTurnIndex];
        // Ensure player is valid and is a bot
        if (currentPlayer && currentPlayer.isBot) {
            // console.log(`🤖 Bot Turn: ${currentPlayer.name}`);

            try {
                let decision;

                // --- BIDDING PHASE ---
                if (this.gameState.phase === 'BIDDING') {
                    // Get true hand from private state
                    // Note: Game.js stores hands in gameState.players server-side
                    const privatePlayer = this.gameState.players[this.gameState.currentTurnIndex];
                    decision = BiddingEvaluator.evaluateBid(privatePlayer.hand, this.gameState, currentPlayer.position);
                }
                // --- PLAYING PHASE ---
                else if (this.gameState.phase === 'PLAYING') {
                    const privatePlayer = this.gameState.players[this.gameState.currentTurnIndex];
                    decision = await mctsAgent.getDecision(this.gameState, privatePlayer);
                }

                if (decision) {
                    // console.log(`Bot Decision (${currentPlayer.name}):`, decision);

                    // Simulate human delay
                    const delay = this.gameState.settings.isDebug ? 0 : 1000;
                    await new Promise(r => setTimeout(r, delay));

                    // Execute
                    const result = this.handleActionInternal(this.gameState.currentTurnIndex, decision.action, decision.payload);

                    // Broadcast Update
                    if (io) {
                        io.to(this.roomId).emit('game_update', { gameState: this.gameState });
                    }

                    if (result && result.success) {
                        // Chain Next Turn if also Bot
                        // const delay = this.gameState.settings.isDebug ? 200 : 1000; // Handled by await above
                        this.checkBotTurn(io);
                    }
                }
            } catch (err) {
                console.error("Bot turn error:", err);
            }
        }
    }

    // Updated handleBid / handlePlay to call checkBotTurn? 
    // No, server.js calls checkBotTurn after broadcasting human move.

    handleBid(playerIndex, bidType) {
        if (bidType === 'PASS') {
            const nextIndex = (this.gameState.currentTurnIndex + 1) % 4;
            // Check if we looped back to the first bidder of this round
            // First bidder is always (dealerIndex + 1) % 4
            const firstBidder = (this.dealerIndex + 1) % 4;

            if (nextIndex === firstBidder) {
                // Determine what to do based on current bidding round
                if (this.gameState.biddingRound === 1) {
                    // Move to Round 2
                    this.gameState.biddingRound = 2;
                    this.gameState.currentTurnIndex = nextIndex;
                    // Notify system? "Round 2"
                    if (this.io) this.io.to(this.roomId).emit('system_message', { text: 'Second Bidding Round' });
                } else {
                    // GASH! Redeal.
                    // Dealer rotates? Yes.
                    this.dealerIndex = (this.dealerIndex + 1) % 4;
                    if (this.io) this.io.to(this.roomId).emit('system_message', { text: 'Everyone Passed (Gash). Redealing...' });

                    // Restart logic
                    this.start();
                    return { success: true, message: 'Redealing' };
                }
            } else {
                this.gameState.currentTurnIndex = nextIndex;
            }

        } else {
            const bidderPos = this.getPosition(playerIndex);

            // GAHWA Check
            // If bidType is GAHWA, we treat it as SUN usually, or specific mode?
            // "If a player calls 'Gahwa' ... during bidding phase".
            // Typically Gahwa relates to Sun/Hokum. 
            // We assume payload might need to specify mode? Or defaults to SUN?
            // Usually Gahwa is a modifier or a high-stakes call on top of a suit/sun?
            // User requirement: "Conditions: If a player calls 'Gahwa' ... and wins the round".
            // Implementation: We set bid.type = 'GAHWA' or bid.isGahwa = true.
            // Let's assume bidType might be 'GAHWA_SUN' or just 'GAHWA'.
            // For now, let's treat 'GAHWA' as 'SUN' but with a flag.

            let effectiveMode = bidType;
            let isGahwa = false;

            if (bidType === 'GAHWA') {
                effectiveMode = 'SUN'; // Default to Sun for Gahwa? Or user must specify?
                isGahwa = true;
            }

            // Store Trump Suit if HOKUM
            if (effectiveMode === 'HOKUM' && this.gameState.floorCard) {
                this.gameState.trumpSuit = this.gameState.floorCard.suit;
            } else {
                this.gameState.trumpSuit = null;
            }

            this.gameState.bid = { type: effectiveMode, bidder: bidderPos, doubled: false, isGahwa: isGahwa };
            this.gameState.phase = 'PLAYING';
            this.gameState.currentTurnIndex = (this.dealerIndex + 1) % 4;

            // --- REDISTRIBUTE CARDS ---
            // 1. Give Floor Card to Bidder
            if (this.gameState.floorCard) {
                this.gameState.players[playerIndex].hand.push(this.gameState.floorCard);
                this.gameState.floorCard = null; // Consumed
            }

            // 2. Deal remaining 11 cards (Indices 21-31)
            let deckPointer = 21;
            for (let i = 0; i < 4; i++) {
                // DEALING LOGIC: Start from Dealer+1?
                // Standard: Anti-clockwise from right of dealer.
                // Our player loop 0..3 is fixed (0=Bottom...).
                // We just iterate 0..3, and if i == playerIndex (Bidder), give 2. Else 3.
                // This is a simplification of the actual "Dealing Order" but valid for distribution.

                // Bidder gets 2 (Total 5+1+2 = 8)
                // Others get 3 (Total 5+3 = 8)
                const count = (i === playerIndex) ? 2 : 3;

                for (let k = 0; k < count; k++) {
                    if (this.deck[deckPointer]) {
                        this.gameState.players[i].hand.push(this.deck[deckPointer++]);
                    }
                }
            }
        }
        return { success: true };
    }

    handlePlay(playerIndex, { cardIndex }) {
        const player = this.gameState.players[playerIndex];
        // Note: player.hand in `gameState.players` is empty for public?
        // Wait. `this.gameState.players` was initialized in `start()` line 155 with `hand: []`.
        // BUT `handlePlay` uses `player.hand`...
        // `start()`: `this.gameState.players.forEach(p => { p.hand = []; ... })`.
        // `dealCards()`: `this.gameState.players[playerIdx].hand.push(card);`
        // So `gameState.players` DOES contain the hand server-side.
        // It's only stripped when sending to client via `socket.emit`?
        // `server.js` might strip it? Or `Game.js` emits the whole thing?
        // Line 169: `emit('game_update', { gameState: this.gameState })`.
        // This suggests `gameState` contains full hands and cheats are possible by inspecting network traffic?
        // YES. This is a security flaw but out of scope for strict rules implementation.
        // The server variable `this.gameState` DOES have hands.

        if (!player || !player.hand[cardIndex]) return { error: `Invalid card index: ${cardIndex}` };

        const card = player.hand[cardIndex];

        // --- STRICT RULE VALIDATION ---
        // 11.1 Requirement: "Referee" (Strict Rule Engine) acts as absolute source of truth.
        const mode = this.gameState.bid.type;
        const trumpSuit = this.gameState.trumpSuit;

        // Find winning team of current trick so far
        const winningTeam = RuleVerifier.getWinningTeam(this.gameState.tableCards, mode === 'SUN' ? 'SUN' : 'HOKUM', trumpSuit, this.gameState.players);

        const isValid = RuleVerifier.isValidMove(
            card,
            player.hand,
            this.gameState.tableCards,
            mode === 'SUN' ? 'SUN' : 'HOKUM',
            trumpSuit,
            player.team,
            winningTeam
        );

        if (!isValid) {
            console.warn(`[INVALID MOVE] Player ${player.name} tried to play ${card.suit}${card.rank}`);
            return { error: 'Invalid Move (Strict Rule Violation)' };
        }

        // Remove from hand
        player.hand.splice(cardIndex, 1);

        // Add to table
        this.gameState.tableCards.push({ card, playedBy: player.position });

        // Check if trick is full (4 cards)
        if (this.gameState.tableCards.length === 4) {
            this.gameState.isTrickTransitioning = true;
            this.gameState.currentTurnIndex = -1; // Block turns

            // Schedule Resolution
            const delay = this.gameState.settings.isDebug ? 500 : 2000;

            // NOTE: Use arrow function to preserve 'this' context
            setTimeout(() => {
                this.resolveTrick();
            }, delay);

            return { success: true, message: 'Trick pending resolution' };
        } else {
            // Next turn for current trick (Simple rotation)
            this.gameState.currentTurnIndex = (this.gameState.currentTurnIndex + 1) % 4;

            // Check for Bot Turn IMMEDIATELY
            if (this.io) {
                // We must emit the update FIRST so frontend sees the played card
                this.io.to(this.roomId).emit('game_update', { gameState: this.gameState });
                this.checkBotTurn(this.io);
            }
            return { success: true };
        }
    }

    handleDeclareProject(playerIndex, { type }) {
        const player = this.gameState.players[playerIndex];

        // Basic validation: Must be first trick (roundHistory empty)
        // Also strictly should be before playing card? (Handled by UI mostly, but server can check if tableCards includes player? 
        // No, player might declared BEFORE playing. If tableCards doesn't have their card yet.)

        // Check Validity
        const validation = validateProject(player.hand, type, this.gameState.bid.type);

        if (validation.valid) {
            const playerPos = this.getPosition(playerIndex);

            // Init array if needed
            if (!this.gameState.declarations[playerPos]) {
                this.gameState.declarations[playerPos] = [];
            }

            // Logic: usually just one main project? Or multiple?
            // "Declarations" is array.
            this.gameState.declarations[playerPos].push({
                type: validation.type,
                score: validation.score,
                rank: validation.rank
            });

            // Notify others? (Usually just "Declared", not shown until reveal).
            // UI shows specific icon? "Projects" button says "Projects Announced".
            // We update public state. UI handles hiding details if needed, but for now we share it (or hide in UI).
            // UI in Table.tsx actually SHOWS the project details in the bubble: 
            // {p.type} {p.rank}
            // Real Baloot: You say "Sira", you don't show cards.
            // Our UI shows cards/icons. We'll stick to that.

            return { success: true };
        } else {
            return { error: 'Invalid Project Declaration', details: validation };
        }
    }

    setIo(io) {
        this.io = io;
    }

    toggleDebugMode(enable) {
        this.gameState.settings.isDebug = enable;
        // If debug, infinite turn duration (visually)
        this.gameState.settings.turnDuration = enable ? 9999 : 30;

        // Notify
        if (this.io) {
            this.io.to(this.roomId).emit('game_update', { gameState: this.gameState });
            this.io.to(this.roomId).emit('system_message', { text: `Debug Mode ${enable ? 'ENABLED' : 'DISABLED'}` });
        }
    }

    resolveTrick() {
        try {
            const mode = this.gameState.bid.type;
            const trumpSuit = this.gameState.trumpSuit || (this.gameState.bid.type === 'HOKUM' && this.gameState.floorCard ? this.gameState.floorCard.suit : '♠');

            // Uses imported getTrickWinner
            const winnerIdx = getTrickWinner(this.gameState.tableCards, mode === 'SUN' ? 'SUN' : 'HOKUM', trumpSuit);

            let winnerPos = null;

            if (winnerIdx !== -1) {
                const winnerCard = this.gameState.tableCards[winnerIdx];
                winnerPos = winnerCard.playedBy;
                const winnerPlayerIdx = this.gameState.players.findIndex(p => p.position === winnerPos);

                this.gameState.currentTurnIndex = winnerPlayerIdx;
            } else {
                console.error("Critical: No winner found for trick");
            }

            // Record Trick in History with CARDS
            // We must clone the cards to preserve them
            this.gameState.roundHistory.push({
                winner: winnerPos,
                cards: this.gameState.tableCards.map(t => ({ ...t.card })),
                points: 0 // Will be calculated at end or now? End is safer for complex rules.
            });

            this.gameState.tableCards = [];
            this.gameState.isTrickTransitioning = false;

            // Check for Project Reveal (End of First Trick)
            if (this.gameState.roundHistory.length === 1) {
                this.gameState.isProjectRevealing = true;
                const revealDuration = this.gameState.settings.isDebug ? 1000 : 4000;

                setTimeout(() => {
                    this.gameState.isProjectRevealing = false;
                    if (this.io) this.io.to(this.roomId).emit('game_update', { gameState: this.gameState });
                }, revealDuration);
            }

            // Check Round End (8 tricks)
            if (this.gameState.roundHistory.length === 8) {
                this.endRound();
            } else {
                if (this.io) {
                    this.io.to(this.roomId).emit('game_update', { gameState: this.gameState });
                    this.checkBotTurn(this.io);
                }
            }

        } catch (error) {
            console.error("Error in resolveTrick:", error);
            // Attempt recovery
            this.gameState.tableCards = [];
            this.gameState.isTrickTransitioning = false;
            if (this.io) this.io.to(this.roomId).emit('game_update', { gameState: this.gameState });
        }
    }

    endRound() {
        console.log("Ending Round...");
        const mode = this.gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM';
        const trumpSuit = this.gameState.trumpSuit;

        let usRaw = 0;
        let themRaw = 0;

        // Sum points from history
        this.gameState.roundHistory.forEach(trick => {
            const winnerPos = trick.winner;
            const points = this.sumTrickPoints(trick.cards, mode, trumpSuit);

            // Map winnerPos to Team
            const winnerP = this.gameState.players.find(p => p.position === winnerPos);
            if (winnerP.team === 'us') usRaw += points;
            else themRaw += points;
        });

        // Add LAST TRICK BONUS (10 points in simple Baloot rules? usually 10)
        // Check rule: "Last trick winner gets 10 points"? 
        // Not specified in prompt, but standard Baloot. 
        // Prompt only said "Scoring Arithmetic ... Sun/Hokum".
        // I will assume standard last trick bonus.
        // Identify winner of last trick
        const lastTrick = this.gameState.roundHistory[this.gameState.roundHistory.length - 1];
        const lastWinnerP = this.gameState.players.find(p => p.position === lastTrick.winner);
        if (lastWinnerP.team === 'us') usRaw += 10;
        else themRaw += 10;

        // Project Points (Simplified: Assuming we stored them in gameState.declarations)
        let usProjects = 0;
        let themProjects = 0;

        Object.keys(this.gameState.declarations).forEach(pos => {
            const p = this.gameState.players.find(pl => pl.position === pos);
            const decls = this.gameState.declarations[pos];
            if (decls) {
                decls.forEach(d => {
                    if (p.team === 'us') usProjects += d.score;
                    else themProjects += d.score;
                });
            }
        });

        // Bidder Team
        const bidderPos = this.gameState.bid.bidder;
        const bidderPlayer = this.gameState.players.find(p => p.position === bidderPos);
        const bidderTeam = bidderPlayer ? bidderPlayer.team : 'us'; // Default

        // Calculate Final
        const result = calculateRoundResult(usRaw, themRaw, usProjects, themProjects, mode, bidderTeam);

        // Gahwa Logic
        if (this.gameState.bid.isGahwa) {
            const bidderWon = (bidderTeam === 'us' && result.us > result.them) || (bidderTeam === 'them' && result.them > result.us);
            if (bidderWon) {
                // VICTORY
                console.log(`GAHWA VICTORY for ${bidderTeam}`);
                this.gameState.matchScores[bidderTeam] = 152; // Instant Win
                // Notify
                if (this.io) this.io.to(this.roomId).emit('system_message', { text: `GAHWA! ${bidderTeam.toUpperCase()} WINS THE GAME!` });
                // End game flow?
            } else {
                // Loss (Khusara handled by calculateRoundResult? If strictly implemented there)
                // But Gahwa usually implies big penalty or loss. 
                // If normal Khusara logic applies, they lose everything.
            }
        }

        // Update Match Scores
        this.gameState.matchScores.us += result.us;
        this.gameState.matchScores.them += result.them;

        console.log(`Round Score: US=${result.us}, THEM=${result.them}`);

        // Reset Phase to WAIT or BIDDING?
        // Check Game Over
        if (this.gameState.matchScores.us >= 152 || this.gameState.matchScores.them >= 152) {
            // Game Over
            if (this.io) this.io.to(this.roomId).emit('system_message', { text: 'GAME OVER' });
        } else {
            // Rotate Dealer
            this.dealerIndex = (this.dealerIndex + 1) % 4;
            // Delay restart
            setTimeout(() => {
                this.start();
            }, 5000);
        }

        if (this.io) this.io.to(this.roomId).emit('game_update', { gameState: this.gameState });
    }

    // Helper wrapper for scoring module
    sumTrickPoints(cards, mode, trumpSuit) {
        // Need to import/require sumCardPoints?
        const { sumCardPoints } = require('./scoring');
        return sumCardPoints(cards, mode, trumpSuit);
    }
}

module.exports = Game;
