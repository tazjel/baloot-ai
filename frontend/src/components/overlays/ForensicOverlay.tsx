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
    const myPlayer = players.find(p => p.index === players[0]?.index); // players[0] is 'me' in rotated view
    const isReporter = qaydState?.reporter === myPlayer?.position;

    // Debug logging
    React.useEffect(() => {
        console.log('[ForensicOverlay] Mounted', {
            active: qaydState?.active,
            reporter: qaydState?.reporter,
            myPos: myPlayer?.position,
            isReporter,
            roundHistoryLikelyType: Array.isArray(roundHistory) && roundHistory.length > 0 ? (roundHistory[0] as any).cards ? 'TRICKS' : 'SCORES' : 'EMPTY'
        });
    }, [qaydState, isReporter, roundHistory, myPlayer]);

    if (!qaydState?.active) return null;

    if (!isReporter) {
        return (
            <div className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-center justify-center flex-col animate-in fade-in zoom-in duration-300">
                <ShieldAlert className="w-20 h-20 text-yellow-500 animate-pulse mb-6 drop-shadow-glow" />
                <h2 className="text-3xl font-bold text-white mb-2 tracking-wider">UNDER INVESTIGATION</h2>
                <p className="text-gray-300 text-lg">Player <span className="text-yellow-400 font-bold">{players.find(p => p.position === qaydState.reporter)?.name || 'Unknown'}</span> has called a Qayd.</p>
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
        <div className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in zoom-in duration-200 font-sans">
            {/* Main Modal Container */}
            <div className="bg-[#2c2c2c] w-full max-w-4xl max-h-[90vh] rounded-3xl shadow-2xl flex flex-col border border-white/10 overflow-hidden relative">


                {/* Background Texture */}
                <div className="absolute inset-0 bg-[url('/patterns/sadou-pattern.png')] opacity-5 pointer-events-none"></div>

                {/* --- HEADER & TYPES --- */}
                <div className="bg-[#1a1a1a] p-6 border-b border-white/5 flex flex-col gap-4">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            <div className="bg-red-600/20 p-2 rounded-lg">
                                <ShieldAlert className="text-red-500 w-6 h-6" />
                            </div>
                            <h2 className="text-2xl font-bold text-white">Report Violation (Qayd)</h2>
                        </div>
                        <button onClick={onCancel} className="text-gray-400 hover:text-white transition-colors">
                            Close
                        </button>
                    </div>

                    {/* Violation Types Selection (Top) */}
                    <div className="flex justify-center gap-2 bg-black/20 p-2 rounded-xl">
                        {['REVOKE', 'EAT', 'UNDERTRUMP'].map(type => (
                            <button
                                key={type}
                                onClick={() => setViolationType(type)}
                                className={`flex-1 py-3 rounded-lg text-sm font-bold transition-all duration-200
                                    ${violationType === type
                                        ? 'bg-amber-500 text-black shadow-lg scale-105'
                                        : 'bg-white/5 text-gray-400 hover:bg-white/10'}
                                `}
                            >
                                {type}
                            </button>
                        ))}
                    </div>
                </div>

                {/* --- CONTENT AREA (Grid) --- */}
                <div className="flex-1 overflow-y-auto p-6 flex gap-6">

                    {/* LEFT: TRICK HISTORY (Vertical List) */}
                    <div className="flex-1 flex flex-col gap-4">
                        <div className="text-xs font-bold text-gray-400 uppercase tracking-widest px-2">Trick History</div>
                        <div className="flex flex-col gap-3">
                            {(currentRoundTricks && currentRoundTricks.length > 0 ? (currentRoundTricks as any[]) : []).map((trick: any, tIdx: number) => {
                                const hasSelection = trick.cards && trick.cards.some((p: any) =>
                                    (p.card?.id === selectedCrime?.card.id) || (p.card?.id === selectedProof?.card.id)
                                );

                                return (
                                    <div key={tIdx} className={`bg-black/40 rounded-xl p-3 border transition-all ${hasSelection ? 'border-amber-500/50 bg-amber-900/10' : 'border-white/5 hover:bg-black/60'}`}>
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="text-xs font-bold text-gray-300">Trick {tIdx + 1}</span>
                                            {hasSelection && <span className="text-[10px] text-amber-400 font-bold px-2 py-0.5 bg-amber-500/10 rounded">SELECTED</span>}
                                        </div>

                                        <div className="flex justify-start gap-2">
                                            {trick.cards && trick.cards.map((play: any, cIdx: number) => {
                                                const cardObj = play.card || play;
                                                if (!cardObj || !cardObj.id) return null;
                                                const isSelected = selectedCrime?.card.id === cardObj.id || selectedProof?.card.id === cardObj.id;

                                                return (
                                                    <div
                                                        key={cIdx}
                                                        onClick={() => handleCardSelect(cardObj, 'HISTORY', play.playedBy || 'Unknown')}
                                                        className={`relative cursor-pointer transition-transform hover:scale-105 ${isSelected ? 'scale-110 z-10' : ''}`}
                                                        style={{ width: '48px', height: '64px' }} // Fixed container size
                                                    >
                                                        {/* Scale Down Wrapper: Render card at 2x size and scale down to 0.5 to keep fonts proportional */}
                                                        <div className="origin-top-left transform scale-50 w-24 h-32">
                                                            <CardVector card={cardObj} className={`w-full h-full rounded-lg shadow-sm text-xs ${isSelected ? 'ring-4 ring-amber-500' : ''}`} />
                                                        </div>

                                                        <div className="absolute -bottom-4 left-0 w-full text-[9px] text-center text-gray-500 mt-1 truncate">
                                                            {play.playedBy}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* RIGHT: LIVE HANDS (Vertical List) - Changed to flex-1 for equal width */}
                    <div className="flex-1 flex flex-col gap-4 border-l border-white/5 pl-6">
                        <div className="text-xs font-bold text-gray-400 uppercase tracking-widest px-2">Current Hands</div>
                        <div className="flex flex-col gap-3">
                            {players.map((p, pIdx) => (
                                <div key={pIdx} className="bg-black/40 rounded-xl p-3 border border-white/5">
                                    <div className="text-xs font-bold text-gray-300 mb-2">{p.name}</div>
                                    <div className="grid grid-cols-4 gap-1">
                                        {p.hand && p.hand.map((card, cIdx) => {
                                            const isSelected = selectedProof?.card.id === card.id;
                                            return (
                                                <div
                                                    key={cIdx}
                                                    onClick={() => handleCardSelect(card, 'HAND')}
                                                    className={`cursor-pointer transition-transform hover:scale-105 ${isSelected ? 'scale-110 z-10' : ''}`}
                                                >
                                                    <CardVector card={card} className={`w-full aspect-[2/3] rounded-sm shadow-sm ${isSelected ? 'ring-2 ring-blue-500' : ''}`} />
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                </div>

                {/* --- FOOTER ACTION --- */}
                <div className="p-6 border-t border-white/5 flex justify-end gap-3 bg-[#1a1a1a]">
                    <button
                        disabled={step !== 'CONFIRM'}
                        onClick={() => {
                            if (selectedCrime && selectedProof) {
                                onAccusation(selectedCrime.card, selectedProof.card, violationType);
                            }
                        }}
                        className={`px-8 py-3 rounded-xl font-bold transition-all shadow-lg
                                ${step === 'CONFIRM'
                                ? 'bg-amber-500 text-black hover:scale-105 hover:bg-amber-400'
                                : 'bg-white/5 text-gray-500 cursor-not-allowed'}
                            `}
                    >
                        CONFIRM QAYD
                    </button>
                </div>
            </div>

        </div>
    );
};
