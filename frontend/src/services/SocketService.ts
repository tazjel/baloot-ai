import { io, Socket } from "socket.io-client";
import { GameState } from "../types";
import { devLogger } from "../utils/devLogger";
import { API_BASE_URL } from "../config";

const SERVER_URL = API_BASE_URL;

interface ApiResponse {
    success: boolean;
    error?: string;
    [key: string]: unknown;
}

class SocketService {
    public socket: Socket | null = null;
    private connectionStatusCallbacks: ((status: 'connected' | 'disconnected' | 'reconnecting', attempt?: number) => void)[] = [];
    private reconnectAttempt = 0;
    private maxReconnectAttempts = 5;

    // Stored room context for auto-rejoin on reconnect
    private activeRoomId: string | null = null;
    private activePlayerName: string | null = null;

    connect() {
        if (!this.socket) {
            this.socket = io(SERVER_URL, {
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 16000,
            });
            this.socket.on('connect', () => {
                this.reconnectAttempt = 0;
                devLogger.log('SOCKET', 'Connected to Game Server', { id: this.socket?.id });
                this.emitConnectionStatus('connected');
            });
            this.socket.on('connect_error', (err) => {
                devLogger.error('SOCKET', 'Connection Error', err);
            });
            this.socket.on('disconnect', (reason) => {
                devLogger.log('SOCKET', 'Disconnected', { reason });
                this.emitConnectionStatus('disconnected');
            });
            this.socket.io.on('reconnect_attempt', (attempt) => {
                this.reconnectAttempt = attempt;
                const delay = Math.min(1000 * Math.pow(2, attempt - 1), 16000);
                devLogger.log('SOCKET', `Reconnecting (attempt ${attempt}/${this.maxReconnectAttempts}, backoff ${delay}ms)`);
                this.emitConnectionStatus('reconnecting', attempt);
            });
            this.socket.io.on('reconnect', () => {
                this.reconnectAttempt = 0;
                devLogger.log('SOCKET', 'Reconnected successfully');
                this.emitConnectionStatus('connected');

                // Auto-rejoin room if we were in one before disconnect
                if (this.activeRoomId && this.activePlayerName) {
                    devLogger.log('SOCKET', 'Auto-rejoining room after reconnect', { roomId: this.activeRoomId });
                    this.joinRoom(this.activeRoomId, this.activePlayerName, (res) => {
                        if (res.success) {
                            devLogger.log('SOCKET', 'Auto-rejoin successful');
                        } else {
                            devLogger.error('SOCKET', 'Auto-rejoin failed', { error: res.error });
                        }
                    });
                }
            });
            this.socket.io.on('reconnect_failed', () => {
                devLogger.error('SOCKET', `Reconnection failed after ${this.maxReconnectAttempts} attempts`);
                this.emitConnectionStatus('disconnected');
            });
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

    createRoom(callback: (res: ApiResponse) => void) {
        if (!this.socket) return;
        this.socket.emit('create_room', {}, callback);
    }

    joinRoom(roomId: string, playerName: string, callback: (res: ApiResponse) => void) {
        if (!this.socket) return;
        // Store room context for auto-rejoin on reconnect
        this.activeRoomId = roomId;
        this.activePlayerName = playerName;
        this.socket.emit('join_room', { roomId, playerName }, callback);
    }

    sendAction(roomId: string, action: string, payload: Record<string, unknown>, callback?: (res: ApiResponse) => void) {
        if (!this.socket) {
            if (callback) callback({ success: false, error: "Socket not connected" });
            return;
        }
        this.socket.emit('game_action', { roomId, action, payload }, (res: ApiResponse) => {
            if (res.success) devLogger.log('SOCKET', 'Action Success', { action });
            else devLogger.error('SOCKET', 'Action Failed', { action, error: res.error });

            if (callback) {
                callback(res);
            } else if (!res.success) {
                devLogger.error('SOCKET', 'Action Failed (no callback)', { action, error: res.error });
            }
        });
    }

    sendDebugAction(roomId: string, action: string, payload: Record<string, unknown>) {
        if (!this.socket) return;
        this.socket.emit('debug_action', { roomId, action, payload }, (res: ApiResponse) => {
            if (!res.success) {
                devLogger.error('SOCKET', 'Debug Action Failed', { action, error: res.error });
            }
        });
    }

    onGameUpdate(callback: (gameState: GameState) => void) {
        if (!this.socket) return () => { };

        const handler = (data: { gameState: GameState }) => {
            devLogger.log('SOCKET', 'Game Update Received', { phase: data.gameState.phase, turn: data.gameState.currentTurnIndex });
            callback(data.gameState)
        };

        this.socket.on('game_update', handler);
        return () => {
            this.socket?.off('game_update', handler);
        };
    }

    onGameStart(callback: (gameState: GameState) => void) {
        if (!this.socket) return () => { };
        const handler = (data: { gameState: GameState }) => callback(data.gameState);
        this.socket.on('game_start', handler);
        return () => {
            this.socket?.off('game_start', handler);
        };
    }

    addBot(roomId: string, callback: (res: ApiResponse) => void) {
        if (!this.socket) return;
        this.socket.emit('add_bot', { roomId }, callback);
    }


    onBotSpeak(callback: (data: { playerIndex: number, text: string, emotion: string }) => void) {
        if (!this.socket) return () => { };
        const handler = (data: { playerIndex: number, text: string, emotion: string }) => callback(data);
        this.socket.on('bot_speak', handler);
        return () => {
            this.socket?.off('bot_speak', handler);
        };
    }

    // --- Connection Status Observer Pattern ---
    private emitConnectionStatus(status: 'connected' | 'disconnected' | 'reconnecting', attempt?: number) {
        this.connectionStatusCallbacks.forEach(cb => cb(status, attempt));
    }

    onConnectionStatus(callback: (status: 'connected' | 'disconnected' | 'reconnecting', attempt?: number) => void) {
        this.connectionStatusCallbacks.push(callback);
        return () => {
            this.connectionStatusCallbacks = this.connectionStatusCallbacks.filter(cb => cb !== callback);
        };
    }
}

export default new SocketService();
