import React, { useState } from 'react';
import { PlayerPosition, GamePhase } from '../types';
import CardPicker from './CardPicker';

interface ScenarioTableProps {
    scenarioState: any; // Using any for flexibility during dev, improve later
    onUpdateState: (newState: any) => void;
}

const ScenarioTable: React.FC<ScenarioTableProps> = ({ scenarioState, onUpdateState }) => {
    const [editingHand, setEditingHand] = useState<number | null>(null); // Index of player being edited
    const [editingFloor, setEditingFloor] = useState(false);
    const [editingPlayedPos, setEditingPlayedPos] = useState<PlayerPosition | null>(null);
    const [editingBidPos, setEditingBidPos] = useState<PlayerPosition | null>(null);

    // Calculate used cards to disable them in picker
    const getTakenCards = () => {
        let taken: string[] = [];

        // From Hands (exclude current editing hand)
        scenarioState.players.forEach((p: any, idx: number) => {
            if (idx !== editingHand) {
                p.hand.forEach((c: any) => taken.push(`${c.rank}${c.suit}`));
            }
        });

        // From Floor (exclude if editing floor)
        if (!editingFloor && scenarioState.floorCard) {
            taken.push(`${scenarioState.floorCard.rank}${scenarioState.floorCard.suit}`);
        }

        // From Played Cards (exclude if editing specific played card)
        if (scenarioState.playedCards) {
            Object.entries(scenarioState.playedCards).forEach(([pos, card]: [string, any]) => {
                if (pos !== editingPlayedPos) {
                    taken.push(`${card.rank}${card.suit}`);
                }
            });
        }

        return taken;
    };

    const getMyCards = () => {
        if (editingHand !== null) {
            const p = scenarioState.players[editingHand];
            return p.hand.map((c: any) => `${c.rank}${c.suit}`);
        }
        if (editingFloor && scenarioState.floorCard) {
            return [`${scenarioState.floorCard.rank}${scenarioState.floorCard.suit}`];
        }
        if (editingPlayedPos && scenarioState.playedCards?.[editingPlayedPos]) {
            const c = scenarioState.playedCards[editingPlayedPos];
            return [`${c.rank}${c.suit}`];
        }
        return [];
    };

    const handleCardSelect = (rank: string, suit: string) => {
        // --- HAND EDITING ---
        if (editingHand !== null) {
            const updatedPlayers = scenarioState.players.map((p: any) => ({ ...p, hand: [...p.hand] }));
            const player = updatedPlayers[editingHand];
            const isBidding = scenarioState.phase === GamePhase.Bidding;
            const limit = isBidding ? 5 : 8;

            const existsIdx = player.hand.findIndex((c: any) => c.rank === rank && c.suit === suit);
            if (existsIdx >= 0) {
                player.hand.splice(existsIdx, 1);
            } else {
                if (player.hand.length < limit) {
                    player.hand.push({ rank, suit });
                    if (player.hand.length === limit) setEditingHand(null);
                }
            }
            onUpdateState({ ...scenarioState, players: updatedPlayers });
            return;
        }

        // --- FLOOR EDITING ---
        if (editingFloor) {
            // Toggle: If same card selected, remove it. Else replace it.
            const current = scenarioState.floorCard;
            if (current && current.rank === rank && current.suit === suit) {
                onUpdateState({ ...scenarioState, floorCard: null });
            } else {
                onUpdateState({ ...scenarioState, floorCard: { rank, suit } });
                setEditingFloor(false); // Auto close
            }
            return;
        }

        // --- PLAYED CARD EDITING ---
        if (editingPlayedPos) {
            const current = scenarioState.playedCards?.[editingPlayedPos];
            const newPlayed = { ...(scenarioState.playedCards || {}) };

            if (current && current.rank === rank && current.suit === suit) {
                delete newPlayed[editingPlayedPos];
            } else {
                newPlayed[editingPlayedPos] = { rank, suit };
                setEditingPlayedPos(null); // Auto close
            }
            onUpdateState({ ...scenarioState, playedCards: newPlayed });
            return;
        }
    };

    const handleBidSelect = (action: string, suit?: string) => {
        if (!editingBidPos) return;

        const newBids = { ...(scenarioState.playerBids || {}) };

        if (action === 'DELETE') {
            delete newBids[editingBidPos];
        } else {
            newBids[editingBidPos] = { action, suit };
        }

        onUpdateState({ ...scenarioState, playerBids: newBids });
        setEditingBidPos(null);
    };

    const getPositionStyle = (pos: PlayerPosition) => {
        switch (pos) {
            case PlayerPosition.Bottom: return { bottom: '10%', left: '50%', transform: 'translateX(-50%)' };
            case PlayerPosition.Top: return { top: '10%', left: '50%', transform: 'translateX(-50%)' };
            case PlayerPosition.Right: return { right: '5%', top: '50%', transform: 'translateY(-50%)' };
            case PlayerPosition.Left: return { left: '5%', top: '50%', transform: 'translateY(-50%)' };
            default: return {};
        }
    };

    const getTableCardStyle = (pos: PlayerPosition) => {
        switch (pos) {
            case PlayerPosition.Bottom: return { bottom: '30%', left: '50%', transform: 'translateX(-50%)' };
            case PlayerPosition.Top: return { top: '30%', left: '50%', transform: 'translateX(-50%)' };
            case PlayerPosition.Right: return { right: '20%', top: '50%', transform: 'translateY(-50%)' };
            case PlayerPosition.Left: return { left: '20%', top: '50%', transform: 'translateY(-50%)' };
            default: return {};
        }
    };

    // Position for Bid Badge (next to player)
    const getBidBadgeStyle = (pos: PlayerPosition) => {
        switch (pos) {
            case PlayerPosition.Bottom: return { bottom: '22%', left: '60%' }; // Right of player
            case PlayerPosition.Top: return { top: '22%', right: '60%' };
            case PlayerPosition.Right: return { right: '15%', top: '35%' }; // Above/side
            case PlayerPosition.Left: return { left: '15%', top: '35%' };
            default: return {};
        }
    };

    return (
        <div className="relative w-full h-[600px] bg-[#1a472a] rounded-xl border-8 border-amber-900 shadow-inner overflow-hidden">
            <div className="absolute inset-0 opacity-20 bg-[url('/felt-pattern.png')] pointer-events-none"></div>

            {/* Center Area */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center z-10">
                {scenarioState.phase === GamePhase.Bidding ? (
                    // Floor Card Slot
                    <div
                        onClick={() => setEditingFloor(true)}
                        className={`w-20 h-28 border-2 border-dashed rounded-lg flex items-center justify-center cursor-pointer transition-all hover:scale-105
                            ${scenarioState.floorCard ? 'bg-white border-solid border-slate-900' : 'border-yellow-500/50 bg-black/20 text-yellow-500/50'}
                        `}
                    >
                        {scenarioState.floorCard ? (
                            <span className={`text-2xl font-bold ${['H', 'D'].includes(scenarioState.floorCard.suit) ? 'text-red-600' : 'text-black'}`}>
                                {scenarioState.floorCard.rank} {['S', 'H', 'D', 'C'].find(s => s === scenarioState.floorCard.suit)}
                            </span>
                        ) : (
                            <span className="text-xs">Floor</span>
                        )}
                    </div>
                ) : (
                    // Playing Phase Decoration
                    <div className="w-32 h-32 bg-green-900/50 rounded-full border-4 border-yellow-600/30 flex items-center justify-center">
                        <span className="text-yellow-500/50 font-bold">Table</span>
                    </div>
                )}
            </div>

            {/* Players & Playing Elements */}
            {scenarioState.players.map((p: any, idx: number) => {
                const playedCard = scenarioState.playedCards?.[p.position];
                const playerBid = scenarioState.playerBids?.[p.position];

                return (
                    <React.Fragment key={idx}>
                        {/* Player Hand Area */}
                        <div
                            onClick={() => setEditingHand(idx)}
                            className={`absolute p-4 rounded-xl border-2 transition-all cursor-pointer hover:scale-105 active:scale-95 z-20
                        ${editingHand === idx ? 'bg-yellow-900/80 border-yellow-500 shadow-[0_0_20px_rgba(234,179,8,0.5)]' : 'bg-black/40 border-slate-600 hover:bg-black/60'}
                        `}
                            style={getPositionStyle(p.position)}
                        >
                            <div className="text-center mb-2">
                                <span className="font-bold text-white shadow-black drop-shadow-md">{p.name || p.position}</span>
                                <span className="block text-xs text-yellow-500">{p.hand.length} Cards</span>
                            </div>
                            <div className="flex -space-x-2">
                                {p.hand.map((c: any, cIdx: number) => (
                                    <div key={cIdx} className="w-8 h-12 bg-white rounded border border-gray-400 text-black text-xs flex items-center justify-center shadow-md">
                                        <span className={['H', 'D'].includes(c.suit) ? 'text-red-600' : 'text-black'}>{c.rank}</span>
                                    </div>
                                ))}
                                {p.hand.length === 0 && <div className="w-8 h-12 border border-dashed border-gray-500 rounded opacity-50"></div>}
                            </div>
                        </div>

                        {/* Played Card Slot (Only in Playing Phase) */}
                        {scenarioState.phase === GamePhase.Playing && (
                            <div
                                onClick={() => setEditingPlayedPos(p.position)}
                                className={`absolute w-16 h-24 rounded border-2 transition-all cursor-pointer hover:scale-110 z-10 flex items-center justify-center
                                ${editingPlayedPos === p.position ? 'border-yellow-400 shadow-[0_0_15px_rgba(250,204,21,0.6)]' : 'border-dashed border-slate-500/50 bg-black/10'}
                                ${playedCard ? 'bg-white border-solid' : ''}
                            `}
                                style={getTableCardStyle(p.position)}
                            >
                                {playedCard ? (
                                    <span className={`text-xl font-bold ${['H', 'D'].includes(playedCard.suit) ? 'text-red-600' : 'text-black'}`}>
                                        {playedCard.rank}
                                    </span>
                                ) : (
                                    <span className="text-[10px] text-slate-500 opacity-50">Play</span>
                                )}
                            </div>
                        )}

                        {/* Bid Badge (Only in Bidding Phase) */}
                        {scenarioState.phase === GamePhase.Bidding && (
                            <div
                                onClick={() => setEditingBidPos(p.position)}
                                className={`absolute px-3 py-1 rounded-full border-2 transition-all cursor-pointer hover:scale-110 z-30 font-bold text-sm shadow-lg
                                ${playerBid ? 'bg-blue-600 border-blue-400 text-white' : 'bg-slate-700 border-slate-500 text-slate-400'}
                            `}
                                style={getBidBadgeStyle(p.position)}
                            >
                                {playerBid ? (
                                    <span>
                                        {playerBid.action === 'HOKUM' ? (
                                            <>Hokum {['S', 'H', 'D', 'C'].includes(playerBid.suit) && <span className={['H', 'D'].includes(playerBid.suit) ? 'text-red-300' : 'text-white'}>{playerBid.suit}</span>}</>
                                        ) : playerBid.action}
                                    </span>
                                ) : "Set Bid"}
                            </div>
                        )}

                    </React.Fragment>
                )
            })}

            {/* Card Picker Modal */}
            {(editingHand !== null || editingFloor || editingPlayedPos) && (
                <div className="absolute inset-0 bg-black/60 z-50 flex items-center justify-center -backdrop-blur-sm">
                    <div className="relative">
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                setEditingHand(null);
                                setEditingFloor(false);
                                setEditingPlayedPos(null);
                            }}
                            className="absolute -top-4 -right-4 w-8 h-8 bg-red-500 text-white rounded-full font-bold shadow-lg hover:bg-red-600 z-10"
                        >
                            X
                        </button>
                        <CardPicker
                            onSelect={handleCardSelect}
                            takenCards={getTakenCards()}
                            myCards={getMyCards()}
                        />
                    </div>
                </div>
            )}

            {/* Bid Picker Modal */}
            {editingBidPos && (
                <div className="absolute inset-0 bg-black/60 z-50 flex items-center justify-center -backdrop-blur-sm">
                    <div className="bg-slate-800 p-6 rounded-xl border border-slate-600 shadow-2xl max-w-sm w-full">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-white font-bold text-lg">Select Bid for {editingBidPos}</h3>
                            <button onClick={() => setEditingBidPos(null)} className="text-red-400 hover:text-red-300">Close</button>
                        </div>

                        <div className="grid grid-cols-2 gap-3 mb-4">
                            <button onClick={() => handleBidSelect('PASS')} className="p-3 bg-slate-700 hover:bg-slate-600 rounded text-white font-bold">Pass</button>
                            <button onClick={() => handleBidSelect('ASHKEL')} className="p-3 bg-red-900/50 hover:bg-red-900 rounded text-red-200 border border-red-500/30 font-bold">Ashkel</button>
                            <button onClick={() => handleBidSelect('SUN')} className="p-3 bg-yellow-600/50 hover:bg-yellow-600 rounded text-yellow-200 border border-yellow-500/30 font-bold col-span-2">Sun ☀️</button>
                        </div>

                        <div className="mb-2 text-slate-400 text-sm font-bold">Hokum (Suit)</div>
                        <div className="grid grid-cols-4 gap-2">
                            {['S', 'H', 'D', 'C'].map(suit => (
                                <button
                                    key={suit}
                                    onClick={() => handleBidSelect('HOKUM', suit)}
                                    className="p-2 bg-slate-700 hover:bg-slate-600 rounded text-xl border border-slate-500"
                                >
                                    <span className={['H', 'D'].includes(suit) ? 'text-red-500' : 'text-white'}>
                                        {{ S: '♠', H: '♥', D: '♦', C: '♣' }[suit]}
                                    </span>
                                </button>
                            ))}
                        </div>

                        <button onClick={() => handleBidSelect('DELETE')} className="mt-6 w-full py-2 border border-red-500 text-red-500 rounded hover:bg-red-500/10">
                            Clear Bid
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ScenarioTable;
