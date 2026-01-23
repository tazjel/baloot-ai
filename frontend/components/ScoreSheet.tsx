import React from 'react';
import { RoundResult } from '../types';

interface ScoreSheetProps {
    roundHistory: RoundResult[];
    matchScores: { us: number; them: number };
    currentRoundScore: { us: number; them: number };
}

const ScoreSheet: React.FC<ScoreSheetProps> = ({ roundHistory, matchScores, currentRoundScore }) => {
    return (
        <div className="w-full bg-[#f3e5ab] text-black font-serif rounded-lg shadow-inner overflow-hidden relative">
            {/* Paper Texture Overlay */}
            <div className="absolute inset-0 pointer-events-none opacity-10 bg-[url('https://www.transparenttextures.com/patterns/notebook.png')]"></div>

            {/* Header */}
            <div className="flex border-b-2 border-gray-400 bg-[#e6d595] p-2 text-center font-bold text-lg relative z-10">
                <div className="w-1/2 border-l border-gray-400">لنا (Lana)</div>
                <div className="w-1/2">لهم (Laham)</div>
            </div>

            {/* History Rows */}
            <div className="p-2 space-y-1 min-h-[150px] relative z-10">
                {roundHistory.map((round) => (
                    <div key={round.roundNumber} className="flex text-lg border-b border-gray-300 pb-1 group relative cursor-help hover:bg-black/5 transition-colors">
                        {/* Tooltip for Score Breakdown */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-black text-white text-xs p-2 rounded hidden group-hover:block z-50 pointer-events-none shadow-xl">
                            <div className="font-bold border-b border-gray-600 mb-1 pb-1">Round {round.roundNumber} Breakdown</div>
                            <div className="flex justify-between text-blue-300">
                                <span>Us:</span>
                                <span>{round.us.rawCardPoints} (Cards) + {round.us.projectPoints} (Proj)</span>
                            </div>
                            <div className="flex justify-between text-red-300">
                                <span>Them:</span>
                                <span>{round.them.rawCardPoints} (Cards) + {round.them.projectPoints} (Proj)</span>
                            </div>
                        </div>

                        {/* Penalty / Qayd Indicators */}
                        {round.us.totalRaw === 0 && (
                            <div className="absolute left-1 top-1/2 -translate-y-1/2 text-red-600 text-xs font-black" title="Qayd / Shutout">❌</div>
                        )}
                        {round.them.totalRaw === 0 && (
                            <div className="absolute right-1 top-1/2 -translate-y-1/2 text-red-600 text-xs font-black" title="Qayd / Shutout">❌</div>
                        )}

                        <div className={`w-1/2 text-center border-l border-gray-300 font-bold ${round.winner === 'us' ? 'text-green-800' : ''}`}>
                            {round.us.gamePoints}
                        </div>
                        <div className={`w-1/2 text-center font-bold ${round.winner === 'them' ? 'text-red-800' : ''}`}>
                            {round.them.gamePoints}
                        </div>
                    </div>
                ))}

                {/* Current Round (In Progress) */}
                <div className="flex text-lg text-gray-500 italic">
                    <div className="w-1/2 text-center border-l border-gray-300">{currentRoundScore.us > 0 ? `+${currentRoundScore.us}` : '-'}</div>
                    <div className="w-1/2 text-center">{currentRoundScore.them > 0 ? `+${currentRoundScore.them}` : '-'}</div>
                </div>
            </div>

            {/* Total Footer */}
            <div className="flex border-t-2 border-gray-800 bg-[#e6d595] p-2 text-center font-black text-xl relative z-10">
                <div className="w-1/2 border-l border-gray-800 text-blue-900">{matchScores.us}</div>
                <div className="w-1/2 text-red-900">{matchScores.them}</div>
            </div>

            {/* Sakkah Line Visualization (Optional - usually just a line across) */}
            <div className="absolute top-0 bottom-0 left-1/2 w-px bg-red-400/30 z-0"></div>
        </div>
    );
};

export default ScoreSheet;
