
import React, { useEffect, useState } from 'react';
import Table from '../Table';
import { API_BASE_URL } from '../../config';
import { GameState, GamePhase } from '../../types';
import { ArrowLeft, CheckCircle, XCircle, RotateCcw, Lightbulb } from 'lucide-react';
import { soundManager } from '../../services/SoundManager';

interface PuzzleArenaProps {
    id: string;
    onBack: () => void;
}

const PuzzleArena: React.FC<PuzzleArenaProps> = ({ id, onBack }) => {

    const [puzzle, setPuzzle] = useState<any>(null);
    const [gameState, setGameState] = useState<GameState | null>(null);
    const [result, setResult] = useState<'PENDING' | 'CORRECT' | 'WRONG'>('PENDING');
    const [feedback, setFeedback] = useState<string>("");
    const [moves, setMoves] = useState<string[]>([]); // Track user moves

    useEffect(() => {
        // Load Puzzle
        fetch(`${API_BASE_URL}/academy/puzzles/${id}`)
            .then(res => res.json())
            .then(data => {
                if (data.puzzle) {
                    setPuzzle(data.puzzle);
                    // Assume initial_state_json is ready for Table
                    const state = data.puzzle.initial_state_json;
                    if (state) {
                        setGameState({
                            ...state,
                            phase: GamePhase.Playing // Ensure active
                        });
                    }
                }
            })
            .catch(err => {
                console.error("Puzzle Fetch Error:", err);
                setFeedback("Failed to load puzzle.");
                setResult('WRONG');
            });
    }, [id]);

    const handleAction = async (action: string, payload: any) => {
        if (result !== 'PENDING') return;

        if (action === 'PLAY') {
            // 1. Update Local UI immediately (Optimistic)
            // We need to simulate the card moving to table?
            // The Table component usually waits for "Server Update" via props.
            // But here we are offline/static.
            // We must manually update 'gameState' to show the card played.

            if (!gameState) return;

            const playerIndex = 0; // Assume Hero is 0
            const card = gameState.players[playerIndex].hand[payload.cardIndex];
            const cardStr = `${card.rank}${card.suit}`;

            // Update moves history
            const newMoves = [...moves, cardStr];
            setMoves(newMoves);

            // Verify with Backend
            try {
                const res = await fetch(`${API_BASE_URL}/academy/verify`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        puzzleId: id,
                        moves: newMoves
                    })
                });
                const check = await res.json();

                if (check.success) {
                    // Mark Correct
                    setResult('CORRECT');
                    setFeedback(check.message);
                    soundManager.playProjectSound();
                } else if (!check.success && check.message.includes("Wrong")) {
                    // Mark Wrong (Only if explicitly wrong, not just 'incomplete')
                    // The current backend simplistic logic says "Wrong move" if mismatch.
                    // If partial match, it says "Good move..."

                    if (check.message.includes("Good move")) {
                        // Allow continue
                        // We need to update State to show card on table
                        // And maybe AI response?
                        // For MVP, single-step puzzles are safest.
                    } else {
                        setResult('WRONG');
                        setFeedback(check.message);
                        soundManager.playErrorSound(); // Fail sound?
                    }
                }

                // Update Visual State (Remove card from hand, add to table)
                const newHand = [...gameState.players[playerIndex].hand];
                newHand.splice(payload.cardIndex, 1);

                const newTable = [...gameState.tableCards, {
                    card: card,
                    playedBy: gameState.players[playerIndex].position
                }];

                setGameState({
                    ...gameState,
                    players: gameState.players.map((p, i) => i === 0 ? { ...p, hand: newHand } : p),
                    tableCards: newTable
                    // Turn logic? for multi-step we need to advance turn.
                });

            } catch (e) {
                console.error(e);
            }
        }
    };

    if (!gameState && result !== 'WRONG') return <div className="bg-slate-950 h-screen flex items-center justify-center text-white">Loading Scenario...</div>;

    return (
        <div className="relative h-screen w-full overflow-hidden bg-slate-950 font-tajawal">
            {/* Overlay UI */}
            <div className="absolute top-4 right-4 z-50">
                <button onClick={onBack} className="bg-black/50 hover:bg-black/70 text-white px-4 py-2 rounded-full flex items-center gap-2 backdrop-blur-md transition-all border border-white/10 uppercase tracking-widest text-xs font-bold">
                    <ArrowLeft size={16} /> Exit
                </button>
            </div>

            {/* Mission Objective */}
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-slate-900/90 text-white px-8 py-4 rounded-2xl border border-amber-500/20 shadow-2xl flex flex-col items-center gap-1 backdrop-blur-xl min-w-[300px]">
                <div className="text-amber-500 text-xs font-bold uppercase tracking-widest">Mission Objective</div>
                <div className="text-lg font-bold">{puzzle?.description || "Solve the puzzle"}</div>
            </div>

            {/* Hint Button */}
            <div className="absolute bottom-8 right-8 z-50">
                <button className="bg-indigo-600 hover:bg-indigo-500 text-white p-4 rounded-full shadow-lg shadow-indigo-600/30 transition-all">
                    <Lightbulb size={24} />
                </button>
            </div>

            {/* Game Table */}
            {gameState && (
                <Table
                    gameState={gameState}
                    onPlayerAction={handleAction}
                    // Disable other interactive elements
                    onChallenge={() => { }}
                    onAddBot={() => { }}
                    onDebugAction={() => { }}
                    isCuttingDeck={false}
                    onSawa={() => { }}
                    onEmoteClick={() => { }}
                />
            )}

            {/* Feedback Overlay */}
            {result !== 'PENDING' && (
                <div className="absolute inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
                    <div className="bg-slate-900 border border-white/10 p-8 rounded-3xl max-w-lg w-full text-center shadow-2xl relative overflow-hidden">
                        {/* Background Glow */}
                        <div className={`absolute inset-0 opacity-20 ${result === 'CORRECT' ? 'bg-green-500' : 'bg-red-500'}`} />

                        <div className="relative z-10">
                            {result === 'CORRECT' ? (
                                <CheckCircle size={80} className="mx-auto text-green-400 mb-6 drop-shadow-[0_0_15px_rgba(74,222,128,0.5)]" />
                            ) : (
                                <XCircle size={80} className="mx-auto text-red-400 mb-6 drop-shadow-[0_0_15px_rgba(248,113,113,0.5)]" />
                            )}

                            <h2 className="text-4xl font-black mb-2 text-white">
                                {result === 'CORRECT' ? 'Excellent!' : 'Incorrect'}
                            </h2>
                            <p className="text-white/60 mb-6">{result === 'CORRECT' ? "You found the optimal line." : "That's not quite right."}</p>

                            <div className="bg-black/30 p-4 rounded-xl text-white text-lg mb-8 border border-white/5">
                                {feedback}
                            </div>

                            <div className="flex gap-4 justify-center">
                                <button onClick={() => window.location.reload()} className="px-8 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold flex items-center gap-2 transition-colors">
                                    <RotateCcw size={20} /> Retry
                                </button>
                                {result === 'CORRECT' && (
                                    <button onClick={onBack} className="px-8 py-3 bg-amber-500 hover:bg-amber-400 text-black rounded-xl font-bold shadow-lg shadow-amber-500/20 transition-all flex items-center gap-2">
                                        Next Lesson <ArrowLeft size={20} />
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PuzzleArena;
