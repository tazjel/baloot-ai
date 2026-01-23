import React, { useState } from 'react';
import { Wand2, Save, List } from 'lucide-react';
import { submitTrainingData } from '../../services/trainingService';
import { GamePhase } from '../../types';

interface BiddingLabViewProps {
    // Self-contained
}

const BiddingLabView: React.FC<BiddingLabViewProps> = () => {
    // --- BIDDING GENERATOR STATE ---
    const [coreCards, setCoreCards] = useState<any[]>([]);
    const [biddingFloorCard, setBiddingFloorCard] = useState<any>(null); // {rank, suit}
    const [generatedScenarios, setGeneratedScenarios] = useState<any[]>([]);
    const [batchBid, setBatchBid] = useState<string>(''); // e.g., JSON string of action
    const [batchReason, setBatchReason] = useState<string>('');
    const [loading, setLoading] = useState(false);

    const suits = ['S', 'H', 'D', 'C'];
    const ranks = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A'];

    const toggleCoreCard = (card: { rank: string, suit: string }) => {
        const exists = coreCards.find(c => c.rank === card.rank && c.suit === card.suit);
        if (exists) {
            setCoreCards(coreCards.filter(c => c.rank !== card.rank || c.suit !== card.suit));
        } else {
            if (coreCards.length >= 5) return;
            setCoreCards([...coreCards, card]);
        }
    };

    const generateScenarios = () => {
        if (!biddingFloorCard) {
            alert("Please select a Floor Card.");
            return;
        }

        // 1. Identify available cards
        const used = new Set<string>();
        coreCards.forEach(c => used.add(`${c.rank}${c.suit}`));
        used.add(`${biddingFloorCard.rank}${biddingFloorCard.suit}`);

        const deck: { rank: string, suit: string }[] = [];
        suits.forEach(s => {
            ranks.forEach(r => {
                if (!used.has(`${r}${s}`)) {
                    deck.push({ rank: r, suit: s });
                }
            });
        });

        const needed = 5 - coreCards.length;
        if (needed < 0) {
            alert("Too many core cards!");
            return;
        }

        const newScenarios: any[] = [];

        const generate = (count: number) => {
            for (let i = 0; i < count; i++) {
                // Shuffle deck
                const currentDeck = [...deck];
                for (let j = currentDeck.length - 1; j > 0; j--) {
                    const k = Math.floor(Math.random() * (j + 1));
                    [currentDeck[j], currentDeck[k]] = [currentDeck[k], currentDeck[j]];
                }
                const fillers = currentDeck.slice(0, needed);
                const hand = [...coreCards, ...fillers];

                // Construct State
                const state = {
                    players: [
                        { name: 'Me', position: 'Bottom', hand: hand },
                        { name: 'Right', position: 'Right', hand: [] }, // Others empty
                        { name: 'Partner', position: 'Top', hand: [] },
                        { name: 'Left', position: 'Left', hand: [] },
                    ],
                    phase: GamePhase.Bidding,
                    dealerIndex: 3, // Left deals -> Me is first
                    currentTurn: 0,
                    bid: { type: 'PASS', suit: null }, // Initial state
                    floorCard: biddingFloorCard,
                    playedCards: {},
                    playerBids: {}
                };
                newScenarios.push({
                    id: Math.random().toString(36).substr(2, 9),
                    state: state
                });
            }
        }

        if (needed === 0) {
            generate(1);
        } else {
            generate(10);
        }

        setGeneratedScenarios(newScenarios);
    };

    const submitBatch = async () => {
        if (!batchBid || !batchReason) {
            alert("Please set Batch Bid and Reason");
            return;
        }

        setLoading(true);
        try {
            for (const scen of generatedScenarios) {
                const example = {
                    contextHash: `gen-${Date.now()}-${Math.random()}`,
                    gameState: JSON.stringify(scen.state),
                    badMove: "Simulation",
                    correctMove: batchBid,
                    reason: batchReason
                };
                await submitTrainingData(example);
            }
            alert(`Saved ${generatedScenarios.length} scenarios!`);
            setGeneratedScenarios([]);
        } catch (e) {
            console.error(e);
            alert("Error saving batch");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col lg:flex-row flex-1 gap-6 overflow-hidden overflow-y-auto lg:overflow-y-hidden">
            {/* Left: Generator Controls */}
            <div className="w-full lg:w-[400px] shrink-0 bg-slate-800 rounded-xl p-4 overflow-y-auto border border-slate-700 flex flex-col gap-6">

                <div>
                    <h2 className="text-xl font-bold text-slate-300 mb-2">1. Floor Card</h2>
                    <div className="flex flex-wrap gap-1">
                        {suits.map(s => (
                            <div key={s} className="flex gap-1">
                                {ranks.map(r => {
                                    const isSelected = biddingFloorCard?.rank === r && biddingFloorCard?.suit === s;
                                    return (
                                        <button
                                            key={r + s}
                                            onClick={() => setBiddingFloorCard({ rank: r, suit: s })}
                                            className={`w-8 h-10 text-xs font-bold rounded border ${isSelected ? 'bg-yellow-600 border-white ring-2 ring-yellow-400' : 'bg-slate-700 border-slate-600 text-slate-400'} flex items-center justify-center`}
                                        >
                                            <span className={['H', 'D'].includes(s) ? 'text-red-400' : 'text-slate-200'}>{r}{{ S: '♠', H: '♥', D: '♦', C: '♣' }[s] as any}</span>
                                        </button>
                                    )
                                })}
                            </div>
                        ))}
                    </div>
                </div>

                <div>
                    <h2 className="text-xl font-bold text-slate-300 mb-2">2. Core Cards (Required)</h2>
                    <p className="text-xs text-slate-500 mb-2">{coreCards.length}/5 Selected</p>
                    <div className="flex flex-wrap gap-1">
                        {suits.map(s => (
                            <div key={s} className="flex gap-1">
                                {ranks.map(r => {
                                    const isSelected = coreCards.find(c => c.rank === r && c.suit === s);
                                    const isFloor = biddingFloorCard?.rank === r && biddingFloorCard?.suit === s;
                                    return (
                                        <button
                                            key={r + s}
                                            disabled={!!isFloor}
                                            onClick={() => toggleCoreCard({ rank: r, suit: s })}
                                            className={`w-8 h-10 text-xs font-bold rounded border ${isSelected ? 'bg-blue-600 border-white ring-2 ring-blue-400' : isFloor ? 'opacity-20 cursor-not-allowed bg-black' : 'bg-slate-700 border-slate-600 text-slate-400'} flex items-center justify-center`}
                                        >
                                            <span className={['H', 'D'].includes(s) ? 'text-red-400' : 'text-slate-200'}>{r}{{ S: '♠', H: '♥', D: '♦', C: '♣' }[s] as any}</span>
                                        </button>
                                    )
                                })}
                            </div>
                        ))}
                    </div>
                </div>

                <button
                    onClick={generateScenarios}
                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded font-bold transition-all shadow-lg shadow-purple-900/20 flex items-center justify-center gap-2"
                >
                    <Wand2 size={20} /> Generate Batch
                </button>

                <div className="mt-4 pt-4 border-t border-slate-700">
                    <h2 className="text-xl font-bold text-slate-300 mb-2">3. Batch Labeling</h2>
                    <div className="mb-2">
                        <label className="text-xs text-slate-400">Correct Bid</label>
                        <input
                            className="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm text-green-400 font-mono"
                            value={batchBid}
                            onChange={e => setBatchBid(e.target.value)}
                            placeholder='{"action": "SUN"}'
                        />
                        <div className="flex gap-2 mt-1">
                            <button onClick={() => setBatchBid(JSON.stringify({ action: "SUN" }))} className="px-2 py-1 bg-yellow-900/50 text-yellow-400 text-xs rounded border border-yellow-700">Set SUN</button>
                            <button onClick={() => setBatchBid(JSON.stringify({ action: "HOKUM", suit: biddingFloorCard?.suit || 'S' }))} className="px-2 py-1 bg-blue-900/50 text-blue-400 text-xs rounded border border-blue-700">Set HOKUM</button>
                        </div>
                    </div>
                    <div className="mb-4">
                        <label className="text-xs text-slate-400">Reason</label>
                        <textarea
                            className="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm h-20"
                            value={batchReason}
                            onChange={e => setBatchReason(e.target.value)}
                            placeholder="Why is this the best bid?"
                        />
                    </div>

                    <button
                        onClick={submitBatch}
                        disabled={generatedScenarios.length === 0}
                        className={`w-full py-3 bg-green-600 hover:bg-green-500 text-white rounded font-bold flex items-center justify-center gap-2 ${generatedScenarios.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {loading ? 'Saving...' : <><Save size={20} /> Save All ({generatedScenarios.length})</>}
                    </button>
                </div>
            </div>

            {/* Right: Preview List */}
            <div className="flex-1 bg-black/50 rounded-xl border border-slate-700 p-4 flex flex-col overflow-hidden">
                <h2 className="text-xl font-bold text-slate-300 mb-4 flex items-center gap-2"><List /> Generated Scenarios Preview</h2>
                <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-4 content-start">
                    {generatedScenarios.length === 0 ? (
                        <div className="col-span-2 flex flex-col items-center justify-center h-64 text-slate-500">
                            <Wand2 size={48} className="mb-4 opacity-50" />
                            <p>Select cards and generate variations</p>
                        </div>
                    ) : (
                        generatedScenarios.map(scen => (
                            <div key={scen.id} className="bg-slate-800 p-3 rounded border border-slate-600 relative">
                                <div className="absolute top-2 right-2 text-xs text-slate-500 font-mono">{scen.id}</div>
                                <div className="text-xs text-slate-400 mb-1">Floor: <span className="text-white font-bold">{scen.state.floorCard.rank}{scen.state.floorCard.suit}</span></div>
                                <div className="flex gap-1">
                                    {scen.state.players[0].hand.map((c: any, idx: number) => (
                                        <div key={idx} className={`w-8 h-12 flex items-center justify-center bg-slate-200 text-black font-bold rounded text-sm ${['H', 'D'].includes(c.suit) ? 'text-red-600' : ''}`}>
                                            {c.rank}<span className="text-[10px]">{{ S: '♠', H: '♥', D: '♦', C: '♣' }[c.suit] as any}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};

export default BiddingLabView;
