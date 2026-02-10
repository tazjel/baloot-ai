import React from 'react';
import ScoreBadge from './ScoreBadge';
import ContractIndicator from './ContractIndicator';
import { GameState, Bid, Player, DoublingLevel } from '../../types';

interface HudLayerProps {
    matchScores: { us: number; them: number };
    bid: Bid;
    players: Player[];
    doublingLevel: DoublingLevel;
    isDealer: boolean;
    metadata?: GameState['metadata'];
}

export default function HudLayer({
    matchScores,
    bid,
    players,
    doublingLevel,
    isDealer,
    metadata,
}: HudLayerProps) {
    return (
        <>
            {/* Score Badge */}
            <ScoreBadge matchScores={matchScores} />

            {/* Ghost of Baloot Past HUD */}
            {metadata?.original_final_scores && (
                <div className="absolute top-28 left-4 z-40 bg-black/60 backdrop-blur-md p-2 rounded-lg border border-purple-500/50 shadow-lg flex flex-col gap-1 animate-in slide-in-from-left duration-700">
                    <div className="text-[10px] text-purple-300 font-bold uppercase tracking-wider flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse"></span>
                        Ghost of Past
                    </div>
                    {(() => {
                        const curUs = matchScores.us;
                        const origUs = metadata.original_final_scores.us;
                        const origThem = metadata.original_final_scores.them;
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

            {/* Contract Indicator */}
            <div className="absolute top-16 left-4 z-50">
                <ContractIndicator bid={bid} players={players} doublingLevel={doublingLevel || 1} />
            </div>

            {/* Dealer Badge for Me */}
            {isDealer && (
                <div className="absolute top-4 right-4 bg-white/90 px-3 py-1 rounded-full shadow-lg border border-yellow-500 flex items-center gap-2 animate-in fade-in duration-700">
                    <div className="w-5 h-5 bg-[var(--color-premium-gold)] rounded-full flex items-center justify-center font-bold text-xs text-black">D</div>
                    <span className="text-xs font-bold text-gray-800">أنت الموزع</span>
                </div>
            )}
        </>
    );
}
