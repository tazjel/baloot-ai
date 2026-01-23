import React, { useState, useEffect } from 'react';
import { Player, PlayerPosition } from '../types';
import { TriangleAlert, Gavel, X, Scale, FileText, Stamp } from 'lucide-react';

interface DisputeModalProps {
    players: Player[];
    onConfirm: (suspectPos: PlayerPosition) => void;
    onCancel: () => void;
    verdict?: { isGuilty: boolean; reason: string } | null; // If present, show verdict screen
}

const DisputeModal: React.FC<DisputeModalProps> = ({ players, onConfirm, onCancel, verdict }) => {
    const [selectedSuspect, setSelectedSuspect] = useState<PlayerPosition | null>(null);
    const [step, setStep] = useState<'SELECT' | 'ANALYZING' | 'VERDICT'>('SELECT');

    useEffect(() => {
        if (verdict) {
            setStep('ANALYZING');
            // Fake analysis time for drama
            const timer = setTimeout(() => {
                setStep('VERDICT');
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [verdict]);

    const handleConfirm = () => {
        if (selectedSuspect) {
            onConfirm(selectedSuspect);
        }
    };

    return (
        <div className="absolute inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md perspective-container">
            {/* TRIBUNAL CONTAINER */}
            <div className={`
                relative w-full max-w-2xl bg-[#1e1e1e] border-2 border-[#b8860b] shadow-[0_0_50px_rgba(184,134,11,0.3)] 
                rounded-xl overflow-hidden transition-all duration-500
                ${step === 'VERDICT' ? 'scale-105 shadow-[0_0_100px_rgba(255,0,0,0.5)]' : ''}
            `}>

                {/* Header (Golden Scale) */}
                <div className="bg-gradient-to-r from-[#2c1810] via-[#3d251e] to-[#2c1810] p-4 flex items-center justify-between border-b border-[#b8860b]/50">
                    <div className="flex items-center gap-3 text-[#b8860b]">
                        <Scale size={28} />
                        <h2 className="text-2xl font-serif tracking-widest uppercase">Mahkamt Al-Baloot</h2>
                    </div>
                    {!verdict && (
                        <button onClick={onCancel} className="text-[#b8860b] hover:text-white transition-colors">
                            <X size={24} />
                        </button>
                    )}
                </div>

                <div className="p-8 min-h-[400px] flex flex-col items-center justify-center relative">

                    {/* STEP 1: SELECT SUSPECT */}
                    {step === 'SELECT' && (
                        <div className="w-full animate-in fade-in slide-in-from-bottom-5 duration-500">
                            <div className="text-center mb-8">
                                <h3 className="text-gray-300 text-lg mb-2">Who violated the laws of Baloot?</h3>
                                <p className="text-sm text-gray-500">Select the suspect to open a case file.</p>
                            </div>

                            <div className="grid grid-cols-3 gap-4 mb-8">
                                {players.filter(p => !p.position.toString().includes('Me')).map(p => (
                                    <button
                                        key={p.position}
                                        onClick={() => setSelectedSuspect(p.position)}
                                        className={`group relative p-4 rounded-xl border-2 transition-all duration-300 ${selectedSuspect === p.position
                                                ? 'bg-[#2c1810] border-red-600 shadow-[0_0_20px_rgba(220,38,38,0.4)] scale-105'
                                                : 'bg-[#2a2a2a] border-[#444] hover:border-[#b8860b] hover:bg-[#333]'
                                            }`}
                                    >
                                        <div className="text-4xl mb-2 grayscale group-hover:grayscale-0 transition-all">{p.avatar}</div>
                                        <span className={`font-bold ${selectedSuspect === p.position ? 'text-red-500' : 'text-gray-300'}`}>
                                            {p.name}
                                        </span>
                                        {selectedSuspect === p.position && (
                                            <div className="absolute top-2 right-2 text-red-600 animate-pulse">
                                                <TriangleAlert size={16} />
                                            </div>
                                        )}
                                    </button>
                                ))}
                            </div>

                            <button
                                disabled={!selectedSuspect}
                                onClick={handleConfirm}
                                className="w-full py-4 bg-gradient-to-r from-red-900 to-red-700 text-white font-bold text-lg rounded-lg shadow-lg hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all flex items-center justify-center gap-2"
                            >
                                <Gavel size={24} />
                                <span>Accuse & Judge</span>
                            </button>
                        </div>
                    )}

                    {/* STEP 2: ANALYZING */}
                    {step === 'ANALYZING' && (
                        <div className="flex flex-col items-center animate-in fade-in duration-300">
                            <div className="w-20 h-20 border-4 border-[#b8860b] border-t-transparent rounded-full animate-spin mb-6"></div>
                            <h3 className="text-[#b8860b] text-xl font-serif animate-pulse">Reviewing Evidence...</h3>
                            <p className="text-gray-500 mt-2">Consulting the Grand Baloot Book</p>
                        </div>
                    )}

                    {/* STEP 3: VERDICT */}
                    {step === 'VERDICT' && verdict && (
                        <div className="flex flex-col items-center w-full animate-in zoom-in-90 duration-300">

                            {/* STAMP ANIMATION */}
                            <div className={`
                                mb-8 transform transition-all duration-500 scale-[2] opacity-0 animate-[stamp_0.5s_ease-out_forwards]
                            `}>
                                {verdict.isGuilty ? (
                                    <div className="border-8 border-red-600 text-red-600 px-10 py-4 font-black text-5xl rotate-[-12deg] tracking-widest uppercase opacity-80 mix-blend-screen shadow-[0_0_30px_red]">
                                        GUILTY
                                    </div>
                                ) : (
                                    <div className="border-8 border-green-500 text-green-500 px-10 py-4 font-black text-5xl rotate-[12deg] tracking-widest uppercase opacity-80 mix-blend-screen shadow-[0_0_30px_green]">
                                        INNOCENT
                                    </div>
                                )}
                            </div>

                            {/* REASON CARD */}
                            <div className="bg-[#2a2a2a] p-6 rounded-lg border border-gray-600 w-full max-w-md relative">
                                <FileText className="absolute -top-6 left-1/2 -translate-x-1/2 bg-[#1e1e1e] p-2 text-gray-400 rounded-full border border-gray-600" size={40} />

                                <h4 className="text-center text-gray-300 font-bold mb-4 mt-4 uppercase tracking-wider">Judgement Reasoning</h4>
                                <p className={`text-center text-lg leading-relaxed ${verdict.isGuilty ? 'text-red-300' : 'text-green-300'}`}>
                                    "{verdict.reason}"
                                </p>
                            </div>

                            <button
                                onClick={onCancel}
                                className="mt-8 px-8 py-3 bg-white/10 hover:bg-white/20 text-white rounded-full transition-all"
                            >
                                {verdict.isGuilty ? 'Apply Penalty (Kaboot)' : 'Resume Game'}
                            </button>
                        </div>
                    )}
                </div>

                {/* STYLE FOR STAMP ANIMATION */}
                <style>{`
                    @keyframes stamp {
                        0% { transform: scale(3); opacity: 0; }
                        50% { transform: scale(1); opacity: 1; }
                        75% { transform: scale(1.1); }
                        100% { transform: scale(1) rotate(${verdict?.isGuilty ? '-12deg' : '12deg'}); opacity: 1; }
                    }
                `}</style>
            </div>
        </div>
    );
};

export default DisputeModal;
