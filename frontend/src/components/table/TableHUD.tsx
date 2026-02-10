import React from 'react';
import { AnimatePresence } from 'framer-motion';
import { GameState, Player, Bid } from '../../types';
import { TensionLevel } from '../../hooks/useGameTension';

import { QaydOverlay } from '../overlays/QaydOverlay';
import { HeartbeatLayer } from '../effects/HeartbeatLayer';
import SawaModal from '../SawaModal';
import GablakTimer from '../GablakTimer';
import ScoreBadge from './ScoreBadge';
import ContractIndicator from './ContractIndicator';

interface TableHUDProps {
    gameState: GameState;
    players: Player[];
    bid: Bid;
    matchScores: { us: number; them: number };
    tension: TensionLevel;
    bpm: number;
    onPlayerAction: (action: string, payload?: any) => void;
    onSawaResponse: (response: 'ACCEPT' | 'REFUSE') => void;
}

/**
 * Zone 1: HUD overlay — scores, contract indicator, timers, and modal overlays.
 * Renders above the arena. Contains no game logic, only presentation.
 */
export default function TableHUD({
    gameState,
    players,
    bid,
    matchScores,
    tension,
    bpm,
    onPlayerAction,
    onSawaResponse,
}: TableHUDProps) {
    return (
        <>
            {/* --- ZONE 1: HUD --- */}
            <ScoreBadge matchScores={matchScores} />

            {/* Ghost of Baloot Past HUD */}
            {gameState.metadata?.original_final_scores && (
                <div className="absolute top-28 left-4 z-40 bg-black/60 backdrop-blur-md p-2 rounded-lg border border-purple-500/50 shadow-lg flex flex-col gap-1 animate-in slide-in-from-left duration-700">
                    <div className="text-[10px] text-purple-300 font-bold uppercase tracking-wider flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse"></span>
                        Ghost of Past
                    </div>
                    {(() => {
                        const curUs = matchScores.us;
                        const origUs = gameState.metadata.original_final_scores.us;
                        const origThem = gameState.metadata.original_final_scores.them;
                        const diffUs = curUs - origUs;
                        return (
                            <div className="flex flex-col">
                                <span className="text-white text-xs font-medium">Original Final: {origUs} - {origThem}</span>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className={`text-sm font-bold ${diffUs >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        {diffUs > 0 ? '+' : ''}{diffUs}
                                    </span>
                                    <span className="text-[10px] text-gray-400">vs Final</span>
                                </div>
                            </div>
                        );
                    })()}
                </div>
            )}

            <div className="absolute top-16 left-4 z-50">
                <ContractIndicator bid={bid} players={players} doublingLevel={gameState.doublingLevel || 1} />
            </div>

            <GablakTimer
                biddingPhase={gameState.biddingPhase}
                isActive={gameState.biddingPhase === 'GABLAK_WINDOW'}
                duration={5}
            />

            {/* Overlays */}
            <HeartbeatLayer tension={tension} bpm={bpm} />
            <AnimatePresence>
                {gameState?.sawaState && gameState.sawaState.active && (
                    <SawaModal
                        isOpen={gameState.sawaState.active || false}
                        claimerName={players.find(p => p.position === gameState.sawaState?.claimer)?.name || 'Unknown Player'}
                        onAccept={() => onSawaResponse('ACCEPT')}
                        onRefuse={() => onSawaResponse('REFUSE')}
                    />
                )}
            </AnimatePresence>

            {/* Qayd Overlay */}
            {gameState.qaydState?.active && (
                <QaydOverlay
                    gameState={gameState}
                    isHokum={(gameState.gameMode as 'SUN' | 'HOKUM') === 'HOKUM'}
                    isClosedDouble={(gameState.doublingLevel || 0) >= 2}
                    onPlayerAction={onPlayerAction}
                    onAccusation={(type, card, trickNum, player) => {
                         onPlayerAction('QAYD_ACCUSATION', {
                             accusation: { crime_card: card, proof_card: null, violation_type: type }
                         });
                    }}
                    onCancel={() => onPlayerAction('QAYD_CANCEL')}
                    onConfirm={() => onPlayerAction('QAYD_CONFIRM')}
                />
            )}
        </>
    );
}
