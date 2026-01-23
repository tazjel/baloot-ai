import React from 'react';
import { GamePhase } from '../../types';

interface ActionSelectorProps {
    phase: GamePhase;
    hand: any[]; // We'll type this loosely for now as it comes from JSON
    currentSelection: string | null; // JSON string of selected action
    onSelect: (actionJson: string) => void;
}

const ActionSelector: React.FC<ActionSelectorProps> = ({ phase, hand, currentSelection, onSelect }) => {

    // Helper to check if selection matches
    const isSelected = (actionJson: string) => currentSelection === actionJson;
    const isSunSelected = currentSelection?.includes("SUN");

    if (phase === GamePhase.Bidding) {
        return (
            <div className="grid grid-cols-2 gap-2">
                <button onClick={() => onSelect(JSON.stringify({ action: "PASS" }))} className={`p-2 rounded border ${currentSelection?.includes("PASS") ? 'bg-slate-600 border-green-500' : 'bg-slate-800 border-slate-600 hover:bg-slate-700'}`}>Pass</button>
                <button onClick={() => onSelect(JSON.stringify({ action: "ASHKEL" }))} className={`p-2 rounded border ${currentSelection?.includes("ASHKEL") ? 'bg-red-900/50 border-red-500' : 'bg-slate-800 border-slate-600 hover:bg-red-900/30'}`}>Ashkel</button>
                <button onClick={() => onSelect(JSON.stringify({ action: "SUN" }))} className={`p-2 rounded border col-span-2 ${currentSelection?.includes("SUN") ? 'bg-yellow-600/50 border-yellow-500' : 'bg-slate-800 border-slate-600 hover:bg-yellow-600/30'}`}>Sun ☀️</button>
                {['S', 'H', 'D', 'C'].map(s => (
                    <button key={s} onClick={() => onSelect(JSON.stringify({ action: "HOKUM", suit: s }))} className={`p-2 rounded border text-xl ${currentSelection?.includes(s) && currentSelection?.includes("HOKUM") ? 'bg-slate-600 border-blue-500' : 'bg-slate-800 border-slate-600 hover:bg-slate-700'}`}>
                        <span className={['H', 'D'].includes(s) ? 'text-red-500' : 'text-white'}>{{ S: '♠', H: '♥', D: '♦', C: '♣' }[s] as any}</span>
                    </button>
                ))}
            </div>
        );
    } else {
        return (
            <div className="grid grid-cols-4 gap-1">
                {hand.map((c: any, idx: number) => {
                    // Normalize play action structure
                    // The Studio saves { action: "PLAY_CARD", card: c }
                    const actionJson = JSON.stringify({ action: "PLAY_CARD", card: c });
                    const selected = isSelected(actionJson);
                    return (
                        <button
                            key={idx}
                            onClick={() => onSelect(actionJson)}
                            className={`p-1 rounded border text-sm h-12 flex items-center justify-center font-bold relative group
                                ${selected ? 'bg-green-600 border-green-400 text-white shadow' : 'bg-white text-black border-slate-400 opacity-90 hover:opacity-100 hover:-translate-y-1 transition-transform'}
                            `}
                        >
                            <span className={['H', 'D'].includes(c.suit) ? 'text-red-600' : 'text-black'}>
                                {c.rank}
                                <span className="text-xs ml-0.5">{{ S: '♠', H: '♥', D: '♦', C: '♣' }[c.suit] as any}</span>
                            </span>
                        </button>
                    );
                })}
            </div>
        );
    }
};

export default ActionSelector;
