import React, { useState } from 'react';
import { GameState, CardModel as CardType } from '../../types';
import CardVector from '../CardVector';
import { ShieldAlert, Search, Gavel } from 'lucide-react';

interface ForensicOverlayProps {
    gameState: GameState;
    onAccusation: (crime: CardType, proof: CardType, type: string) => void;
    onCancel: () => void;
}

type Step = 'SELECT_CRIME' | 'SELECT_PROOF' | 'CONFIRM';

export const ForensicOverlay: React.FC<ForensicOverlayProps> = ({ gameState, onAccusation, onCancel }) => {
    const { qaydState, roundHistory = [], currentRoundTricks = [], players = [] } = gameState;
    const [step, setStep] = useState<Step>('SELECT_CRIME');
    const [violationType, setViolationType] = useState<string>('REVOKE');

    // Track full objects for display
    const [selectedCrime, setSelectedCrime] = useState<{ card: CardType, playedBy: string } | null>(null);
    const [selectedProof, setSelectedProof] = useState<{ card: CardType, source: string } | null>(null);

    // Auth Check
    const myPos = players[0]?.position;
    const isReporter = qaydState?.reporter === myPos;

    // Debug logging
    React.useEffect(() => {
        console.log('[ForensicOverlay] Mounted', {
            active: qaydState?.active,
            reporter: qaydState?.reporter,
            isReporter,
            roundHistoryLikelyType: Array.isArray(roundHistory) && roundHistory.length > 0 ? (roundHistory[0] as any).cards ? 'TRICKS' : 'SCORES' : 'EMPTY'
        });
    }, [qaydState, isReporter, roundHistory]);

    if (!qaydState?.active) return null;

    if (!isReporter) {
        return (
            <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center flex-col animate-in fade-in zoom-in duration-300">
                <ShieldAlert className="w-20 h-20 text-yellow-500 animate-pulse mb-6 drop-shadow-glow" />
                <h2 className="text-3xl font-bold text-white mb-2 tracking-wider">UNDER INVESTIGATION</h2>
                <p className="text-gray-300 text-lg">Player <span className="text-yellow-400 font-bold">{qaydState.reporter}</span> has called a Qayd.</p>
                <div className="mt-8 flex gap-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-bounce delay-0"></div>
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-bounce delay-100"></div>
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-bounce delay-200"></div>
                </div>
            </div>
        );
    }

    const handleCardSelect = (card: CardType, context: 'HISTORY' | 'HAND', playedBy?: string) => {
        console.log('[ForensicOverlay] Card Selected', { card, context, playedBy, step });
        if (step === 'SELECT_CRIME') {
            if (context === 'HISTORY') {
                setSelectedCrime({ card, playedBy: playedBy || 'UNKNOWN' });
                setStep('SELECT_PROOF');
            }
        } else if (step === 'SELECT_PROOF') {
            setSelectedProof({ card, source: context });
            setStep('CONFIRM');
        }
    };

    return (
        <div className="absolute inset-0 z-50 bg-[#0B1120]/95 backdrop-blur-xl flex flex-col p-6 animate-in fade-in zoom-in duration-300 font-sans border-[6px] border-[#0B1120] rounded-none">

            {/* Background Texture */}
            <div className="absolute inset-0 bg-[url('/patterns/sadou-pattern.png')] opacity-5 pointer-events-none"></div>

            {/* --- HEADER --- */}
            <div className="relative flex justify-between items-center mb-6 bg-slate-900/80 p-5 rounded-2xl border border-amber-500/20 shadow-2xl overflow-hidden">
                {/* Gold Glow */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-amber-500 to-transparent opacity-50"></div>

                <div className="flex items-center gap-5 z-10">
                    <div className="bg-slate-800 p-3 rounded-xl border border-slate-700 shadow-inner">
                        <Gavel className="text-amber-500 w-10 h-10 drop-shadow-md" />
                    </div>
                    <div>
                        <h2 className="text-3xl font-extrabold text-white tracking-widest uppercase font-mono">Forensic Court</h2>
                        <div className="flex items-center gap-3 text-sm text-slate-400 mt-1">
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse"></span>
                                <span className="text-red-500 font-bold tracking-wider text-xs">RECORDING SESSION</span>
                            </div>
                            <span className="text-slate-600">|</span>
                            <span className="text-amber-500/80 font-mono">CASE ID: #{gameState.gameId?.substring(0, 6) || 'UNKNOWN'}</span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Steps Indicator */}
                    <div className="flex bg-slate-950/50 p-1.5 rounded-lg border border-slate-800 gap-1 font-mono text-xs">
                        <span className={`px-3 py-1.5 rounded ${step === 'SELECT_CRIME' ? 'bg-amber-500/20 text-amber-200 border border-amber-500/30' : 'text-slate-500'}`}>1. DETECT CRIME</span>
                        <span className="text-slate-600 py-1.5">›</span>
                        <span className={`px-3 py-1.5 rounded ${step === 'SELECT_PROOF' ? 'bg-amber-500/20 text-amber-200 border border-amber-500/30' : 'text-slate-500'}`}>2. ESTABLISH PROOF</span>
                        <span className="text-slate-600 py-1.5">›</span>
                        <span className={`px-3 py-1.5 rounded ${step === 'CONFIRM' ? 'bg-red-500/20 text-red-200 border border-red-500/30' : 'text-slate-500'}`}>3. VERDICT</span>
                    </div>
                </div>
            </div>

            {/* --- EVIDENCE BOARD --- */}
            <div className="flex-1 flex flex-col gap-6 overflow-hidden relative z-10">

                {/* 1. TIMELINE */}
                <div className="flex-1 bg-gradient-to-b from-slate-900/90 to-slate-900/60 rounded-3xl border border-slate-700/50 p-1 relative overflow-hidden flex flex-col shadow-inner group">
                    <div className="absolute top-4 left-0 bg-amber-500 text-slate-900 text-[10px] font-black px-4 py-1 rounded-r-lg uppercase tracking-widest shadow-lg shadow-amber-500/20 z-20 flex items-center gap-2">
                        <Search size={12} /> Exhibit A: Trick Timeline
                    </div>

                    {/* Film Strip Effect */}
                    <div className="absolute top-0 bottom-0 left-12 w-[1px] bg-slate-800/50 z-0"></div>
                    <div className="absolute top-0 bottom-0 right-12 w-[1px] bg-slate-800/50 z-0"></div>

                    <div className="flex-1 overflow-x-auto overflow-y-hidden flex items-center gap-8 px-8 pt-10 pb-4 scrollbar-hide">
                        {(currentRoundTricks && currentRoundTricks.length > 0 ? (currentRoundTricks as any[]) : []).map((trick: any, tIdx: number) => {
                            // Determine if this trick contains selected items
                            const hasSelection = trick.cards && trick.cards.some((p: any) =>
                                (p.card?.id === selectedCrime?.card.id) || (p.card?.id === selectedProof?.card.id)
                            );

                            return (
                                <div key={tIdx} className={`relative group/trick min-w-[160px] transition-all duration-300 ${hasSelection ? 'opacity-100 scale-100' : 'opacity-70 hover:opacity-100'}`}>
                                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] text-slate-500 font-mono bg-slate-950 px-2 py-0.5 rounded border border-slate-800">TRICK {tIdx + 1}</div>

                                    <div className="grid grid-cols-2 gap-2 p-2 bg-slate-950/40 rounded-xl border border-slate-800">
                                        {trick.cards && trick.cards.map((play: any, cIdx: number) => {
                                            const cardObj = play.card || play;
                                            if (!cardObj || !cardObj.id) return null;
                                            return (
                                                <div
                                                    key={cIdx}
                                                    onClick={() => handleCardSelect(cardObj, 'HISTORY', play.playedBy || 'Unknown')}
                                                    className={`relative cursor-pointer transition-all duration-300 
                                                ${selectedCrime?.card.id === cardObj.id ? 'ring-4 ring-red-500 shadow-[0_0_20px_rgba(239,68,68,0.6)] scale-110 z-30' : ''}
                                                ${selectedProof?.card.id === cardObj.id ? 'ring-4 ring-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.6)] scale-110 z-30' : ''}
                                                ${!selectedCrime && !selectedProof ? 'hover:scale-105 hover:z-20' : ''}
                                            `}
                                                >
                                                    <CardVector card={cardObj} className="w-14 h-20 shadow-lg rounded" />
                                                    <div className="absolute -bottom-1.5 -right-1.5 bg-black text-[7px] text-slate-300 px-1 py-px rounded border border-slate-800 font-mono">
                                                        {(play.playedBy || '?').substring(0, 3)}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>

                {/* 2. SUSPECT HANDS */}
                <div className="h-[300px] bg-slate-900/40 rounded-3xl border border-red-900/30 p-1 relative flex flex-col overflow-hidden">
                    <div className="absolute inset-0 bg-red-900/5 pointer-events-none animate-pulse"></div>
                    <div className="absolute top-4 left-0 bg-red-600 text-white text-[10px] font-black px-4 py-1 rounded-r-lg uppercase tracking-widest shadow-lg shadow-red-500/20 z-20 flex items-center gap-2">
                        <ShieldAlert size={12} /> Exhibit B: Live Hands (Unsealed)
                    </div>

                    <div className="flex-1 overflow-x-auto flex items-center gap-4 px-6 pt-10 pb-4">
                        {players.map((p, pIdx) => (
                            <div key={pIdx} className="relative bg-slate-950/60 border border-slate-800 rounded-2xl p-4 min-w-[220px] h-full flex flex-col group overflow-hidden">
                                {/* Diagonal Stamp */}
                                <div className="absolute top-6 -right-8 bg-red-600/20 text-red-500 text-[8px] font-black tracking-[0.2em] transform rotate-45 py-1 px-10 border-y border-red-600/20 z-0">
                                    CLASSIFIED
                                </div>

                                <div className="flex justify-between items-center mb-4 pb-2 border-b border-white/5 relative z-10">
                                    <div>
                                        <div className="text-xs font-bold text-slate-200">{p.name}</div>
                                        <div className="text-[10px] text-slate-500 font-mono">{p.position}</div>
                                    </div>
                                    <div className="w-2 h-2 rounded-full bg-green-500/50"></div>
                                </div>

                                <div className="flex-1 grid grid-cols-4 gap-2 content-start relative z-10">
                                    {p.hand && p.hand.map((card, cIdx) => (
                                        <div
                                            key={cIdx}
                                            onClick={() => handleCardSelect(card, 'HAND')}
                                            className={`cursor-pointer transition-all duration-200
                                                ${selectedProof?.card.id === card.id ? 'ring-2 ring-blue-500 shadow-blue-500/50 scale-110 z-20' : 'hover:-translate-y-2 opacity-90 hover:opacity-100'}
                                            `}
                                        >
                                            <CardVector card={card} className="w-full aspect-[2/3] shadow-lg rounded-sm" />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

            </div>

            {/* --- ACTION FOOTER --- */}
            <div className="mt-6 flex justify-between items-end border-t border-slate-800/50 pt-6">

                {/* Selected Context */}
                <div className="flex gap-4">
                    {/* Crime Slot */}
                    <div className={`relative w-40 p-3 rounded-xl border-2 transition-all duration-300 ${selectedCrime ? 'border-red-500/50 bg-red-950/20' : 'border-slate-800 bg-slate-900/50 border-dashed'}`}>
                        <div className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-2">The Violation</div>
                        <div className="flex items-center gap-3">
                            {selectedCrime ? (
                                <>
                                    <div className="w-8 h-10 rounded border border-white/10 overflow-hidden shadow-md">
                                        <CardVector card={selectedCrime.card} className="w-full h-full" />
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-xs text-red-200 font-bold">Selected</div>
                                        <div className="text-[9px] text-red-400">by {selectedCrime.playedBy}</div>
                                    </div>
                                </>
                            ) : (
                                <div className="text-xs text-slate-600 italic">Select card from Timeline</div>
                            )}
                        </div>
                    </div>

                    {/* Proof Slot */}
                    <div className={`relative w-40 p-3 rounded-xl border-2 transition-all duration-300 ${selectedProof ? 'border-blue-500/50 bg-blue-950/20' : 'border-slate-800 bg-slate-900/50 border-dashed'}`}>
                        <div className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-2">The Evidence</div>
                        <div className="flex items-center gap-3">
                            {selectedProof ? (
                                <>
                                    <div className="w-8 h-10 rounded border border-white/10 overflow-hidden shadow-md">
                                        <CardVector card={selectedProof.card} className="w-full h-full" />
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-xs text-blue-200 font-bold">Selected</div>
                                        <div className="text-[9px] text-blue-400">Source: {selectedProof.source}</div>
                                    </div>
                                </>
                            ) : (
                                <div className="text-xs text-slate-600 italic">Select card from Hands</div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Center Controls */}
                <div className="flex bg-slate-950 p-1.5 rounded-xl border border-slate-800 gap-1 shadow-2xl">
                    {['REVOKE', 'EAT', 'UNDERTRUMP'].map(type => (
                        <button
                            key={type}
                            onClick={() => setViolationType(type)}
                            className={`px-5 py-2.5 rounded-lg text-xs font-bold transition-all duration-300 tracking-wide
                                ${violationType === type
                                    ? 'bg-amber-600 text-white shadow-lg shadow-amber-900/50 scale-105'
                                    : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}
                            `}
                        >
                            {type}
                        </button>
                    ))}
                </div>

                {/* Primary Actions */}
                <div className="flex gap-4">
                    <button
                        onClick={onCancel}
                        className="px-6 py-3 rounded-xl text-slate-500 font-bold hover:text-slate-300 hover:bg-slate-900 transition-colors text-sm uppercase tracking-wide border border-transparent hover:border-slate-800"
                    >
                        Dismiss Case
                    </button>
                    <button
                        disabled={step !== 'CONFIRM'}
                        onClick={() => {
                            if (selectedCrime && selectedProof) {
                                onAccusation(selectedCrime.card, selectedProof.card, violationType);
                            }
                        }}
                        className={`h-14 px-8 rounded-xl font-bold flex items-center gap-3 shadow-2xl transition-all duration-300 border border-white/10
                             ${step === 'CONFIRM'
                                ? 'bg-gradient-to-br from-red-700 to-red-600 text-white hover:scale-105 hover:shadow-red-900/50 cursor-pointer'
                                : 'bg-slate-900 text-slate-700 cursor-not-allowed grayscale'}
                         `}
                    >
                        <div className={`bg-black/20 p-2 rounded-lg ${step === 'CONFIRM' ? 'animate-bounce' : ''}`}>
                            <Gavel size={20} />
                        </div>
                        <div className="text-left">
                            <div className="text-[10px] opacity-70 uppercase tracking-wider">Final Ruler</div>
                            <div className="text-sm">CONFIRM PENALTY</div>
                        </div>
                    </button>
                </div>
            </div>

        </div>
    );
};
