import React, { useState, useEffect, useMemo } from 'react';
import { CardModel, Suit, Rank } from '../types';
import CardVector from '../components/CardVector';
// getAssetPath removed as unused

// Reuse existing UI components where possible, or simplified versions
// We need a visual representation of 4 players + table
// For MVP, we'll build a custom simple view to ensure Open Hand works easily

interface ReplayPageProps {
    gameId: string;
    onBack: () => void;
    onFork: (newGameId: string) => void;
    onLoadReplay?: (id: string) => void;
}

const ReplayPage: React.FC<ReplayPageProps> = ({ gameId, onBack, onFork, onLoadReplay }) => {
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [roundIdx, setRoundIdx] = useState(0);
    const [playbackStep, setPlaybackStep] = useState(0); // 0 to 40 (8 tricks * 5 phases)
    const [isPlaying, setIsPlaying] = useState(false);

    // Saved Replays List
    const [savedReplays, setSavedReplays] = useState<any[]>([]);
    const [showSidebar, setShowSidebar] = useState(false); // Default hidden for full immersion

    // Fetch Saved List
    // Fetch Saved List
    const fetchSavedGames = () => {
        setLoading(true);
        const cacheBuster = Date.now();
        fetch(`/react-py4web/replay/list?t=${cacheBuster}`)
            .then(async res => {
                const text = await res.text();
                try {
                    const data = JSON.parse(text);
                    if (data.matches) setSavedReplays(data.matches);
                    else if (data.error) setError("Server: " + data.error);
                } catch (e) {
                    console.error("JSON Parse Error", e);
                    setError("Invalid JSON: " + text.substring(0, 50) + "...");
                }
            })
            .catch(e => setError("Network: " + e.message))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchSavedGames();
    }, []);

    // Fetch History
    useEffect(() => {
        if (!gameId) return;

        fetch(`/match_history/${gameId}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                if (data.history) {
                    setHistory(data.history);
                    // Default to start of first round, first step
                    if (data.history.length > 0) {
                        setRoundIdx(0);
                        setPlaybackStep(0);
                    }
                }
                setLoading(false);
            })
            .catch(e => {
                setError(e.message);
                setLoading(false);
            });
    }, [gameId]);

    // Auto-Play Effect
    useEffect(() => {
        let interval: any;
        if (isPlaying) {
            interval = setInterval(() => {
                setPlaybackStep(prev => {
                    if (prev >= 40) { // Max 8 tricks * 5 steps/trick = 40
                        setIsPlaying(false);
                        return prev;
                    }
                    return prev + 1;
                });
            }, 1000); // 1 second per action
        }
        return () => clearInterval(interval);
    }, [isPlaying]);

    // Computed State for Current Frame (Step-Based)
    const currentFrame = useMemo(() => {
        try {
            if (!history[roundIdx]) return null;

            const roundParams = history[roundIdx];
            if (!roundParams) return { error: "Round data missing", hands: { Bottom: [], Top: [], Left: [], Right: [] }, tableCards: [], bid: { type: 'Unknown', suit: '', bidder: '' } };

            const initialHands = roundParams.initialHands;
            const tricks = roundParams.tricks;

            if (!initialHands || typeof initialHands !== 'object') {
                return { error: "No Initial Hands captured.", hands: { Bottom: [], Top: [], Left: [], Right: [] }, tableCards: [], bid: { type: 'Unknown', suit: '', bidder: '' } };
            }

            // 1. Restore Initial Hands
            const hands: Record<string, any[]> = {};
            Object.keys(initialHands).forEach(pos => {
                if (Array.isArray(initialHands[pos])) {
                    hands[pos] = [...initialHands[pos]];
                } else {
                    hands[pos] = [];
                }
            });

            const activeTableCards: { card: CardModel, player: string }[] = [];

            // 2. Play through history based on 'playbackStep'
            // Step 0 = Start of Trick 1
            // Step 1 = Card 1 Played
            // ...
            // Step 4 = Card 4 Played (Full Table)
            // Step 5 = Clear Table (End of Trick 1) / Start of Trick 2

            const currentTrickIndex = Math.floor(playbackStep / 5);
            const stepInTrick = playbackStep % 5; // 0..4

            if (Array.isArray(tricks)) {
                // Replay COMPLETED tricks (removed from hands, cleared from table)
                for (let t = 0; t < currentTrickIndex; t++) {
                    if (!tricks[t]) continue;
                    const trick = tricks[t];

                    // Normalize Moves (Backend sends 'cards' + 'playedBy', Frontend needs pairs)
                    const moves = trick.moves || (trick.cards && trick.playedBy ? trick.cards.map((card: any, idx: number) => ({
                        card: card,
                        player: trick.playedBy[idx]
                    })) : []);

                    if (Array.isArray(moves)) {
                        moves.forEach((move: any) => {
                            if (hands[move.player]) {
                                hands[move.player] = hands[move.player].filter((c: any) =>
                                    !(c.suit === move.card.suit && c.rank === move.card.rank)
                                );
                            }
                        });
                    }
                }

                // Replay CURRENT trick (remove from hands, ADD to table)
                if (tricks[currentTrickIndex]) {
                    const currentTrick = tricks[currentTrickIndex];

                    // Normalize Moves
                    const moves = currentTrick.moves || (currentTrick.cards && currentTrick.playedBy ? currentTrick.cards.map((card: any, idx: number) => ({
                        card: card,
                        player: currentTrick.playedBy[idx]
                    })) : []);

                    // Only show cards up to current step
                    // 0 = no cards (start of trick)
                    // 1 = 1 card played
                    const cardsToShow = (stepInTrick === 4) ? 4 : stepInTrick;

                    if (Array.isArray(moves)) {
                        for (let i = 0; i < cardsToShow; i++) {
                            const move = moves[i];
                            if (move && move.card) {
                                // Remove from hand
                                if (hands[move.player]) {
                                    hands[move.player] = hands[move.player].filter((c: any) =>
                                        !(c.suit === move.card.suit && c.rank === move.card.rank)
                                    );
                                }
                                // Add to table
                                activeTableCards.push({ card: move.card, player: move.player });
                            }
                        }
                    }
                }
            }

            return {
                hands,
                tableCards: activeTableCards,
                bid: roundParams.bid || { type: 'Unknown', suit: '', bidder: '' },
                error: null
            };
        } catch (e: any) {
            console.error("Replay Frame Calc Error", e);
            return {
                hands: { Bottom: [], Top: [], Left: [], Right: [] }, // Empty hands to prevent render crash
                tableCards: [],
                bid: { type: 'Error', suit: '', bidder: '' },
                error: `Playback Error: ${e.message}`
            };
        }

    }, [history, roundIdx, playbackStep]);

    const handleFork = async () => {
        // Calculate trick/round from step
        const trickIdx = Math.floor(playbackStep / 5);
        try {
            const res = await fetch('/replay/fork', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    gameId,
                    roundNum: roundIdx + 1,
                    trickIndex: trickIdx
                })
            });
            const data = await res.json();
            if (data.success) onFork(data.newGameId);
            else alert("Fork Failed: " + data.error);
        } catch (e) {
            alert("Fork Error: " + e);
        }
    };

    if (loading && !savedReplays.length) return <div className="text-white p-10">Loading Replay...</div>;

    const isReady = currentFrame && !error;

    // Toggle Sidebar
    const toggleSidebar = () => setShowSidebar(!showSidebar);

    return (
        <div className="h-full w-full bg-black relative overflow-hidden font-tajawal text-white">

            {/* Sidebar Overlay (Drawer) */}
            <div
                className={`absolute top-0 right-0 h-full w-80 bg-slate-900/95 backdrop-blur-xl border-l border-white/10 shadow-2xl z-[60] transform transition-transform duration-300 ease-out ${showSidebar ? 'translate-x-0' : 'translate-x-full'}`}
            >
                <div className="p-4 border-b border-white/10 font-bold text-[#CDA434] flex justify-between items-center bg-black/20">
                    <span>Saved Games</span>
                    <div className="flex gap-2">
                        <button onClick={fetchSavedGames} className="text-xs bg-white/10 px-2 py-1 rounded hover:bg-white/20 transition-colors">↻</button>
                        <button onClick={() => setShowSidebar(false)} className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded hover:bg-red-500/30 transition-colors">✕</button>
                    </div>
                </div>
                <div className="h-[calc(100%-60px)] overflow-y-auto">
                    {savedReplays.map(match => (
                        <div
                            key={match.gameId}
                            onClick={() => { onLoadReplay && onLoadReplay(match.gameId); setShowSidebar(false); }}
                            className={`p-4 border-b border-white/5 cursor-pointer hover:bg-white/5 transition-all group ${match.gameId === gameId ? 'bg-[#CDA434]/10 border-l-4 border-[#CDA434]' : 'border-l-4 border-transparent'}`}
                        >
                            <div className="font-bold text-sm text-white group-hover:text-[#CDA434] transition-colors truncate">{match.gameId}</div>
                            <div className="text-xs text-white/40 mt-1">{new Date(match.timestamp).toLocaleString()}</div>
                            <div className="flex justify-between mt-2 text-xs font-mono">
                                <span className="text-green-400 bg-green-900/20 px-1 rounded">Us: {match.scoreUs}</span>
                                <span className="text-red-400 bg-red-900/20 px-1 rounded">Them: {match.scoreThem}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Sidebar Toggle Button (Only visible when sidebar is closed) */}
            {!showSidebar && (
                <button
                    onClick={toggleSidebar}
                    className="absolute top-4 right-4 z-[55] p-2 bg-slate-800/80 backdrop-blur rounded-lg border border-white/10 hover:bg-[#CDA434] hover:text-black transition-all shadow-lg group"
                    title="Load Saved Game"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                </button>
            )}

            {/* Main Content (Full Screen) */}
            <div className="absolute inset-0 flex flex-col p-0 bg-black">
                {!isReady ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-4 bg-[#1a1a1a]">
                        <div className="text-4xl">🎬</div>
                        <div className="text-xl font-light">{loading ? "Loading Replay..." : error ? `Error: ${error}` : "Select a replay to start"}</div>
                        {!gameId && (
                            <button onClick={toggleSidebar} className="mt-4 px-6 py-2 bg-[#CDA434] text-black font-bold rounded-full hover:bg-yellow-400 transition-transform hover:scale-105 shadow-lg">
                                Open Saved Games
                            </button>
                        )}
                    </div>
                ) : (
                    <>
                        {/* Header Overlay */}
                        <div className="absolute top-0 left-0 right-0 z-50 p-6 flex justify-between items-start pointer-events-none bg-gradient-to-b from-black/80 to-transparent h-32">
                            <div className="pointer-events-auto">
                                <h1 className="text-4xl font-black text-[#CDA434] drop-shadow-[0_2px_10px_rgba(205,164,52,0.5)] font-mono tracking-tighter">REPLAY<span className="text-white">STUDIO</span></h1>
                                <div className="text-[10px] text-white/60 uppercase tracking-[0.2em] mt-1 flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                                    Cinema Mode • {gameId.substring(0, 8)}
                                </div>
                            </div>
                            <div className="flex gap-3 pointer-events-auto pr-12"> {/* Padding Right to avoid overlap with Sidebar toggle */}
                                <button onClick={onBack} className="px-5 py-2 bg-white/5 backdrop-blur-md rounded-lg hover:bg-white/10 border border-white/10 text-xs font-bold uppercase tracking-widest transition-all">
                                    Exit
                                </button>
                                <button
                                    onClick={handleFork}
                                    className="px-6 py-2 bg-[#CDA434] hover:bg-yellow-400 text-black rounded-lg font-bold shadow-[0_0_20px_rgba(205,164,52,0.3)] animate-pulse text-xs uppercase tracking-widest transition-transform hover:scale-105"
                                >
                                    Fork Now ⚡
                                </button>
                            </div>
                        </div>

                        {/* Controls Overlay (Bottom) */}
                        <div className="absolute bottom-10 left-1/2 transform -translate-x-1/2 z-50 w-3/4 max-w-3xl pointer-events-auto">
                            <div className="bg-black/60 backdrop-blur-xl p-4 rounded-full border border-white/10 shadow-[0_10px_40px_rgba(0,0,0,0.5)] flex flex-col gap-2 relative overflow-hidden group hover:bg-black/80 transition-all">
                                {/* Progress Bar Background */}
                                <div className="absolute bottom-0 left-0 h-1 bg-[#CDA434]/20 w-full">
                                    <div className="h-full bg-[#CDA434]" style={{ width: `${(playbackStep / 40) * 100}%` }} />
                                </div>

                                <div className="flex items-center gap-6 px-4">
                                    {/* Play Button */}
                                    <button
                                        onClick={() => setIsPlaying(!isPlaying)}
                                        className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${isPlaying ? 'bg-white text-black hover:bg-gray-200' : 'bg-[#CDA434] text-black hover:bg-yellow-400'} shadow-lg scale-100 active:scale-95`}
                                    >
                                        {isPlaying ? <span className="text-2xl font-bold">⏸</span> : <span className="text-2xl font-bold ml-1">▶</span>}
                                    </button>

                                    {/* Timeline Slider */}
                                    <div className="flex-1 flex flex-col gap-1 py-2">
                                        <div className="flex justify-between text-[10px] text-white/50 uppercase font-bold tracking-widest px-1">
                                            <span>Start</span>
                                            <span className="text-[#CDA434]">Trick {Math.floor(playbackStep / 5) + 1} / 8</span>
                                        </div>
                                        <input
                                            type="range"
                                            min={0}
                                            max={40}
                                            value={playbackStep}
                                            onChange={(e) => { setPlaybackStep(Number(e.target.value)); setIsPlaying(false); }}
                                            className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-[#CDA434] hover:h-2 transition-all"
                                        />
                                    </div>

                                    {/* Round Selector (Mini) */}
                                    <div className="flex gap-1">
                                        {history.map((r, idx) => (
                                            <button
                                                key={idx}
                                                onClick={() => { setRoundIdx(idx); setPlaybackStep(0); setIsPlaying(false); }}
                                                className={`w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold transition-all ${roundIdx === idx ? 'bg-white text-black scale-110 shadow-lg' : 'bg-white/5 text-white/30 hover:bg-white/10'}`}
                                            >
                                                R{idx + 1}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Game View Container (Clean LTR Context) */}
                        <div className="flex-1 relative overflow-hidden" dir="ltr">

                            {/* Cinematic Background */}
                            <div className="absolute inset-0 bg-[#0a0a0a]">
                                <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_50%_50%,#2a1a10_0%,#000000_100%)]" />
                                <div className="absolute inset-0 bg-[url('/noise.png')] opacity-[0.03]" />
                            </div>

                            {/* 3D Scene */}
                            <div className="relative w-full h-full flex items-center justify-center perspective-container" style={{ perspective: '2000px' }}>

                                {/* Table Group */}
                                <div
                                    className="relative w-[1200px] h-[800px] transform-style-3d transition-transform duration-700 ease-out"
                                    style={{
                                        transform: 'rotateX(30deg) translateY(50px) scale(0.85)',
                                        transformStyle: 'preserve-3d'
                                    }}
                                >

                                    {/* Table Surface (Rug) */}
                                    <div className="absolute inset-0 rounded-[100px] shadow-[0_50px_100px_rgba(0,0,0,0.8)] overflow-hidden bg-[#5D2906] border-8 border-[#3E1C03]">
                                        {/* Texture */}
                                        <div className="absolute inset-0 opacity-80"
                                            style={{
                                                backgroundImage: `
                                                    radial-gradient(circle at center, transparent 30%, #3a1500 100%),
                                                    repeating-linear-gradient(45deg, rgba(205,164,52,0.05) 0, rgba(205,164,52,0.05) 1px, transparent 1px, transparent 10px),
                                                    repeating-linear-gradient(-45deg, rgba(205,164,52,0.05) 0, rgba(205,164,52,0.05) 1px, transparent 1px, transparent 10px)
                                                `
                                            }}
                                        />
                                        {/* Center Decal */}
                                        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] border-[2px] border-[#CDA434]/10 rounded-full flex items-center justify-center">
                                            <div className="w-[400px] h-[400px] border border-[#CDA434]/5 rounded-full" />
                                        </div>
                                    </div>

                                    {/* Game Elements Layer (Z-Lifted) */}
                                    <div className="absolute inset-0 z-10">

                                        {/* Minimalist Center Info (Floating) */}
                                        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-0 flex flex-col items-center gap-2" style={{ transform: 'translate(-50%, -50%) translateZ(20px)' }}>
                                            <div className="px-6 py-3 rounded-2xl bg-black/40 backdrop-blur-md border border-[#CDA434]/30 flex items-center gap-4 text-[#CDA434] shadow-xl">
                                                <div className="text-2xl font-bold">{currentFrame.bid.type}</div>
                                                <div className="text-3xl">{currentFrame.bid.suit === 'S' ? '♠' : currentFrame.bid.suit === 'H' ? '♥' : currentFrame.bid.suit === 'D' ? '♦' : '♣'}</div>
                                            </div>
                                            <div className="text-white/40 font-mono text-xs tracking-widest">{currentFrame.bid.bidder}</div>
                                        </div>

                                        {/* Hands & Avatars */}
                                        {Object.entries(currentFrame.hands).map(([pos, cards]) => {
                                            if (!Array.isArray(cards)) return null;
                                            const playerIndex = ['Bottom', 'Right', 'Top', 'Left'].indexOf(pos);
                                            // Exact coordinates for 4 players in 1200x800 space
                                            // Bottom (Us)
                                            // Top (Them)
                                            // Right (Them)
                                            // Left (Us)

                                            let containerStyle: React.CSSProperties = {};
                                            let avatarStyle: React.CSSProperties = {};

                                            // Adjusting to sit nicely AROUND the table
                                            switch (pos) {
                                                case 'Bottom':
                                                    containerStyle = { bottom: '-40px', left: '50%', transform: 'translateX(-50%) translateZ(50px)' };
                                                    avatarStyle = { bottom: '-120px', left: '50%', transform: 'translateX(-50%)' };
                                                    break;
                                                case 'Top':
                                                    containerStyle = { top: '-40px', left: '50%', transform: 'translateX(-50%) translateZ(20px)' }; // Far away
                                                    avatarStyle = { top: '-120px', left: '50%', transform: 'translateX(-50%)' };
                                                    break;
                                                case 'Left':
                                                    containerStyle = { left: '40px', top: '50%', transform: 'translateY(-50%) rotate(90deg) translateZ(30px)' };
                                                    avatarStyle = { left: '-100px', top: '50%', transform: 'translateY(-50%)' };
                                                    break;
                                                case 'Right':
                                                    containerStyle = { right: '40px', top: '50%', transform: 'translateY(-50%) rotate(-90deg) translateZ(30px)' };
                                                    avatarStyle = { right: '-100px', top: '50%', transform: 'translateY(-50%)' };
                                                    break;
                                            }

                                            return (
                                                <React.Fragment key={pos}>
                                                    {/* Avatar */}
                                                    <div className="absolute z-20" style={avatarStyle}>
                                                        <div className="w-16 h-16 rounded-full border-2 border-[#CDA434] bg-black shadow-[0_0_20px_rgba(205,164,52,0.4)] flex items-center justify-center">
                                                            <span className="text-[#CDA434] font-bold text-xl">{pos[0]}</span>
                                                        </div>
                                                    </div>

                                                    {/* Cards Container */}
                                                    <div className="absolute flex items-center justify-center" style={containerStyle}>
                                                        {(cards as any[]).map((c: any, i: number) => {
                                                            if (!c) return null;
                                                            const total = (cards as any[]).length;
                                                            const offset = i - (total - 1) / 2;
                                                            return (
                                                                <div key={i}
                                                                    className="absolute origin-bottom transition-all duration-300"
                                                                    style={{
                                                                        transform: `translateX(${offset * 30}px) rotate(${offset * 5}deg) translateY(${Math.abs(offset) * 5}px)`,
                                                                        width: '90px',
                                                                        height: '130px',
                                                                        zIndex: i,
                                                                        marginTop: pos === 'Bottom' ? '-60px' : '0'
                                                                    }}
                                                                >
                                                                    <CardVector card={c} className="w-full h-full shadow-lg rounded-xl border border-black/20 bg-white" isPlayable={false} />
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                </React.Fragment>
                                            );
                                        })}

                                        {/* Played Cards (Table Center) */}
                                        {Array.isArray(currentFrame.tableCards) && currentFrame.tableCards.map((played, i) => {
                                            const playOffset = 100;
                                            let style: React.CSSProperties = { position: 'absolute', top: '50%', left: '50%', zIndex: 100, transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)' };

                                            // Random slight rotation for realism
                                            const randomRot = (played.card.rank + played.card.suit).length % 10 - 5;

                                            switch (played.player) {
                                                case 'Bottom': style.transform = `translate(-50%, ${playOffset}px) rotate(${randomRot}deg) translateZ(60px)`; break;
                                                case 'Top': style.transform = `translate(-50%, -${playOffset + 120}px) rotate(${randomRot}deg) translateZ(60px)`; break;
                                                case 'Left': style.transform = `translate(-${playOffset + 80}px, -50%) rotate(90deg) translateZ(60px)`; break;
                                                case 'Right': style.transform = `translate(${playOffset}px, -50%) rotate(-90deg) translateZ(60px)`; break;
                                            }

                                            return (
                                                <div key={i} style={style} className="w-[90px] h-[130px] shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
                                                    <CardVector card={played.card} className="w-full h-full rounded-xl" isPlayable={false} />
                                                </div>
                                            );
                                        })}

                                    </div>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};
// getSuitIcon removed as unused
export default ReplayPage;
