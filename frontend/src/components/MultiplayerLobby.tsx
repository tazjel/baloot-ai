
import React, { useState, useEffect } from 'react';
import { ArrowLeft, Users, Play, Copy, Loader, Wifi } from 'lucide-react';
import socketService from '../services/SocketService';
import { devLogger } from '../utils/devLogger';

interface MultiplayerLobbyProps {
    onBack: () => void;
    onGameStart: (gameState: any, myIndex: number, roomId: string) => void;
}

const MultiplayerLobby: React.FC<MultiplayerLobbyProps> = ({ onBack, onGameStart }) => {
    const [playerName, setPlayerName] = useState(() => {
        const profile = localStorage.getItem('baloot_user_profile');
        return profile ? JSON.parse(profile).firstName : '';
    });
    const [roomCode, setRoomCode] = useState('');
    const [error, setError] = useState('');
    const [isConnecting, setIsConnecting] = useState(false);
    const [createdRoomId, setCreatedRoomId] = useState<string | null>(null);

    useEffect(() => {
        // Connect to socket when entering lobby
        socketService.connect();

        return () => {
            // Don't disconnect here, we might need it for the game.
            // But if we go back, maybe? For now, keep connection.
        };
    }, []);

    const handleCreateRoom = () => {
        setIsConnecting(true);
        setError('');

        socketService.createRoom((response: any) => {
            setIsConnecting(false);
            if (response.success) {
                setCreatedRoomId(response.roomId);
                // Auto-join the created room
                handleJoinRoom(response.roomId);
            } else {
                setError(response.error || 'Failed to create room');
            }
        });
    };

    const handleJoinRoom = (code: string = roomCode) => {
        if (!code || !playerName) {
            setError('Please enter your name and a room code');
            return;
        }

        setIsConnecting(true);
        setError('');

        socketService.joinRoom(code.toUpperCase(), playerName, (response: any) => {
            setIsConnecting(false);
            if (response.success) {
                devLogger.log('LOBBY', 'Joined Room', response);
                // We have joined! Now we wait for game start OR if full, server might send game_started separately
                // But for now, our server sends immediate gamestate. 
                // In a real lobby, we'd wait. 
                // If the server sends gameState, it means we entered. 
                // But we might be WAITING.

                // For Phase 1 of Multiplayer:
                // Just pass the state up. The Game View will render 'WAITING' if needed.
                onGameStart(response.gameState, response.yourIndex, code.toUpperCase());
            } else {
                setError(response.error || 'Failed to join room');
            }
        });
    };

    return (
        <div className="flex flex-col items-center justify-center w-full h-full bg-[#050505] text-white p-4 font-['Tajawal'] relative overflow-hidden">
            {/* Background Pattern */}
            <div className="absolute inset-0 opacity-10 pointer-events-none" style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23d4af37' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
            }}></div>

            <div className="z-10 bg-[#1e1e1e] border border-gray-700 p-8 rounded-2xl shadow-2xl w-full max-w-md backdrop-blur-sm bg-opacity-90">
                <div className="flex items-center justify-between mb-8">
                    <button onClick={onBack} className="p-2 hover:bg-gray-700 rounded-full transition-colors">
                        <ArrowLeft className="text-gray-400" />
                    </button>
                    <h1 className="text-2xl font-bold text-yellow-500 flex items-center gap-2">
                        <Wifi size={24} />
                        Multiplayer Lobby
                    </h1>
                    <div className="w-10"></div>
                </div>

                {error && (
                    <div className="bg-red-900/50 border border-red-500 text-red-200 p-3 rounded-lg mb-6 text-sm text-center animate-pulse">
                        {error}
                    </div>
                )}

                <div className="space-y-6">
                    <div>
                        <label className="block text-gray-400 text-sm mb-2">My Name</label>
                        <input
                            type="text"
                            value={playerName}
                            onChange={(e) => setPlayerName(e.target.value)}
                            className="w-full bg-[#121212] border border-gray-600 rounded-lg p-3 text-white focus:border-yellow-500 focus:outline-none transition-colors"
                            placeholder="Enter your name"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {/* Join Existing */}
                        <div className="col-span-2">
                            <label className="block text-gray-400 text-sm mb-2">Room Code</label>
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={roomCode}
                                    onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                                    maxLength={4}
                                    className="flex-1 bg-[#121212] border border-gray-600 rounded-lg p-3 text-white focus:border-yellow-500 focus:outline-none font-mono tracking-widest text-center uppercase text-lg"
                                    placeholder="ABCD"
                                />
                                <button
                                    onClick={() => handleJoinRoom()}
                                    disabled={isConnecting || !roomCode}
                                    className="bg-yellow-600 hover:bg-yellow-500 text-black font-bold px-6 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                >
                                    {isConnecting ? <Loader className="animate-spin" /> : <Play size={20} />}
                                    Join
                                </button>
                            </div>
                        </div>

                        <div className="relative flex py-2 items-center col-span-2">
                            <div className="flex-grow border-t border-gray-700"></div>
                            <span className="flex-shrink-0 mx-4 text-gray-500 text-xs uppercase">Or</span>
                            <div className="flex-grow border-t border-gray-700"></div>
                        </div>

                        {/* Create New */}
                        <button
                            onClick={handleCreateRoom}
                            disabled={isConnecting}
                            className="col-span-2 bg-[#2a2a2a] hover:bg-[#333] border border-gray-600 text-yellow-500 font-bold p-4 rounded-lg transition-all flex items-center justify-center gap-2 group"
                        >
                            {isConnecting ? <Loader className="animate-spin" /> : <Users className="group-hover:scale-110 transition-transform" />}
                            Create New Room
                        </button>
                    </div>
                </div>

                {createdRoomId && (
                    <div className="mt-6 bg-green-900/30 border border-green-500/50 rounded-xl p-4 text-center animate-in fade-in slide-in-from-bottom-4">
                        <p className="text-gray-400 text-sm mb-1">Room Created!</p>
                        <div className="text-3xl font-mono font-bold text-green-400 tracking-[0.5em] mb-2">{createdRoomId}</div>
                        <p className="text-xs text-green-200/70">Automatic join in progress...</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default MultiplayerLobby;
