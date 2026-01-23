
const Game = require('./Game');
const { v4: uuidv4 } = require('uuid');

class RoomManager {
    constructor() {
        this.rooms = new Map(); // roomId -> Game instance
        this.socketToRoom = new Map(); // socketId -> roomId
    }

    createRoom() {
        // Generate a simple 4 letter code for easy sharing
        const roomId = this.generateRoomCode();
        const game = new Game(roomId);
        this.rooms.set(roomId, game);
        return roomId;
    }

    joinRoom(roomId, player) {
        const game = this.rooms.get(roomId);
        if (!game) {
            throw new Error('Room not found');
        }
        if (game.isFull()) {
            throw new Error('Room is full');
        }

        const addedPlayer = game.addPlayer(player);
        this.socketToRoom.set(player.socketId, roomId);

        return { game, player: addedPlayer };
    }

    handleDisconnect(socketId) {
        const roomId = this.socketToRoom.get(socketId);
        if (roomId) {
            const game = this.rooms.get(roomId);
            if (game) {
                // If game in progress, replace with bot
                if (game.gameState.phase !== 'WAITING') {
                    const botPlayer = game.replaceWithBot(socketId);
                    return { roomId, game, replacedWithBot: true, botPlayer };
                } else {
                    // Just remove
                    game.removePlayer(socketId);
                    // If empty, remove room?
                    if (game.players.length === 0) {
                        this.rooms.delete(roomId);
                        return { roomId, roomDeleted: true };
                    }
                    return { roomId, game, removed: true };
                }
            }
            this.socketToRoom.delete(socketId);
        }
        return null;
    }

    getGame(roomId) {
        return this.rooms.get(roomId);
    }

    removeRoom(roomId) {
        this.rooms.delete(roomId);
        // Also cleanup socket map... theoretically need to iterate or track
    }

    generateRoomCode() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        let result = '';
        for (let i = 0; i < 4; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        // Ensure uniqueness (simple check)
        if (this.rooms.has(result)) return this.generateRoomCode();
        return result;
    }
}

module.exports = new RoomManager();
