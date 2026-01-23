import React, { useEffect, useState } from 'react';
import { GamePhase } from '../types';
import { Clock } from 'lucide-react';

interface GablakTimerProps {
    biddingPhase?: string;
    isActive: boolean;
    duration?: number; // Total duration (e.g. 5s)
    startTime?: number; // Server timestamp
}

const GablakTimer: React.FC<GablakTimerProps> = ({ biddingPhase, isActive, duration = 5, startTime }) => {
    const [timeLeft, setTimeLeft] = useState(duration);

    useEffect(() => {
        if (biddingPhase !== 'GABLAK_WINDOW') return;

        // Simple local countdown for visualization
        // In real implementations, sync with server time
        setTimeLeft(duration);

        const interval = setInterval(() => {
            setTimeLeft(prev => {
                if (prev <= 0) {
                    clearInterval(interval);
                    return 0;
                }
                return prev - 0.1;
            });
        }, 100);

        return () => clearInterval(interval);
    }, [biddingPhase, duration, startTime]);

    if (biddingPhase !== 'GABLAK_WINDOW') return null;

    // Calculate progress for bar
    const progress = (timeLeft / duration) * 100;
    const isCritical = timeLeft < 2;

    return (
        <div className="absolute top-[40%] left-1/2 -translate-x-1/2 z-50 flex flex-col items-center animate-pulse-fast">
            <div className={`
                flex items-center gap-2 px-6 py-2 rounded-full border-2 shadow-[0_0_20px_rgba(255,165,0,0.5)]
                backdrop-blur-md transition-colors duration-300
                ${isCritical ? 'bg-red-900/80 border-red-500 text-red-200' : 'bg-amber-900/80 border-amber-500 text-amber-200'}
            `}>
                <Clock size={20} className={isCritical ? 'animate-bounce' : ''} />
                <span className="font-bold font-tajawal text-lg">
                    فرصة قيدها! (Steal Window)
                </span>
                <span className="font-mono text-xl w-12 text-center">
                    {timeLeft.toFixed(1)}s
                </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-2 bg-black/50 rounded-full mt-2 overflow-hidden border border-white/10">
                <div
                    className={`h-full transition-all duration-100 ease-linear ${isCritical ? 'bg-red-500' : 'bg-amber-500'}`}
                    style={{ width: `${progress}%` }}
                />
            </div>

            {isActive && (
                <div className="mt-2 text-xs text-amber-300 font-bold bg-black/60 px-2 py-1 rounded">
                    Tap project/play to steal!
                </div>
            )}
        </div>
    );
};

export default GablakTimer;
