import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, ShieldAlert, LineChart as ChartIcon } from 'lucide-react';
import { WinProbabilityGraph } from '../analytics/WinProbabilityGraph';
import { BlunderGraph } from '../analytics/BlunderGraph';
import { GameState } from '../../types';

interface WarRoomOverlayProps {
    gameState: GameState;
    showAnalytics: boolean;
    setShowAnalytics: (show: boolean) => void;
}

export const WarRoomOverlay: React.FC<WarRoomOverlayProps> = ({ gameState, showAnalytics, setShowAnalytics }) => {
    const [analyticsView, setAnalyticsView] = useState<'WIN' | 'BLUNDER'>('WIN');

    return (
        <>
            {/* Analytics Toggle (War Room) */}
            <button
                onClick={() => setShowAnalytics(!showAnalytics)}
                className={`absolute top-4 left-44 z-50 p-1.5 rounded-full border transition-all shadow-lg ${showAnalytics ? 'bg-yellow-500/80 border-yellow-300 text-white' : 'bg-white/20 border-white/30 text-white hover:bg-white/40'}`}
                title="Toggle War Room"
            >
                <ChartIcon size={18} />
            </button>

            {/* Analytics Overlay */}
            <AnimatePresence>
                {showAnalytics && gameState.analytics && (
                    <motion.div
                        initial={{ opacity: 0, y: -20, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -20, scale: 0.9 }}
                        className="absolute top-16 left-4 z-[60] w-64 h-48 sm:w-80 sm:h-60 pointer-events-none"
                    >
                        <div className="w-full h-full pointer-events-auto relative group">
                            {/* Toggle View on Click (or small button) */}
                            <div className="absolute top-2 right-2 z-10 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onClick={() => setAnalyticsView('WIN')} className={`p-1 rounded ${analyticsView === 'WIN' ? 'bg-yellow-500 text-white' : 'bg-slate-700 text-slate-400'}`}>
                                    <Trophy size={12} />
                                </button>
                                <button onClick={() => setAnalyticsView('BLUNDER')} className={`p-1 rounded ${analyticsView === 'BLUNDER' ? 'bg-red-500 text-white' : 'bg-slate-700 text-slate-400'}`}>
                                    <ShieldAlert size={12} />
                                </button>
                            </div>

                            {analyticsView === 'WIN' ? (
                                <WinProbabilityGraph data={gameState.analytics.winProbability} />
                            ) : (
                                <BlunderGraph data={gameState.analytics.blunders || {}} />
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
};
