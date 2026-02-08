import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GraduationCap, AlertTriangle, Play, RotateCcw } from 'lucide-react';
import { GhostCardLayer } from '../GhostCardLayer';
import { CardModel as CardType } from '../../types';
import Card from '../Card';

interface InterventionData {
    type: 'BLUNDER' | 'MISTAKE';
    message: string;
    better_card: CardType;
    reason: string;
    diff: number;
    candidates?: any[]; // Added for Holographic Thought
}

interface ProfessorOverlayProps {
    intervention: InterventionData | null;
    onUndo: () => void;
    onInsist: () => void;
}

export const ProfessorOverlay: React.FC<ProfessorOverlayProps> = ({ intervention, onUndo, onInsist }) => {
    if (!intervention) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: 20 }}
                    className="w-[500px] bg-slate-900 border-2 border-yellow-500/50 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
                >
                    {/* Header */}
                    <div className="bg-gradient-to-r from-yellow-600 to-yellow-800 p-4 flex items-center gap-3">
                        <div className="p-2 bg-white/10 rounded-full">
                            <GraduationCap size={28} className="text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white leading-none">The Professor</h2>
                            <span className="text-yellow-200 text-xs font-medium tracking-wide">AI COACHING INTERVENTION</span>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="p-6 flex flex-col items-center text-center">
                        <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-3 w-full flex items-start gap-3 text-left">
                            <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={20} />
                            <div>
                                <h3 className="text-red-400 font-bold text-sm uppercase mb-1">{intervention.type} DETECTED</h3>
                                <p className="text-slate-300 text-sm leading-relaxed">
                                    {intervention.message}
                                </p>
                            </div>
                        </div>

                        <div className="w-full flex justify-center mb-8">
                            {intervention.candidates && intervention.candidates.length > 0 ? (
                                <div className="flex flex-col items-center w-full">
                                    <span className="text-xs text-slate-400 mb-2 uppercase tracking-wider">Analysis: Top Candidates</span>
                                    <GhostCardLayer candidates={intervention.candidates} />

                                    <div className="mt-4 flex flex-col items-center text-center max-w-sm">
                                        <span className="text-sm font-semibold text-green-400 mb-1">Coach's Insight:</span>
                                        <p className="text-xs text-slate-400 leading-relaxed">
                                            {intervention.reason}
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex items-center gap-8">
                                    <div className="flex flex-col items-center">
                                        <span className="text-xs text-slate-400 mb-2 uppercase tracking-wider">Better Move</span>
                                        <div className="scale-125 origin-center">
                                            <Card
                                                card={intervention.better_card}
                                                isPlayable={false}
                                                className="h-[120px]"
                                            />
                                        </div>
                                    </div>

                                    <div className="flex flex-col items-start text-left max-w-[200px]">
                                        <span className="text-sm font-semibold text-green-400 mb-1">Why it's better:</span>
                                        <p className="text-xs text-slate-400 leading-relaxed">
                                            {intervention.reason}
                                        </p>
                                        <div className="mt-2 text-xs font-mono text-slate-500">
                                            EV Diff: +{(intervention.diff * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="flex gap-4 w-full">
                            <button
                                onClick={onUndo}
                                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-semibold transition-all border border-slate-600"
                            >
                                <RotateCcw size={18} />
                                Reconsider
                            </button>
                            <button
                                onClick={onInsist}
                                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-red-600/20 hover:bg-red-600/30 text-red-200 hover:text-white font-semibold transition-all border border-red-500/30 hover:border-red-500"
                            >
                                <Play size={18} />
                                I Insist (Play it)
                            </button>
                        </div>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
};
