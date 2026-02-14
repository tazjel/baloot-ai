import React, { useRef, useEffect, useState } from 'react';
import { useAnimatedNumber } from '../../hooks/useAnimatedNumber';

interface ScoreBadgeProps {
    matchScores: { us: number, them: number };
}

const ScoreBadge = ({ matchScores }: ScoreBadgeProps) => {
    if (!matchScores) return null;

    const usDisplay = useAnimatedNumber(matchScores.us);
    const themDisplay = useAnimatedNumber(matchScores.them);

    // Track flash state
    const prevUsRef = useRef(matchScores.us);
    const prevThemRef = useRef(matchScores.them);
    const [usFlash, setUsFlash] = useState(false);
    const [themFlash, setThemFlash] = useState(false);

    useEffect(() => {
        if (matchScores.us !== prevUsRef.current) {
            prevUsRef.current = matchScores.us;
            setUsFlash(true);
            const t = setTimeout(() => setUsFlash(false), 400);
            return () => clearTimeout(t);
        }
    }, [matchScores.us]);

    useEffect(() => {
        if (matchScores.them !== prevThemRef.current) {
            prevThemRef.current = matchScores.them;
            setThemFlash(true);
            const t = setTimeout(() => setThemFlash(false), 400);
            return () => clearTimeout(t);
        }
    }, [matchScores.them]);

    return (
        <div className="absolute top-4 left-4 z-50 flex gap-3">
            {/* Us Score */}
            <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl px-2 py-0.5 shadow-xl border-2 border-white/20 backdrop-blur-sm">
                <div className="text-[9px] text-white/80 font-bold">نحن</div>
                <div className={`text-[15px] font-black text-white ${usFlash ? 'score-flash' : ''}`}>{usDisplay}</div>
            </div>
            {/* Them Score */}
            <div className="bg-gradient-to-br from-red-600 to-red-800 rounded-2xl px-2 py-0.5 shadow-xl border-2 border-white/20 backdrop-blur-sm">
                <div className="text-[9px] text-white/80 font-bold">هم</div>
                <div className={`text-[15px] font-black text-white ${themFlash ? 'score-flash' : ''}`}>{themDisplay}</div>
            </div>
        </div>
    );
};

export default ScoreBadge;
