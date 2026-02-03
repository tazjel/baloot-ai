
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Trophy, ArrowRight, BrainCircuit, AlertCircle, ArrowLeft } from 'lucide-react';
// import { Button } from '@/components/ui/button'; 
import { API_BASE_URL } from '../config';

interface PuzzleSummary {
    id: string;
    difficulty: string;
    description: string;
    context_hash: string;
}

interface PuzzleListProps {
    onSelectPuzzle: (id: string) => void;
    onBack: () => void;
}

const PuzzleList: React.FC<PuzzleListProps> = ({ onSelectPuzzle, onBack }) => {
    const [puzzles, setPuzzles] = useState<PuzzleSummary[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_BASE_URL}/puzzles`)
            .then(res => res.json())
            .then(data => {
                if (data.puzzles) setPuzzles(data.puzzles);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch puzzles", err);
                setLoading(false);
            });
    }, []);

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6 sm:p-12 font-sans">
            <header className="max-w-4xl mx-auto mb-12 flex items-center justify-between">
                <div>
                    <button onClick={onBack} className="flex items-center gap-2 text-white/50 hover:text-white mb-4 transition-colors">
                        <ArrowLeft size={20} /> Back to Lobby
                    </button>
                    <h1 className="text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-amber-300 to-yellow-500 mb-2">
                        AI Classroom
                    </h1>
                    <p className="text-white/60">Test your Baloot logic against the AI's "Golden Puzzles".</p>
                </div>
                <div className="bg-white/10 p-3 rounded-full">
                    <BrainCircuit size={32} className="text-amber-400" />
                </div>
            </header>

            <main className="max-w-4xl mx-auto">
                {loading ? (
                    <div className="text-center py-20 text-white/50 animate-pulse">Loading Puzzles...</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {puzzles.length === 0 ? (
                            <div className="col-span-2 text-center py-12 bg-white/5 rounded-2xl border border-dashed border-white/10">
                                <AlertCircle className="mx-auto mb-4 text-white/40" />
                                <p>No puzzles generated yet.</p>
                                <p className="text-sm text-white/40 mt-1">Run the Scout to find mistakes!</p>
                            </div>
                        ) : (
                            puzzles.map((puzzle, idx) => (
                                <motion.div
                                    key={puzzle.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.1 }}
                                    className="group relative overflow-hidden bg-white/5 hover:bg-white/10 border border-white/10 hover:border-amber-500/50 rounded-2xl p-6 transition-all duration-300 shadow-lg hover:shadow-amber-500/10"
                                >
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="bg-amber-500/20 text-amber-300 text-xs font-bold px-2 py-1 rounded-md border border-amber-500/30 uppercase tracking-wider">
                                            {puzzle.difficulty}
                                        </div>
                                        <Trophy size={20} className="text-white/20 group-hover:text-amber-400 transition-colors" />
                                    </div>

                                    <h3 className="text-xl font-bold mb-2">Puzzle #{idx + 1}</h3>
                                    <p className="text-sm text-white/60 mb-6 line-clamp-2 h-10">
                                        {puzzle.description}
                                    </p>

                                    <button
                                        onClick={() => onSelectPuzzle(puzzle.id)}
                                        className="inline-flex items-center gap-2 text-amber-400 font-bold group-hover:gap-3 transition-all cursor-pointer"
                                    >
                                        Solve Now <ArrowRight size={16} />
                                    </button>
                                </motion.div>
                            ))
                        )}
                    </div>
                )}
            </main>
        </div>
    );
};

export default PuzzleList;
