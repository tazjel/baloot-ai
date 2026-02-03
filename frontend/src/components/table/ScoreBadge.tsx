import React from 'react';

interface ScoreBadgeProps {
    matchScores: { us: number, them: number };
}

const ScoreBadge = ({ matchScores }: ScoreBadgeProps) => {
    if (!matchScores) return null;
    return (
        <div className="absolute top-4 left-4 z-50 flex gap-3">
            {/* Us Score */}
            <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl px-2 py-0.5 shadow-xl border-2 border-white/20 backdrop-blur-sm">
                <div className="text-[9px] text-white/80 font-bold">نحن</div>
                <div className="text-[15px] font-black text-white">{matchScores.us}</div>
            </div>
            {/* Them Score */}
            <div className="bg-gradient-to-br from-red-600 to-red-800 rounded-2xl px-2 py-0.5 shadow-xl border-2 border-white/20 backdrop-blur-sm">
                <div className="text-[9px] text-white/80 font-bold">هم</div>
                <div className="text-[15px] font-black text-white">{matchScores.them}</div>
            </div>
        </div>
    );
};

export default ScoreBadge;
