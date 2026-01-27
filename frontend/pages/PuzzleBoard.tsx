import React, { useEffect, useState } from 'react';
import Table from '../components/Table';
import { API_BASE_URL } from '../config';
import { GameState, GamePhase } from '../types';
import { ArrowLeft, CheckCircle, XCircle, RotateCcw } from 'lucide-react';
import { soundManager } from '../services/SoundManager';
// import confetti from 'canvas-confetti'; // Optional: Add later for pizzazz

interface PuzzleBoardProps {
    id: string;
    onBack: () => void;
}

const PuzzleBoard: React.FC<PuzzleBoardProps> = ({ id, onBack }) => {

    const [puzzle, setPuzzle] = useState<any>(null);
    const [gameState, setGameState] = useState<GameState | null>(null);
    const [result, setResult] = useState<'PENDING' | 'CORRECT' | 'WRONG'>('PENDING');
    const [feedback, setFeedback] = useState<string>("");

    useEffect(() => {
        // Load Puzzle
        console.log("Fetching Puzzle ID:", id);
        fetch(`${API_BASE_URL}/puzzles/${id}`)
            .then(res => {
                console.log("Fetch Status:", res.status);
                return res.json();
            })
            .then(data => {
                console.log("Puzzle Data:", data);
                if (data.puzzle) {
                    setPuzzle(data.puzzle);
                    const initial = data.puzzle.game_state;

                    // Force state for UI
                    // Ensure the 'players' array has 'Me' as the active turn player if possible?
                    // The puzzle stores the state exactly as the bot saw it.
                    // If bot was index 2 (Top), we need to rotate the view so Index 2 is "Bottom" (Me).
                    // This requires a rotation helper similar to 'get_relative_index'.

                    // But 'Table.tsx' expects Player 0 to be 'Me'. 
                    // We need to adapt the gameState so clarity is maintained.

                    // ADAPTER: Find the puzzle player
                    const heroIndex = initial.currentTurnIndex;

                    // Rotate players so heroIndex is at 0
                    const players = initial.players || [];
                    const rotatedPlayers = [
                        ...players.slice(heroIndex),
                        ...players.slice(0, heroIndex)
                    ];

                    // Remap positions standard (Bottom, Right, Top, Left)
                    const heroPos = initial.players[heroIndex].position;
                    // Actually, let's just cheat and force the UI to treat hero as "Me"
                    // But Table component assumes players[0] is Me.

                    rotatedPlayers.forEach((p: any, idx) => {
                        if (idx === 0) p.name = "You (Bot)";
                        p.index = (heroIndex + idx) % 4; // Virtual index? No, keep original index for logic
                    });

                    // Update Table Cards to match visual rotation? 
                    // Table uses 'playedBy' position. 
                    // If we don't rotate positions, the avatars might be wrong place, but gameplay is correct.
                    // For now, pass state as is, but ensure players[0] corresponds to the hero?

                    // Better approach: Just set 'players' such that the first element IS the current turn player.
                    // And Table renders players[0] as Bottom.

                    setGameState({
                        ...initial,
                        players: rotatedPlayers,
                        // Ensure phase is Playing
                        phase: GamePhase.Playing
                    });
                }
            })
            .catch(err => {
                console.error("Puzzle Fetch Error:", err);
                setFeedback("Failed to load puzzle: " + err.message);
                setResult('WRONG');
            });
    }, [id]);

    const handleAction = (action: string, payload: any) => {
        if (result !== 'PENDING') return;

        // Check Solution
        const correct = puzzle.solution;

        let isCorrect = false;

        if (action === 'PLAY') {
            // Compare card index? 
            // BEWARE: The index in Payload corresponds to the ROTATED hand (0-7 for the user).
            // The Solution usually expects the original absolute index or card content.
            // The best way is to compare the *Card Content* (Rank/Suit).

            // Get played card
            const card = gameState?.players[0].hand[payload.cardIndex];
            // Get expected card (we might need to find it in hand if solution stores index)
            // Solution from BotTrainingData usually has 'cardIndex' relative to the original state.

            if (correct.action === 'PLAY') {
                // If solution has rank/suit, compare that
                if (correct.card) {
                    isCorrect = (card.rank === correct.card.rank && card.suit === correct.card.suit);
                } else {
                    // Fallback: If generic index, it's risky. 
                    // Assume for now 'correct' has been hydrated with reasoning or strict check.
                    // Let's assume ANY Valid Play that matches Expected Logic is OK?
                    // No, duplicate the strict index check from the validation script? 

                    // Hack for MVP: Check if card index matches exactly?
                    // Since we rotated players[0] to be the Hero, their hand is players[0].hand.
                    // The 'correct.cardIndex' is relative to that player's hand.
                    isCorrect = (payload.cardIndex === correct.cardIndex);
                }
            }
        }

        if (isCorrect) {
            setResult('CORRECT');
            setFeedback(`✅ Correct! ${correct.reasoning || "Perfect move."}`);
            soundManager.playProjectSound(); // Success sound
        } else {
            setResult('WRONG');
            setFeedback(`❌ Incorrect. Gemini suggests: ${correct.reasoning}`);
        }
    };

    // If loading and no error, show loading
    if (!gameState && result !== 'WRONG') return <div className="bg-slate-900 h-screen flex items-center justify-center text-white">Loading Puzzle...</div>;

    return (
        <div className="relative h-screen w-full overflow-hidden bg-slate-900">
            {/* Overlay UI */}
            {/* Top Right: Exit */}
            <div className="absolute top-4 right-4 z-50">
                <button onClick={onBack} className="bg-black/50 hover:bg-black/70 text-white px-4 py-2 rounded-full flex items-center gap-2 backdrop-blur-md transition-all border border-white/10">
                    <ArrowLeft size={16} /> Exit Class
                </button>
            </div>

            {/* Top Center: Title Badge */}
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-amber-500 text-black px-6 py-2 rounded-full font-bold shadow-lg flex items-center gap-2">
                🎓 Puzzle Mode
            </div>

            {/* Game Table (Only if we have state) */}
            {gameState && (
                <Table
                    gameState={gameState}
                    onPlayerAction={handleAction}
                />
            )}

            {/* Result Overlay */}
            {result !== 'PENDING' && (
                <div className="absolute inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-slate-900 border border-white/10 p-8 rounded-3xl max-w-lg w-full text-center shadow-2xl transform scale-100 animate-in zoom-in-95 duration-200">
                        {result === 'CORRECT' ? (
                            <CheckCircle size={64} className="mx-auto text-green-400 mb-4" />
                        ) : (
                            <XCircle size={64} className="mx-auto text-red-400 mb-4" />
                        )}

                        <h2 className={`text-3xl font-black mb-2 ${result === 'CORRECT' ? 'text-green-400' : 'text-red-400'}`}>
                            {result === 'CORRECT' ? 'Excellent!' : 'Try Again'}
                        </h2>

                        <div className="bg-white/5 p-4 rounded-xl text-white/90 text-left mb-6 font-mono text-sm leading-relaxed border-l-4 border-amber-500">
                            {feedback}
                        </div>

                        <div className="flex gap-3 justify-center">
                            <button onClick={() => window.location.reload()} className="px-6 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold flex items-center gap-2 transition-colors">
                                <RotateCcw size={18} /> Retry
                            </button>
                            {result === 'CORRECT' && (
                                <button onClick={onBack} className="px-6 py-3 bg-green-500 hover:bg-green-600 text-white rounded-xl font-bold shadow-lg shadow-green-500/20 transition-all">
                                    Finish
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PuzzleBoard;
