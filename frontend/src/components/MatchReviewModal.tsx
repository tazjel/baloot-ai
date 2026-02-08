import React, { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, Play, Check, ChevronDown, ChevronUp } from 'lucide-react';

import { Suit } from '../types';

// Helper for card display
const MiniCard = ({ card, playedBy, isWinner }: { card: any, playedBy: string, isWinner: boolean }) => {
    if (!card) return <div className="w-12 h-16 bg-white/10 rounded border border-dashed border-white/20" />;

    const getSuitColor = (s: string) => {
        if (s === '♥' || s === '♦') return 'text-red-500';
        return 'text-black';
    };

    return (
        <div className={`flex flex-col items-center gap-1 ${isWinner ? 'scale-110' : ''}`}>
            <div className={`
                w-12 h-16 bg-white rounded shadow-md border 
                ${isWinner ? 'border-[var(--color-premium-gold)] ring-2 ring-[var(--color-premium-gold)]/50' : 'border-gray-300'}
                flex items-center justify-center relative
            `}>
                <span className={`text-xl font-bold ${getSuitColor(card.suit)}`}>{card.rank}</span>
                <span className={`absolute bottom-1 right-1 text-xs ${getSuitColor(card.suit)}`}>{card.suit}</span>
            </div>
            <span className="text-[10px] text-white/80 uppercase font-bold text-center max-w-[4rem] truncate">
                {playedBy}
            </span>
            {isWinner && <span className="text-[8px] bg-[var(--color-premium-gold)] text-black px-1 rounded">WINNER</span>}
        </div>
    );
};

interface MatchReviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    fullMatchHistory: any[];
    players: any[];
}

