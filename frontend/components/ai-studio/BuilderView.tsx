import React, { useState, useRef } from 'react';
import { RefreshCw, Save, Upload, Video, Camera, Wand2 } from 'lucide-react';
import { submitTrainingData, analyzeScreenshot, askStrategy, generateScenario } from '../../services/trainingService';
import ScenarioTable from '../ScenarioTable';
import ActionSelector from './ActionSelector';
import { GamePhase } from '../../types';

interface BuilderViewProps {
    scenarioState: any;
    setScenarioState: (state: any) => void;
    correctAction: string;
    setCorrectAction: (action: string) => void;
    reasoning: string;
    setReasoning: (reason: string) => void;
    currentImage: string | null;
    setCurrentImage: (img: string | null) => void;
    onSaveSuccess: () => void;
}

const PREDEFINED_REASONS = [
    "Winning the bid with strong cards",
    "Cutting opponent's communication",
    "Saving Ace/Ten for later",
    "Opening a new suit for partner",
    "Forcing opponent to play high",
    "Passing due to weak hand",
    "Signaling strength to partner",
    "Avoiding risk",
    "Other (Custom)"
];

const BuilderView: React.FC<BuilderViewProps> = ({
    scenarioState, setScenarioState,
    correctAction, setCorrectAction,
    reasoning, setReasoning,
    currentImage, setCurrentImage,
    onSaveSuccess
}) => {

    // Local State for Builder helpers
    const [analyzing, setAnalyzing] = useState(false);
    const [strategyResult, setStrategyResult] = useState<any>(null);
    const [scenarioText, setScenarioText] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [videoSrc, setVideoSrc] = useState<string | null>(null);
    const [videoFile, setVideoFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const videoRef = useRef<HTMLVideoElement>(null);

    const handleAutoDistribute = () => {
        const suits = ['S', 'H', 'D', 'C'];
        const ranks = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A'];

        // 1. Collect all used cards
        const used = new Set<string>();
        scenarioState.players.forEach((p: any) => p.hand.forEach((c: any) => used.add(`${c.rank}${c.suit}`)));
        if (scenarioState.floorCard) used.add(`${scenarioState.floorCard.rank}${scenarioState.floorCard.suit}`);
        if (scenarioState.playedCards) {
            Object.values(scenarioState.playedCards).forEach((c: any) => used.add(`${c.rank}${c.suit}`));
        }

        // 2. Generate remaining deck
        const deck: { rank: string, suit: string }[] = [];
        suits.forEach(s => {
            ranks.forEach(r => {
                if (!used.has(`${r}${s}`)) {
                    deck.push({ rank: r, suit: s });
                }
            });
        });

        // 3. Shuffle
        for (let i = deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [deck[i], deck[j]] = [deck[j], deck[i]];
        }

        // 4. Distribute
        const limit = scenarioState.phase === GamePhase.Bidding ? 5 : 8;
        const newPlayers = scenarioState.players.map((p: any) => ({ ...p, hand: [...p.hand] }));

        let cardIdx = 0;
        newPlayers.forEach((p: any) => {
            while (p.hand.length < limit && cardIdx < deck.length) {
                p.hand.push(deck[cardIdx++]);
            }
        });

        setScenarioState({ ...scenarioState, players: newPlayers });
    };

    const handleSaveScenario = async () => {
        if (!correctAction || !reasoning) {
            alert("Please define Correct Action and Reasoning");
            return;
        }

        const example = {
            contextHash: `scen-${Date.now()}`,
            gameState: JSON.stringify(scenarioState),
            badMove: "Simulation",
            correctMove: correctAction,
            reason: reasoning,
            imageFilename: currentImage || undefined
        };

        await submitTrainingData(example);
        alert("Scenario Saved!");
        onSaveSuccess();
    };

    const handleVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        const file = e.target.files[0];
        const url = URL.createObjectURL(file);
        setVideoSrc(url);
        setVideoFile(file);
    };

    const handleAnalyzeVideo = async () => {
        if (!videoFile) return;
        setLoading(true);
        try {
            const res = await analyzeScreenshot(videoFile);
            if (res.data) {
                const aiState = res.data;
                mergeState(aiState);
                if (res.imageFilename) setCurrentImage(res.imageFilename);
                alert("Video Analyzed & State Populated!");
                setVideoSrc(null);
            }
        } catch (error) {
            console.error(error);
            alert("Video Analysis Failed.");
        } finally {
            setLoading(false);
        }
    };

    const handleCaptureFrame = () => {
        if (!videoRef.current) return;
        const video = videoRef.current;
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        if (ctx) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob((blob) => {
                if (blob) {
                    const file = new File([blob], "video-capture.jpg", { type: "image/jpeg" });
                    const event = { target: { files: [file] } } as any;
                    handleImageUpload(event);
                    setVideoSrc(null);
                }
            }, 'image/jpeg');
        }
    };

    const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        const file = e.target.files[0];
        setLoading(true);
        try {
            const res = await analyzeScreenshot(file);
            if (res.data) {
                mergeState(res.data);
                if (res.imageFilename) setCurrentImage(res.imageFilename);
                alert("Scenario populated from screenshot!");
            }
        } catch (error) {
            console.error(error);
            alert("Failed to analyze screenshot.");
        } finally {
            setLoading(false);
        }
    };

    const mergeState = (aiState: any) => {
        setScenarioState((prev: any) => ({
            ...prev,
            players: aiState.players || prev.players,
            dealerIndex: aiState.dealerIndex ?? prev.dealerIndex,
            currentTurn: aiState.currentTurn ?? prev.currentTurn,
            phase: aiState.phase || prev.phase,
            floorCard: aiState.floorCard ?? prev.floorCard,
            playedCards: aiState.playedCards ?? prev.playedCards,
            bid: aiState.bid ?? prev.bid
        }));
    };

    const handleAskAI = async () => {
        setAnalyzing(true);
        setStrategyResult(null);
        try {
            const res = await askStrategy(scenarioState);
            if (res.recommendation) {
                setStrategyResult(res.recommendation);
            } else if (res.error) {
                alert(`AI Error: ${res.error}`);
            }
        } catch (e) {
            console.error(e);
            alert("Analysis failed.");
        } finally {
            setAnalyzing(false);
        }
    };

    const handleGenerateFromText = async () => {
        if (!scenarioText.trim()) return;
        setIsGenerating(true);
        try {
            const res = await generateScenario(scenarioText);
            if (res.data) {
                mergeState(res.data);
                alert("Scenario Generated from Text!");
                setScenarioText('');
            } else if (res.error) {
                alert("Error: " + res.error);
            }
        } catch (e) {
            console.error(e);
            alert("Generation failed");
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="flex flex-col lg:flex-row flex-1 gap-6 overflow-hidden overflow-y-auto lg:overflow-y-hidden">
            {/* Left Column: Controls */}
            <div className="w-full lg:w-[450px] shrink-0 bg-slate-800 rounded-xl p-4 overflow-y-auto border border-slate-700 flex flex-col gap-6 order-2 lg:order-1">

                {/* 1. Importers */}
                <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
                    <h3 className="text-sm font-bold text-slate-300 mb-3 uppercase tracking-wider">Import Scenario</h3>
                    <div className="grid grid-cols-2 gap-2 mb-4">
                        <label className="flex flex-col items-center justify-center p-3 bg-slate-800 rounded border border-slate-600 hover:bg-slate-700 cursor-pointer">
                            <Upload size={20} className="mb-1 text-blue-400" />
                            <span className="text-xs">Screenshot</span>
                            <input type="file" onChange={handleImageUpload} className="hidden" accept="image/*" />
                        </label>
                        <label className="flex flex-col items-center justify-center p-3 bg-slate-800 rounded border border-slate-600 hover:bg-slate-700 cursor-pointer">
                            <Video size={20} className="mb-1 text-purple-400" />
                            <span className="text-xs">Video</span>
                            <input type="file" onChange={handleVideoUpload} className="hidden" accept="video/*" />
                        </label>
                    </div>

                    <div className="relative">
                        <input
                            value={scenarioText}
                            onChange={e => setScenarioText(e.target.value)}
                            placeholder="Describe scenario (e.g. 'I have 3 aces...')"
                            className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm pr-10"
                        />
                        <button
                            onClick={handleGenerateFromText}
                            disabled={isGenerating}
                            className="absolute right-1 top-1 p-1.5 bg-indigo-600 rounded text-white hover:bg-indigo-500"
                        >
                            <Wand2 size={14} className={isGenerating ? "animate-spin" : ""} />
                        </button>
                    </div>
                </div>

                {/* 2. Scenario state controls */}
                <div className="flex gap-2">
                    <button onClick={handleAutoDistribute} className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm font-bold flex items-center justify-center gap-2">
                        <RefreshCw size={14} /> Auto-Fill Hands
                    </button>
                    <button onClick={handleAskAI} className="flex-1 py-2 bg-purple-600 hover:bg-purple-500 rounded text-sm font-bold flex items-center justify-center gap-2">
                        {analyzing ? 'Thinking...' : '🤔 Ask AI Strategy'}
                    </button>
                </div>

                {strategyResult && (
                    <div className="bg-purple-900/30 border border-purple-500/50 p-3 rounded text-sm text-purple-200">
                        <strong>AI Suggestion:</strong> {strategyResult}
                    </div>
                )}

                {/* 3. Expected Output */}
                <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700 flex-1">
                    <h3 className="text-sm font-bold text-slate-300 mb-3 uppercase tracking-wider border-b border-slate-700 pb-2">Define Correct Play</h3>

                    <div className="mb-4">
                        <label className="text-xs text-slate-400 mb-1 block">Correct Action</label>
                        <input
                            value={correctAction}
                            readOnly
                            className="w-full bg-slate-950 border border-slate-600 rounded p-2 font-mono text-green-400 mb-2"
                            placeholder="Select action from board..."
                        />
                        <ActionSelector
                            phase={scenarioState.phase}
                            hand={scenarioState.players[0].hand}
                            currentSelection={correctAction}
                            onSelect={setCorrectAction}
                        />
                    </div>

                    <div className="mb-4">
                        <label className="text-xs text-slate-400 mb-1 block">Reasoning</label>
                        <select
                            onChange={e => setReasoning(e.target.value)}
                            className="w-full bg-slate-800 border border-slate-600 rounded p-2 mb-2 text-sm"
                        >
                            <option value="">Select a reason...</option>
                            {PREDEFINED_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
                        </select>
                        <textarea
                            value={reasoning}
                            onChange={e => setReasoning(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-600 rounded p-2 text-sm h-20"
                            placeholder="Detailed explanation..."
                        />
                    </div>

                    <button
                        onClick={handleSaveScenario}
                        className="w-full py-3 bg-green-600 hover:bg-green-500 text-white rounded font-bold shadow-lg flex items-center justify-center gap-2"
                    >
                        <Save size={18} /> Save Scenario
                    </button>
                </div>
            </div>

            {/* Right Column: Board Visualizer */}
            <div className="flex-1 bg-black/50 rounded-xl border border-slate-700 p-4 flex items-center justify-center overflow-auto relative order-1 lg:order-2">
                <ScenarioTable
                    scenarioState={scenarioState}
                    onUpdateState={(newState) => setScenarioState(newState)}
                />
                {currentImage && (
                    <div className="absolute top-4 right-4 w-32 border border-white/20 rounded shadow-xl">
                        <img src={currentImage.startsWith('http') ? currentImage : `http://127.0.0.1:3005/uploads/${currentImage}`} alt="Reference" className="w-full rounded" />
                    </div>
                )}
            </div>

            {/* Video Overlay */}
            {videoSrc && (
                <div className="fixed inset-0 bg-black/90 z-50 flex flex-col items-center justify-center p-4">
                    <div className="w-full max-w-4xl bg-slate-900 rounded-xl overflow-hidden border border-slate-700">
                        <div className="p-4 flex justify-between items-center bg-slate-800">
                            <h3 className="text-white font-bold">Video Analysis</h3>
                            <button onClick={() => setVideoSrc(null)}><X size={24} /></button>
                        </div>
                        <div className="relative bg-black flex justify-center">
                            <video
                                ref={videoRef}
                                src={videoSrc}
                                controls
                                className="max-h-[60vh]"
                            />
                        </div>
                        <div className="p-6 flex justify-center gap-4 bg-slate-800">
                            <button onClick={handleAnalyzeVideo} className="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded font-bold flex items-center gap-2">
                                <Video size={20} /> Analyze Full Video (Slow)
                            </button>
                            <button onClick={handleCaptureFrame} className="px-6 py-3 bg-green-600 hover:bg-green-500 rounded font-bold flex items-center gap-2">
                                <Camera size={20} /> Capture Current Frame
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default BuilderView;
