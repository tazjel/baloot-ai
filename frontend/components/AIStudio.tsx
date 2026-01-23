import React, { useState, useEffect } from 'react';
import { ArrowLeft, Layers, List, Brain, GraduationCap, Wand2 } from 'lucide-react';
import { getTrainingData } from '../services/trainingService';
import { GamePhase } from '../types';

// Sub-Components
import ReportsListView from './ai-studio/ReportsListView';
import BuilderView from './ai-studio/BuilderView';
import BiddingLabView from './ai-studio/BiddingLabView';
import TrainingView from './ai-studio/TrainingView';
import BrainMemoryView from './ai-studio/BrainMemoryView';

interface AIStudioProps {
    onBack: () => void;
}

const AIStudio: React.FC<AIStudioProps> = ({ onBack }) => {
    const [viewMode, setViewMode] = useState<'LIST' | 'BUILDER' | 'TRAINING' | 'BIDDING' | 'BRAIN'>('LIST');

    // --- LIST MODE STATE ---
    const [examples, setExamples] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    // --- SHARED BUILDER/TRAINING STATE ---
    // Lifted up so switching tabs doesn't destroy work in progress immediately,
    // though TrainingView mostly manages its own puzzle state.
    const [scenarioState, setScenarioState] = useState<any>({
        players: [
            { name: 'Me', position: 'Bottom', hand: [] },
            { name: 'Right', position: 'Right', hand: [] },
            { name: 'Partner', position: 'Top', hand: [] },
            { name: 'Left', position: 'Left', hand: [] },
        ],
        phase: GamePhase.Bidding,
        dealerIndex: 0,
        currentTurn: 0,
        bid: { type: 'SUN', suit: null },
        floorCard: null,
        playedCards: {},
        playerBids: {}
    });

    const [correctAction, setCorrectAction] = useState('');
    const [reasoning, setReasoning] = useState('');
    const [currentImage, setCurrentImage] = useState<string | null>(null);

    useEffect(() => {
        if (viewMode === 'LIST') loadData();
    }, [viewMode]);

    const loadData = async () => {
        setLoading(true);
        const res = await getTrainingData();
        if (res.data) {
            setExamples(res.data);
        }
        setLoading(false);
    };

    const handleDuplicate = (example: any) => {
        try {
            const loadedState = JSON.parse(example.gameState);
            setScenarioState(loadedState);
            setCorrectAction(example.correctMove || '');
            setReasoning(example.reason || '');
            setViewMode('BUILDER');
        } catch (e) {
            console.error("Failed to load scenario", e);
            alert("Error loading scenario data");
        }
    };


    return (
        <div className="flex flex-col h-full w-full bg-slate-900 text-white font-tajawal p-6 overflow-hidden">

            {/* Header */}
            <div className="flex items-center justify-between mb-6 shrink-0">
                <div className="flex items-center gap-4">
                    <button onClick={onBack} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700">
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-yellow-500 to-amber-600 bg-clip-text text-transparent">
                            استوديو الذكاء الاصطناعي
                        </h1>
                        <p className="text-slate-400">تدريب وتصحيح قرارات البوت</p>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex bg-slate-800 p-1 rounded-lg gap-1 overflow-x-auto">
                    <button onClick={() => setViewMode('LIST')} className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all whitespace-nowrap ${viewMode === 'LIST' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-white'}`}>
                        <List size={16} /> Reports
                    </button>
                    <button onClick={() => setViewMode('BUILDER')} className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all whitespace-nowrap ${viewMode === 'BUILDER' ? 'bg-yellow-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}>
                        <Layers size={16} /> Builder
                    </button>
                    <button onClick={() => setViewMode('TRAINING')} className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all whitespace-nowrap ${viewMode === 'TRAINING' ? 'bg-green-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}>
                        <GraduationCap size={16} /> Training
                    </button>
                    <button onClick={() => setViewMode('BIDDING')} className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all whitespace-nowrap ${viewMode === 'BIDDING' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}>
                        <Wand2 size={16} /> Bidding 🧐
                    </button>
                    <button onClick={() => setViewMode('BRAIN')} className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all whitespace-nowrap ${viewMode === 'BRAIN' ? 'bg-indigo-600 text-white shadow ring-1 ring-indigo-400' : 'text-slate-400 hover:text-white'}`}>
                        <Brain size={16} /> Brain Memory
                    </button>
                </div>
            </div>

            {/* CONTENT AREA */}
            {viewMode === 'LIST' && (
                <ReportsListView
                    examples={examples}
                    loading={loading}
                    onLoadData={loadData}
                    onDuplicate={handleDuplicate}
                />
            )}

            {viewMode === 'BUILDER' && (
                <BuilderView
                    scenarioState={scenarioState}
                    setScenarioState={setScenarioState}
                    correctAction={correctAction}
                    setCorrectAction={setCorrectAction}
                    reasoning={reasoning}
                    setReasoning={setReasoning}
                    currentImage={currentImage}
                    setCurrentImage={setCurrentImage}
                    onSaveSuccess={() => setViewMode('LIST')}
                />
            )}

            {viewMode === 'TRAINING' && (
                <TrainingView
                    scenarioState={scenarioState}
                    setScenarioState={setScenarioState}
                />
            )}

            {viewMode === 'BIDDING' && (
                <BiddingLabView />
            )}

            {viewMode === 'BRAIN' && (
                <BrainMemoryView
                    onBack={() => setViewMode('LIST')}
                />
            )}

        </div>
    );
};

export default AIStudio;