const MatchReviewModal: React.FC<MatchReviewModalProps> = ({ isOpen, onClose, fullMatchHistory, players }) => {
    const [selectedRoundIdx, setSelectedRoundIdx] = useState(0);
    const [selectedTrickIdx, setSelectedTrickIdx] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    const currentRound = (fullMatchHistory && fullMatchHistory.length > 0) ? fullMatchHistory[selectedRoundIdx] : { roundNumber: 0, tricks: [], bid: {}, scores: {} };
    const tricks = currentRound?.tricks || [];
    const currentTrick = tricks[selectedTrickIdx];



    // Auto-Play Logic
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isPlaying) {
            interval = setInterval(() => {
                if (selectedTrickIdx < tricks.length - 1) {
                    setSelectedTrickIdx(prev => prev + 1);
                } else {
                    setIsPlaying(false); // Stop at end of round
                }
            }, 1500); // 1.5s per trick
        }
        return () => clearInterval(interval);
    }, [isPlaying, selectedTrickIdx, tricks.length]);

    // Helper to map pos to name
    const getPlayerName = (pos: string) => {
        const p = players.find(x => x.position === pos);
        return p ? p.name : pos;
    };

    const nextTrick = () => {
        if (selectedTrickIdx < tricks.length - 1) setSelectedTrickIdx(prev => prev + 1);
    };

    const prevTrick = () => {
        if (selectedTrickIdx > 0) setSelectedTrickIdx(prev => prev - 1);
    };

    const togglePlay = () => setIsPlaying(!isPlaying);

    const prevRound = () => {
        if (selectedRoundIdx > 0) {
            setSelectedRoundIdx(prev => prev - 1);
            setSelectedTrickIdx(0);
            setIsPlaying(false);
        }
    };

    const nextRound = () => {
        if (selectedRoundIdx < fullMatchHistory.length - 1) {
            setSelectedRoundIdx(prev => prev + 1);
            setSelectedTrickIdx(0);
            setIsPlaying(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/90 backdrop-blur-md p-4">
            <div className="bg-[#1a1a1a] w-full max-w-5xl h-[90vh] rounded-3xl border border-white/10 shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in duration-300">

                {/* Header */}
                <div className="bg-black/40 p-4 border-b border-white/10 flex justify-between items-center shrink-0">
                    <h2 className="text-2xl font-black text-white flex items-center gap-3">
                        <span className="text-[var(--color-premium-gold)]">GAME REVIEW</span>
                        <span className="text-sm bg-white/10 px-3 py-1 rounded-full text-gray-300 font-normal">
                            Round {currentRound.roundNumber} / {fullMatchHistory.length}
                        </span>
                    </h2>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 bg-black/20 rounded-lg p-1 border border-white/10">
                            <button onClick={prevRound} disabled={selectedRoundIdx === 0} className="p-2 hover:bg-white/10 rounded disabled:opacity-30 text-white transition-colors" title="Previous Round">
                                <ChevronUp size={20} />
                            </button>
                            <span className="text-xs font-bold text-gray-400 uppercase px-2">Round</span>
                            <button onClick={nextRound} disabled={selectedRoundIdx === fullMatchHistory.length - 1} className="p-2 hover:bg-white/10 rounded disabled:opacity-30 text-white transition-colors" title="Next Round">
                                <ChevronDown size={20} />
                            </button>
                        </div>
                        <button onClick={onClose} className="bg-white/10 hover:bg-white/20 p-2 rounded-full text-white transition-colors">
                            <X size={24} />
                        </button>
                    </div>
                </div>

                {/* Content Layout (Middle) */}
                <div className="flex-1 flex overflow-hidden relative">

                    {/* Sidebar: Rounds List (Hidden on Mobile, Visible on Desktop) */}
                    <div className="w-64 bg-black/20 border-r border-white/10 overflow-y-auto hidden md:flex flex-col shrink-0">
                        {/* Sidebar content remains same, just ensuring correct scroll */}
                        <div className="p-3 grid gap-2">
                            {fullMatchHistory.map((round, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => { setSelectedRoundIdx(idx); setSelectedTrickIdx(0); setIsPlaying(false); }}
                                    className={`
                                         w-full text-left p-3 rounded-xl border transition-all relative
                                         ${idx === selectedRoundIdx
                                            ? 'bg-[var(--color-premium-gold)] border-[var(--color-premium-gold)] text-black shadow-lg shadow-amber-500/20'
                                            : 'bg-white/5 border-transparent text-gray-400 hover:bg-white/10'
                                        }
                                     `}
                                >
                                    <div className="flex justify-between items-center mb-1">
                                        <span className="font-bold text-sm">Round {round.roundNumber}</span>
                                        <span className="text-xs font-mono opacity-80">{round.bid?.type}</span>
                                    </div>
                                    <div className="flex justify-between text-xs opacity-70">
                                        <span>Us: {round.scores?.us?.result}</span>
                                        <span>Them: {round.scores?.them?.result}</span>
                                    </div>
                                    {idx === selectedRoundIdx && isPlaying && (
                                        <div className="absolute right-2 top-2 w-2 h-2 bg-red-500 rounded-full animate-ping" />
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Main Stage */}
                    <div className="flex-1 flex flex-col relative bg-[url('/assets/cloth_texture.jpg')] bg-cover bg-center overflow-hidden">
                        <div className="absolute inset-0 bg-green-900/40 backdrop-blur-[2px] z-0" />

                        {/* Top Overlay Info */}
                        <div className="relative z-10 p-4 w-full flex justify-center pointer-events-none">
                            <div className="bg-black/60 backdrop-blur rounded-full px-6 py-2 flex items-center gap-6 border border-white/10 shadow-xl">
                                <div className="flex flex-col items-center">
                                    <span className="text-[9px] uppercase text-gray-400 font-bold tracking-widest">Bid</span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-amber-400 font-black text-lg">{currentRound.bid?.type}</span>
                                        <span className="text-white/60 text-xs">by {getPlayerName(currentRound.bid?.bidder)}</span>
                                    </div>
                                </div>
                                <div className="w-px h-8 bg-white/20" />
                                <div className="flex flex-col items-center">
                                    <span className="text-[9px] uppercase text-gray-400 font-bold tracking-widest">Score</span>
                                    <div className="flex gap-3 text-base font-bold">
                                        <span className="text-blue-400">Us: {currentRound.scores?.us?.result}</span>
                                        <span className="text-red-400">Them: {currentRound.scores?.them?.result}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Tricks Center Stage */}
                        <div className="relative z-10 flex-1 flex items-center justify-center p-4 sm:p-8">
                            {!currentTrick ? (
                                <div className="text-white/50">No tricks data</div>
                            ) : (
                                <div className="grid grid-cols-3 gap-4 sm:gap-12 items-center transform scale-90 sm:scale-100 transition-transform">
                                    {/* Top Player */}
                                    <div className="col-start-2 flex justify-center transform -translate-y-4">
                                        {renderCardForPos(currentTrick, 'Top', players)}
                                    </div>

                                    {/* Left Player */}
                                    <div className="col-start-1 row-start-2 flex justify-end transform -translate-x-4">
                                        {renderCardForPos(currentTrick, 'Left', players)}
                                    </div>

                                    {/* Center: Trick Info - Modified to be less obtrusive */}
                                    <div className="col-start-2 row-start-2 flex flex-col items-center justify-center w-24 h-24 sm:w-32 sm:h-32 bg-black/40 rounded-full border border-white/10 backdrop-blur-md shadow-[0_0_30px_rgba(0,0,0,0.3)]">
                                        <div className="text-[8px] sm:text-[10px] text-gray-300 uppercase mb-1 tracking-widest">Winner</div>
                                        <div className="font-black text-lg sm:text-2xl text-[var(--color-premium-gold)] text-center px-1 leading-none mb-1">
                                            {getPlayerName(currentTrick.winner)}
                                        </div>
                                        <div className="text-xs font-mono text-green-400 bg-green-900/30 px-2 py-0.5 rounded flex items-center gap-1">
                                            <span className="text-[8px]">+</span>{currentTrick.points}
                                        </div>
                                    </div>

                                    {/* Right Player */}
                                    <div className="col-start-3 row-start-2 flex justify-start transform translate-x-4">
                                        {renderCardForPos(currentTrick, 'Right', players)}
                                    </div>

                                    {/* Bottom Player */}
                                    <div className="col-start-2 row-start-3 flex justify-center transform translate-y-4">
                                        {renderCardForPos(currentTrick, 'Bottom', players)}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Trick Counter (Subtle) */}
                        <div className="absolute bottom-4 right-4 z-10 text-white/20 font-black text-6xl select-none pointer-events-none">
                            {selectedTrickIdx + 1}
                        </div>
                    </div>
                </div>

                {/* Footer Controls (Fixed Bottom) */}
                <div className="bg-[#111] p-4 border-t border-white/10 shrink-0 relative z-50 flex items-center justify-between gap-4">

                    {/* Playback Controls */}
                    <div className="flex items-center gap-2 w-full md:w-auto justify-center md:justify-start">
                        <button
                            onClick={prevTrick}
                            disabled={selectedTrickIdx === 0}
                            className="w-12 h-12 flex items-center justify-center bg-white/5 hover:bg-white/10 rounded-full text-white disabled:opacity-30 transition-all active:scale-95"
                            title="Previous Trick"
                        >
                            <ChevronLeft size={24} />
                        </button>

                        <button
                            onClick={togglePlay}
                            className={`
                                w-14 h-14 flex items-center justify-center rounded-full text-black font-bold transition-all shadow-lg active:scale-95
                                ${isPlaying ? 'bg-red-500 hover:bg-red-400 shadow-red-500/30' : 'bg-[var(--color-premium-gold)] hover:bg-amber-400 shadow-amber-500/30'}
                            `}
                            title={isPlaying ? "Pause" : "Play"}
                        >
                            {isPlaying ? <PauseIcon /> : <Play size={24} fill="currentColor" />}
                        </button>

                        <button
                            onClick={nextTrick}
                            disabled={selectedTrickIdx >= tricks.length - 1}
                            className="w-12 h-12 flex items-center justify-center bg-white/5 hover:bg-white/10 rounded-full text-white disabled:opacity-30 transition-all active:scale-95"
                            title="Next Trick"
                        >
                            <ChevronRight size={24} />
                        </button>
                    </div>

                    {/* Scrub Bar (Timeline) - Hidden on small screens, shown on md+ */}
                    <div className="hidden md:flex flex-1 mx-8 flex-col gap-2">
                        <div className="flex justify-between text-xs text-gray-400 uppercase font-bold tracking-widest">
                            <span>Start</span>
                            <span>Trick {selectedTrickIdx + 1} of {tricks.length}</span>
                            <span>End</span>
                        </div>
                        <div className="relative h-2 bg-white/10 rounded-full overflow-hidden">
                            <div
                                className="absolute top-0 left-0 h-full bg-[var(--color-premium-gold)] transition-all duration-300 ease-out"
                                style={{ width: `${((selectedTrickIdx + 1) / tricks.length) * 100}%` }}
                            />
                            {/* Ticks */}
                            <div className="absolute inset-0 flex justify-between px-[1px]">
                                {tricks.map((_: any, i: number) => (
                                    <div key={i} className={`w-[1px] h-full ${i === 0 || i === tricks.length ? 'opacity-0' : 'bg-black/50'}`} />
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Round Nav (Secondary) */}
                    <div className="hidden md:flex items-center gap-3">
                        <button onClick={prevRound} disabled={selectedRoundIdx === 0} className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-bold text-gray-300 disabled:opacity-30 transition-colors">
                            Prev Round
                        </button>
                        <button onClick={nextRound} disabled={selectedRoundIdx === fullMatchHistory.length - 1} className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-bold text-gray-300 disabled:opacity-30 transition-colors">
                            Next Round
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );

    function renderCardForPos(trick: any, pos: string, players: any[]) {
        const idx = trick.playedBy.indexOf(pos);
        if (idx === -1) return <div className="w-12 h-16 opacity-0" />;
        const card = trick.cards[idx];
        const isWinner = trick.winner === pos;
        const pName = getPlayerName(pos);
        return <MiniCard card={card} playedBy={pName} isWinner={isWinner} />;
    }
};

const PauseIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <rect x="6" y="4" width="4" height="16" rx="1" />
        <rect x="14" y="4" width="4" height="16" rx="1" />
    </svg>
);

export default MatchReviewModal;
