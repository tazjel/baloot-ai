
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Trophy, ArrowRight, GraduationCap, AlertCircle, ArrowLeft, BookOpen, Clock } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface PuzzleSummary {
    id: string;
    title: string;
    description: string;
    difficulty: 'Beginner' | 'Intermediate' | 'Advanced';
    tags: string[];
}

interface AcademyPageProps {
    onSelectPuzzle: (id: string) => void;
    onBack: () => void;
}

const AcademyPage: React.FC<AcademyPageProps> = ({ onSelectPuzzle, onBack }) => {
    const [puzzles, setPuzzles] = useState<PuzzleSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>('All');

    useEffect(() => {
        fetch(`${API_BASE_URL}/academy/puzzles`)
            .then(res => res.json())
            .then(data => {
                if (data.puzzles) setPuzzles(data.puzzles);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch academy puzzles", err);
                setLoading(false);
            });
    }, []);

    const filteredPuzzles = filter === 'All' 
        ? puzzles 
        : puzzles.filter(p => p.difficulty === filter);

    return (
        <div className="min-h-screen bg-slate-950 text-white p-6 sm:p-12 font-tajawal" dir="rtl">
            <header className="max-w-6xl mx-auto mb-12 flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="text-right">
                    <button onClick={onBack} className="flex items-center gap-2 text-white/50 hover:text-white mb-4 transition-colors">
                        <ArrowRight size={20} className="rotate-180" /> Back to Lobby
                    </button>
                    <h1 className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-l from-amber-300 to-yellow-600 mb-2">
                         أكاديمية البلوت
                    </h1>
                    <p className="text-slate-400 text-lg">The Academy: Master the art of Baloot with tailored scenarios.</p>
                </div>
                <div className="bg-amber-500/10 p-6 rounded-full border border-amber-500/20 shadow-[0_0_50px_rgba(245,158,11,0.2)]">
                    <GraduationCap size={64} className="text-amber-400" />
                </div>
            </header>

            <main className="max-w-6xl mx-auto">
                {/* Filters */}
                <div className="flex gap-4 mb-8 overflow-x-auto pb-2">
                    {['All', 'Beginner', 'Intermediate', 'Advanced'].map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-6 py-2 rounded-full font-bold transition-all whitespace-nowrap ${
                                filter === f 
                                ? 'bg-amber-500 text-black shadow-lg shadow-amber-500/20' 
                                : 'bg-white/5 hover:bg-white/10 text-slate-400'
                            }`}
                        >
                            {f === 'All' ? 'الكل' : f}
                        </button>
                    ))}
                </div>

                {loading ? (
                    <div className="text-center py-20 text-slate-500 animate-pulse">Checking Curriculum...</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredPuzzles.length === 0 ? (
                            <div className="col-span-full text-center py-20 bg-white/5 rounded-3xl border border-dashed border-white/10">
                                <AlertCircle className="mx-auto mb-4 text-slate-500" size={48} />
                                <p className="text-slate-400 text-xl">No puzzles found in this category.</p>
                            </div>
                        ) : (
                            filteredPuzzles.map((puzzle, idx) => (
                                <motion.div
                                    key={puzzle.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    onClick={() => onSelectPuzzle(puzzle.id)}
                                    className="group relative overflow-hidden bg-white/5 hover:bg-white/10 border border-white/5 hover:border-amber-500/50 rounded-2xl p-6 transition-all duration-300 cursor-pointer hover:-translate-y-1 shadow-xl"
                                >
                                    {/* Difficulty Badge */}
                                    <div className="absolute top-4 left-4">
                                        <span className={`text-xs font-bold px-3 py-1 rounded-full border ${
                                            puzzle.difficulty === 'Beginner' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                                            puzzle.difficulty === 'Intermediate' ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' :
                                            'bg-red-500/20 text-red-400 border-red-500/30'
                                        }`}>
                                            {puzzle.difficulty}
                                        </span>
                                    </div>

                                    <div className="mb-4 mt-2">
                                        <h3 className="text-2xl font-bold mb-2 group-hover:text-amber-400 transition-colors">{puzzle.title}</h3>
                                        <p className="text-slate-400 text-sm h-10 line-clamp-2">{puzzle.description}</p>
                                    </div>

                                    {/* Tags */}
                                    <div className="flex flex-wrap gap-2 mb-6">
                                        {puzzle.tags.map(tag => (
                                            <span key={tag} className="text-[10px] bg-slate-800 text-slate-300 px-2 py-1 rounded">#{tag}</span>
                                        ))}
                                    </div>

                                    <div className="flex justify-between items-center text-sm text-slate-500 font-mono group-hover:text-amber-500 transition-colors">
                                        <span className="flex items-center gap-2"><BookOpen size={14} /> Lesson {idx + 1}</span>
                                        <span className="flex items-center gap-1">Start <ArrowLeft size={14} /></span>
                                    </div>
                                </motion.div>
                            ))
                        )}
                    </div>
                )}
            </main>
        </div>
    );
};

export default AcademyPage;
