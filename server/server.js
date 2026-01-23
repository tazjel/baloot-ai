
const express = require('express');
const http = require('http');
const { Server } = require("socket.io");
const cors = require('cors');
const RoomManager = require('./RoomManager');

const app = express();
app.use(cors());

const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*", // Allow all for dev, restrict in prod
        methods: ["GET", "POST"]
    }
});

const PORT = 3001;

io.on('connection', (socket) => {
    console.log('User connected:', socket.id);

    // Create Room
    socket.on('create_room', (data, callback) => {
        try {
            const roomId = RoomManager.createRoom();
            console.log(`Room [${roomId}] created by ${socket.id}`);

            // Set IO for the game instance
            const game = RoomManager.getGame(roomId);
            if (game) game.setIo(io);

            callback({ success: true, roomId });
        } catch (error) {
            callback({ success: false, error: error.message });
        }
    });

    // Join Room
    socket.on('join_room', ({ roomId, playerName }, callback) => {
        try {
            console.log(`Player ${playerName} (${socket.id}) joining room ${roomId}`);
            const { game, player } = RoomManager.joinRoom(roomId, {
                id: socket.id,
                name: playerName,
                socketId: socket.id
            });

            socket.join(roomId);

            // Notify others in room
            socket.to(roomId).emit('player_joined', { player });

            // Return current game state to joiner
            callback({
                success: true,
                gameState: game.gameState,
                yourIndex: player.index
            });

            // Check if full to start
            if (game.isFull()) {
                const started = game.start();
                if (started) {
                    io.to(roomId).emit('game_start', { gameState: game.gameState });
                }
            }

        } catch (error) {
            console.error('Join Error:', error.message);
            callback({ success: false, error: error.message });
        }
    });

    // Game Action
    socket.on('game_action', ({ roomId, action, payload }, callback) => {
        try {
            const game = RoomManager.getGame(roomId);
            if (!game) throw new Error('Game not found');

            // Map 'EMOTE' differently if needed, or handle inside Game
            if (action === 'EMOTE') {
                // Simple broadcast for now
                socket.to(roomId).emit('emote', { playerId: socket.id, ...payload });
                callback({ success: true });
                return;
            }

            const result = game.handleAction(socket.id, action, payload);

            if (result.error) {
                callback({ success: false, error: result.error });
            } else {
                callback({ success: true });
                // Broadcast update to everyone in room
                io.to(roomId).emit('game_update', { gameState: game.gameState });

                // CHECK FOR BOT TURN
                game.checkBotTurn(io);
            }
        } catch (error) {
            console.error('Action Error:', error);
            callback({ success: false, error: error.message });
        }
    });

    // Debug Action
    socket.on('debug_action', ({ roomId, action, payload }, callback) => {
        try {
            const game = RoomManager.getGame(roomId);
            if (!game) throw new Error('Game not found');

            if (action === 'TOGGLE_DEBUG') {
                game.toggleDebugMode(payload.enable);
                callback({ success: true });
            }
        } catch (error) {
            callback({ success: false, error: error.message });
        }
    });

    // Add Bot
    socket.on('add_bot', ({ roomId }, callback) => {
        try {
            const game = RoomManager.getGame(roomId);
            if (!game) throw new Error('Game not found');

            const bot = game.addBot();
            if (bot) {
                io.to(roomId).emit('player_joined', { player: bot });
                // If full, start
                if (game.isFull()) {
                    const started = game.start();
                    if (started) {
                        io.to(roomId).emit('game_start', { gameState: game.gameState });
                        // Check if first player is bot
                        game.checkBotTurn(io);
                    }
                }
                if (typeof callback === 'function') callback({ success: true });
            } else {
                if (typeof callback === 'function') callback({ success: false, error: 'Room full' });
            }
        } catch (error) {
            console.error('[ADD_BOT ERROR]', error);
            if (typeof callback === 'function') callback({ success: false, error: error.message });
        }
    });

    // Handle Disconnect
    socket.on('disconnect', () => {
        console.log('User disconnected:', socket.id);
        const result = RoomManager.handleDisconnect(socket.id);

        if (result) {
            if (result.roomDeleted) {
                console.log(`Room ${result.roomId} deleted (empty)`);
            } else if (result.replacedWithBot) {
                console.log(`Player replaced with Bot in room ${result.roomId}`);
                io.to(result.roomId).emit('game_update', { gameState: result.game.gameState });
                io.to(result.roomId).emit('system_message', { text: `${result.botPlayer.name} replaces disconnected player.` });

                // Trigger Bot Check (if it was their turn)
                if (result.game) result.game.checkBotTurn(io);
            } else if (result.removed) {
                console.log(`Player removed from room ${result.roomId}`);
                io.to(result.roomId).emit('game_update', { gameState: result.game.gameState });
                // We might need a specific 'player_left' event if client handles it specially
                // But game_update should suffice for waiting room
            }
        }
    });
});

server.listen(PORT, () => {
    console.log(`🃏 Baloot Game Server running on port ${PORT}`);
});
