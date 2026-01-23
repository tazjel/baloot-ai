import React from 'react';
import { Gavel, ThumbsUp, ThumbsDown } from 'lucide-react';
import { PlayerPosition } from '../types';

interface SawaModalProps {
    isOpen: boolean;
    claimerName: string;
    onAccept: () => void;
    onRefuse: () => void;
}

const SawaModal: React.FC<SawaModalProps> = ({ isOpen, claimerName, onAccept, onRefuse }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-gradient-to-b from-gray-900 to-black border-2 border-[var(--color-premium-gold)] rounded-3xl p-8 max-w-md w-full shadow-[0_0_50px_rgba(212,175,55,0.3)] animate-bounce-in relative overflow-hidden">

                {/* Background Glow */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-32 bg-[var(--color-premium-gold)] opacity-20 blur-3xl rounded-full pointer-events-none"></div>

                <div className="relative z-10 flex flex-col items-center text-center gap-6">
                    <div className="bg-[var(--color-premium-gold)] p-4 rounded-full shadow-lg shadow-amber-500/20">
                        <Gavel size={48} className="text-black" />
                    </div>

                    <div>
                        <h2 className="text-3xl font-black text-white mb-2 drop-shadow-md">Sawa Check</h2>
                        <p className="text-amber-100/80 text-lg">
                            <span className="font-bold text-[var(--color-premium-gold)]">{claimerName}</span> claims to win all remaining tricks.
                        </p>
                        <p className="text-white/40 text-sm mt-2">
                            If you refuse and they lose a trick, they suffer Khasara!
                        </p>
                    </div>

                    <div className="flex gap-4 w-full mt-2">
                        <button
                            onClick={onRefuse}
                            className="flex-1 py-4 bg-red-600 hover:bg-red-500 text-white rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all hover:scale-105 active:scale-95 shadow-lg shadow-red-900/40"
                        >
                            <ThumbsDown size={20} />
                            Refuse
                        </button>

                        <button
                            onClick={onAccept}
                            className="flex-1 py-4 bg-green-600 hover:bg-green-500 text-white rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all hover:scale-105 active:scale-95 shadow-lg shadow-green-900/40"
                        >
                            <ThumbsUp size={20} />
                            Accept
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SawaModal;
