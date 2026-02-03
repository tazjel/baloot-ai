import React, { useState } from 'react';
import { Trophy, GraduationCap, Play, CheckCircle, X } from 'lucide-react';
import { getTrainingData } from '../../services/trainingService';
import ScenarioTable from '../ScenarioTable';
import ActionSelector from './ActionSelector';

interface TrainingViewProps {
    scenarioState: any;
    setScenarioState: (state: any) => void;
}

const TrainingView: React.FC<TrainingViewProps> = ({ scenarioState, setScenarioState }) => {

    const [trainingPuzzle, setTrainingPuzzle] = useState<any>(null);
    const [puzzleResult, setPuzzleResult] = useState<'PENDING' | 'CORRECT' | 'INCORRECT'>('PENDING');
    const [puzzleScore, setPuzzleScore] = useState(0);
    const [loading, setLoading] = useState(false);

    const startTraining = async () => {
        setLoading(true);
        const res = await getTrainingData();
        if (res.data && res.data.length > 0) {
            const valid = res.data.filter((e: any) => e.correct_move_json && e.game_state_json);
            if (valid.length > 0) {
                pickRandomPuzzle(valid);
            } else {
                alert("No valid puzzles found. Create some in Builder first!");
            }
        } else {
            alert("No training data found. Please go to Scenario Builder and save some scenarios first!");
        }
        setLoading(false);
    };

    const pickRandomPuzzle = (pool: any[]) => {
        const random = pool[Math.floor(Math.random() * pool.length)];
        try {
            const state = JSON.parse(random.game_state_json);
            setTrainingPuzzle({
                ...random,
                parsedState: state,
                parsedAnswer: JSON.parse(random.correct_move_json)
            });
            setScenarioState(state);
            setPuzzleResult('PENDING');
        } catch (e) {
            console.error("Bad puzzle data", e);
            pickRandomPuzzle(pool);
        }
    };

    const submitPuzzleAnswer = (actionJson: string) => {
        if (puzzleResult !== 'PENDING') return;

        const answer = JSON.parse(actionJson);
        const correct = trainingPuzzle.parsedAnswer;

        let isCorrect = false;
        if (answer.action === correct.action) {
            if (answer.action === 'PLAY_CARD' || answer.action === 'PLAY') {
                const c1 = answer.card || answer;
                const c2 = correct.card || correct;
                if (c1.rank === c2.rank && c1.suit === c2.suit) isCorrect = true;
            } else if (answer.action === 'HOKUM') {
                if (answer.suit === correct.suit) isCorrect = true;
            } else {
                isCorrect = true;
            }
        }

        if (isCorrect) {
            setPuzzleResult('CORRECT');
            setPuzzleScore(s => s + 10);
        } else {
            setPuzzleResult('INCORRECT');
            setPuzzleScore(s => Math.max(0, s - 5));
        }
    };

    return (
        <div className="flex flex-col lg:flex-row flex-1 gap-6 overflow-hidden overflow-y-auto lg:overflow-y-hidden">
            {/* Left: Score & Controls */}
            <div className="w-full lg:w-1/4 shrink-0 bg-slate-800 rounded-xl p-4 overflow-y-auto border border-slate-700 flex flex-col gap-6 order-2 lg:order-1">

                <div className="bg-slate-900 rounded-lg p-4 text-center borderBorder-slate-700 shadow-inner">
                    <div className="text-sm text-slate-400 mb-1 flex items-center justify-center gap-2"><Trophy size={14} /> Session Score</div>
                    <div className="text-4xl font-bold text-yellow-500">{puzzleScore}</div>
                </div>

                {!trainingPuzzle ? (
                    <div className="flex flex-col items-center justify-center flex-1 text-center py-10">
                        <GraduationCap size={48} className="text-green-500 mb-4 opacity-80" />
                        <h3 className="text-xl font-bold text-white mb-2">Ready to Train?</h3>
                        <p className="text-sm text-slate-400 mb-6">Solve verified scenarios to improve your Baloot skills.</p>
                        <button
                            onClick={startTraining}
                            disabled={loading}
                            className="px-6 py-3 bg-green-600 hover:bg-green-500 text-white rounded-full font-bold flex items-center gap-2 transition-transform hover:scale-105"
                        >
                            <Play size={20} fill="currentColor" /> {loading ? "Loading..." : "Start Puzzles"}
                        </button>
                    </div>
                ) : (
                    <div className="flex flex-col gap-6 animate-in fade-in">
                        <div className="border border-green-500/30 rounded-lg p-3 bg-green-900/10">
                            <div className="flex justify-between text-xs text-green-400 uppercase font-bold mb-1">
                                <span>Goal</span>
                                <span>{scenarioState.mode === 'HOKUM' ? 'Hokum' : 'Sun'}</span>
                            </div>
                            <div className="text-lg text-white font-bold">
                                find the best move!
                            </div>
                        </div>

                        {/* Puzzle Area */}
                        <div>
                            <h3 className="text-sm text-slate-400 mb-3 border-b border-slate-700 pb-1">Your Hand (Select Action)</h3>
                            <div className={puzzleResult !== 'PENDING' ? 'pointer-events-none opacity-50' : ''}>
                                <ActionSelector
                                    phase={scenarioState.phase}
                                    hand={scenarioState.players[0].hand}
                                    currentSelection={null}
                                    onSelect={submitPuzzleAnswer}
                                />
                            </div>
                        </div>

                        {/* Result Overlay */}
                        {puzzleResult !== 'PENDING' && (
                            <div className={`p-4 rounded-xl border-2 animate-in zoom-in-95 duration-300 ${puzzleResult === 'CORRECT' ? 'bg-green-900/50 border-green-500' : 'bg-red-900/50 border-red-500'}`}>
                                <div className="flex items-center gap-3 mb-2">
                                    {puzzleResult === 'CORRECT' ? <CheckCircle className="text-green-400" size={32} /> : <X className="text-red-400" size={32} />}
                                    <div>
                                        <div className={`text-xl font-bold ${puzzleResult === 'CORRECT' ? 'text-green-300' : 'text-red-300'}`}>
                                            {puzzleResult === 'CORRECT' ? 'Excellent!' : 'Incorrect'}
                                        </div>
                                        <div className="text-xs text-white/70">
                                            {puzzleResult === 'CORRECT' ? 'You found the best move.' : 'That is not the optimal play.'}
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-black/30 p-3 rounded text-sm text-slate-200 mt-2">
                                    <span className="font-bold text-slate-400 block text-xs mb-1">WHY?</span>
                                    {trainingPuzzle.reason}
                                </div>

                                <button
                                    onClick={startTraining} // Fetch next
                                    className="w-full mt-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded font-bold"
                                >
                                    Next Puzzle →
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Right: Board */}
            <div className="flex-1 bg-black/50 rounded-xl border border-slate-700 p-4 flex items-center justify-center overflow-auto relative order-1 lg:order-2 min-h-[400px]">
                {trainingPuzzle ? (
                    <div className="w-full max-w-[800px] pointer-events-none scale-75 sm:scale-90 md:scale-100 origin-center">
                        <ScenarioTable
                            scenarioState={scenarioState}
                            onUpdateState={() => { }} // No-op
                        />
                    </div>
                ) : (
                    <div className="text-slate-600 flex flex-col items-center">
                        <GraduationCap size={64} className="mb-4 opacity-50" />
                        <p>Select a puzzle to start</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TrainingView;
