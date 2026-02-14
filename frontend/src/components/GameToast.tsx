import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Toast, ToastType } from '../hooks/useGameToast';

interface GameToastProps {
    toasts: Toast[];
    onDismiss: (id: string) => void;
}

const TYPE_STYLES: Record<ToastType, string> = {
    turn:    'border-amber-400/60 bg-gradient-to-r from-amber-900/80 to-amber-800/70 text-amber-100',
    akka:    'border-purple-400/60 bg-gradient-to-r from-purple-900/80 to-purple-800/70 text-purple-100',
    sawa:    'border-emerald-400/60 bg-gradient-to-r from-emerald-900/80 to-emerald-800/70 text-emerald-100',
    project: 'border-blue-400/60 bg-gradient-to-r from-blue-900/80 to-blue-800/70 text-blue-100',
    trick:   'border-cyan-400/60 bg-gradient-to-r from-cyan-900/80 to-cyan-800/70 text-cyan-100',
    error:   'border-red-400/60 bg-gradient-to-r from-red-900/80 to-red-800/70 text-red-100',
    info:    'border-white/30 bg-gradient-to-r from-gray-900/80 to-gray-800/70 text-gray-100',
    baloot:  'border-yellow-400/60 bg-gradient-to-r from-yellow-800/90 to-amber-700/80 text-yellow-50',
    kaboot:  'border-rose-400/60 bg-gradient-to-r from-rose-900/90 to-pink-800/80 text-rose-50',
};

export default function GameToast({ toasts, onDismiss }: GameToastProps) {
    return (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[200] flex flex-col items-center gap-2 pointer-events-none w-full max-w-sm px-4">
            <AnimatePresence mode="popLayout">
                {toasts.map((toast) => (
                    <motion.div
                        key={toast.id}
                        layout
                        initial={{ opacity: 0, y: -30, scale: 0.85 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -20, scale: 0.9 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 28 }}
                        onClick={() => onDismiss(toast.id)}
                        className={`
                            pointer-events-auto cursor-pointer
                            w-full px-4 py-2.5 rounded-xl
                            border backdrop-blur-md shadow-lg
                            flex items-center gap-3
                            text-sm font-semibold
                            ${TYPE_STYLES[toast.type]}
                        `}
                        dir="rtl"
                    >
                        <span className="text-lg flex-shrink-0">{toast.icon}</span>
                        <span className="flex-1 leading-snug">{toast.message}</span>
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    );
}
