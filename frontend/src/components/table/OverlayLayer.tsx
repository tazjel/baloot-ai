import React from 'react';
import { AnimatePresence } from 'framer-motion';
import { GameState } from '../../types';
import { QaydOverlay } from '../overlays/QaydOverlay';
import { HeartbeatLayer } from '../effects/HeartbeatLayer';
import SawaModal from '../SawaModal';
import GablakTimer from '../GablakTimer';

interface OverlayLayerProps {
    gameState: GameState;
    tension: any;
    bpm: number;
    onPlayerAction: (action: string, payload?: any) => void;
    handleSawaResponse: (response: 'ACCEPT' | 'REFUSE') => void;
    isSendingAction: boolean;
}

export default function OverlayLayer({
    gameState,
    tension,
    bpm,
    onPlayerAction,
    handleSawaResponse,
    isSendingAction,
}: OverlayLayerProps) {
    const { players, sawaState } = gameState;

    return (
        <>
            {/* Gablak Timer */}
            <GablakTimer
                biddingPhase={gameState.biddingPhase}
                isActive={gameState.biddingPhase === 'GABLAK_WINDOW'}
                duration={5}
            />

            {/* Heartbeat Layer */}
            <HeartbeatLayer tension={tension} bpm={bpm} />

            {/* Sawa Modal */}
            <AnimatePresence>
                {sawaState && sawaState.active && (
                    <SawaModal
                        isOpen={sawaState.active || false}
                        claimerName={players.find(p => p.position === sawaState?.claimer)?.name || 'Unknown Player'}
                        onAccept={() => handleSawaResponse('ACCEPT')}
                        onRefuse={() => handleSawaResponse('REFUSE')}
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

            {/* Sending Indicator Overlay */}
            {isSendingAction && (
                <div className="absolute inset-0 bg-black/20 z-[1000] flex items-center justify-center pointer-events-none">
                    <div className="bg-white/90 backdrop-blur text-black px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 animate-pulse">
                        <div className="w-5 h-5 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
                        <span className="font-bold">Sending...</span>
                        <button
                            onClick={() => window.location.reload()}
                            className="ml-4 text-xs underline text-red-300 hover:text-white"
                        >
                            Stuck? Reload
                        </button>
                    </div>
                </div>
            )}
        </>
    );
}
