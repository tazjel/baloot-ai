
import { io, Socket } from "socket.io-client";

const SERVER_URL = "http://localhost:3005"; // Direct connection to Backend (Bypasses Proxy)

class SocketService {
    public socket: Socket | null = null;

    connect() {
        if (!this.socket) {
            this.socket = io(SERVER_URL, {
                transports: ['websocket', 'polling'], // Try websocket first
                reconnection: true,
            });
            this.socket.on('connect', () => {
                console.log('Connected to Game Server:', this.socket?.id);
            });
            this.socket.on('connect_error', (err) => {
                console.error('Socket Connection Error:', err);
            });
        } else if (!this.socket.connected) {
        } else if (!this.socket.connected) {
            this.socket.connect();
        }
        return this.socket;
    }

    disconnect() {
        if (this.socket && this.socket.connected) {
            this.socket.disconnect();
        }
    }

    createRoom(callback: (res: any) => void) {
        if (!this.socket) return;
        this.socket.emit('create_room', {}, callback);
    }

    joinRoom(roomId: string, playerName: string, callback: (res: any) => void) {
        if (!this.socket) return;
        this.socket.emit('join_room', { roomId, playerName }, callback);
    }

    sendAction(roomId: string, action: string, payload: any, callback?: (res: any) => void) {
        if (!this.socket) {
            if (callback) callback({ success: false, error: "Socket not connected" });
            return;
        }
        this.socket.emit('game_action', { roomId, action, payload }, (res: any) => {
            // @ts-ignore
            import('../utils/devLogger').then(({ devLogger }) => {
                if (res.success) devLogger.log('SOCKET', 'Action Success', { action });
                else devLogger.error('SOCKET', 'Action Failed', { action, error: res.error });
            });

            if (callback) {
                callback(res);
            } else if (!res.success) {
                console.error("Action Failed:", res.error);
            }
        });
    }

    sendDebugAction(roomId: string, action: string, payload: any) {
        if (!this.socket) return;
        this.socket.emit('debug_action', { roomId, action, payload }, (res: any) => {
            if (!res.success) {
                console.error("Debug Action Failed:", res.error);
            }
        });
    }

    onGameUpdate(callback: (gameState: any) => void) {
        if (!this.socket) return () => { };

        const handler = (data: any) => {
            // @ts-ignore
            import('../utils/devLogger').then(({ devLogger }) => devLogger.log('SOCKET', 'Game Update Received', { phase: data.gameState.phase, turn: data.gameState.currentTurnIndex }));
            callback(data.gameState)
        };

        this.socket.on('game_update', handler);
        return () => {
            this.socket?.off('game_update', handler);
        };
    }

    onGameStart(callback: (gameState: any) => void) {
        if (!this.socket) return () => { };
        const handler = (data: any) => callback(data.gameState);
        this.socket.on('game_start', handler);
        return () => {
            this.socket?.off('game_start', handler);
        };
    }

    addBot(roomId: string, callback: (res: any) => void) {
        if (!this.socket) return;
        this.socket.emit('add_bot', { roomId }, callback);
    }


    onBotSpeak(callback: (data: { playerIndex: number, text: string, emotion: string }) => void) {
        if (!this.socket) return () => { };
        const handler = (data: any) => callback(data);
        this.socket.on('bot_speak', handler);
        return () => {
            this.socket?.off('bot_speak', handler);
        };
    }

    // Add more event wrappers here
}

export default new SocketService();
