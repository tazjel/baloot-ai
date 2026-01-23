import React from 'react';
import { GamePhase } from '../types';
import { Lock, Unlock } from 'lucide-react';

interface VariantSelectionModalProps {
    phase: GamePhase;
    isMyTurn: boolean;
    onSelect: (variant: 'OPEN' | 'CLOSED') => void;
}

const VariantSelectionModal: React.FC<VariantSelectionModalProps> = ({ phase, isMyTurn, onSelect }) => {
    if (phase !== GamePhase.VariantSelection) return null;

    if (!isMyTurn) {
        return (
            <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fadeIn">
                <div className="bg-zinc-900 border border-white/10 p-6 rounded-2xl shadow-2xl flex flex-col items-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-400 mb-4"></div>
                    <div className="text-white font-tajawal text-lg">Waiting for Buyer to choose Open/Closed...</div>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-md animate-fadeIn">
            <div className="bg-zinc-900 border border-amber-500/30 p-8 rounded-3xl shadow-2xl flex flex-col items-center max-w-md w-full mx-4">
                <h2 className="text-2xl font-bold text-amber-400 mb-2 font-tajawal">Choose Play Mode</h2>
                <p className="text-zinc-400 text-sm mb-8 text-center">
                    You have been doubled. As the Buyer, you decide: <br />
                    <span className="text-white">Open (Maftuh)</span> or <span className="text-white">Closed (Magfool)</span>?
                </p>

                <div className="flex gap-4 w-full">
                    {/* OPEN */}
                    <button
                        onClick={() => onSelect('OPEN')}
                        className="flex-1 flex flex-col items-center gap-3 bg-zinc-800 hover:bg-zinc-700 p-6 rounded-2xl border border-white/5 transition-all hover:scale-105 active:scale-95 group"
                    >
                        <div className="p-4 bg-emerald-500/20 rounded-full group-hover:bg-emerald-500/30 transition-colors">
                            <Unlock size={32} className="text-emerald-400" />
                        </div>
                        <div className="text-emerald-400 font-bold text-xl">OPEN</div>
                        <div className="text-zinc-500 text-xs">Play any card</div>
                    </button>

                    {/* CLOSED */}
                    <button
                        onClick={() => onSelect('CLOSED')}
                        className="flex-1 flex flex-col items-center gap-3 bg-zinc-800 hover:bg-zinc-700 p-6 rounded-2xl border border-white/5 transition-all hover:scale-105 active:scale-95 group"
                    >
                        <div className="p-4 bg-rose-500/20 rounded-full group-hover:bg-rose-500/30 transition-colors">
                            <Lock size={32} className="text-rose-400" />
                        </div>
                        <div className="text-rose-400 font-bold text-xl">CLOSED</div>
                        <div className="text-zinc-500 text-xs">Restricted Leads</div>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default VariantSelectionModal;
