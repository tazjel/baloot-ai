import React from 'react';
import { motion } from 'framer-motion';
import Card from './Card';
import { CardModel } from '../types';

interface CandidateMove {
    card: CardModel;
    win_rate: number;
    diff: number;
    rank: number;
}

interface GhostCardLayerProps {
    candidates: CandidateMove[];
}

export const GhostCardLayer: React.FC<GhostCardLayerProps> = ({ candidates }) => {
    if (!candidates || candidates.length === 0) return null;

    return (
        <div className="flex items-center justify-center p-4">
            <div className="flex gap-3 sm:gap-4 items-end justify-center">
                {candidates.map((cand, idx) => {
                    const isBest = idx === 0;

                    return (
                        <motion.div
                            key={idx}
                            initial={{ opacity: 0, scale: 0.5, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            transition={{ delay: idx * 0.1, duration: 0.4 }}
                            className="relative flex flex-col items-center group"
                        >
                            {/* Annotation */}
                            <div className={`mb-2 px-3 py-1 rounded-full text-sm font-bold shadow-lg backdrop-blur-md border ${isBest ? 'bg-green-500/80 border-green-300 text-white' : 'bg-blue-400/70 border-blue-200 text-white'
                                }`}>
                                +{Math.round(cand.diff * 100)}%
                            </div>

                            {/* The Ghost Card */}
                            <div className={`relative ${isBest ? 'scale-110' : 'scale-90 opacity-80'} transition-transform duration-300`}>
                                {/* Glowing Aura for Best Move */}
                                {isBest && (
                                    <div className="absolute -inset-3 bg-green-400/40 rounded-xl blur-lg animate-pulse" />
                                )}

                                <Card
                                    card={cand.card}
                                    className="w-20 h-28 sm:w-24 sm:h-36 shadow-2xl skew-x-1"
                                    isPlayable={false}
                                />

                                {/* Label */}
                                <div className="absolute -bottom-6 w-full text-center text-xs font-bold text-white drop-shadow-md">
                                    Option #{cand.rank}
                                </div>
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
};
