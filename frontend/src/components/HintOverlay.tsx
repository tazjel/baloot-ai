/**
 * HintOverlay — Floating tooltip showing the AI hint reasoning.
 *
 * Positioned above the player's hand with an amber gradient, Lightbulb icon,
 * Arabic reasoning text, and an X dismiss button.
 *
 * M17.2: AI Hint System
 */
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Lightbulb, X } from 'lucide-react';
import { HintResult } from '../types';

interface HintOverlayProps {
    hint: HintResult | null;
    isVisible: boolean;
    onDismiss: () => void;
}

const HintOverlay: React.FC<HintOverlayProps> = ({ hint, isVisible, onDismiss }) => {
    return (
        <AnimatePresence>
            {hint && isVisible && (
                <motion.div
                    key="hint-overlay"
                    initial={{ opacity: 0, y: 20, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 20, scale: 0.9 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    className="absolute bottom-36 sm:bottom-40 left-1/2 -translate-x-1/2 z-[1050]
                               bg-gradient-to-r from-amber-900/95 to-yellow-900/95 backdrop-blur-lg
                               rounded-2xl border border-amber-500/40 shadow-2xl
                               px-5 py-3 max-w-xs flex items-start gap-3"
                >
                    <Lightbulb size={20} className="text-amber-400 mt-0.5 flex-shrink-0" />
                    <span className="text-amber-200 text-sm font-bold font-tajawal leading-relaxed">
                        {hint.reasoning}
                    </span>
                    <button
                        onClick={onDismiss}
                        className="text-amber-400/60 hover:text-white transition-colors flex-shrink-0"
                        aria-label="Dismiss hint"
                    >
                        <X size={16} />
                    </button>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

export default HintOverlay;
