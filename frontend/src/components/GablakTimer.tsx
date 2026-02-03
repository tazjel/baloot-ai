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
        <div className="absolute top-[40%] left-1/2 -translate-x-1/2 z-50 flex flex-col items-center animate-in fade-in zoom-in duration-300">
            <div className={`
                flex items-center gap-2 px-3 py-1.5 rounded-full border shadow-lg backdrop-blur-sm
                transition-colors duration-300
                ${isCritical ? 'bg-red-900/90 border-red-500/50 text-red-100' : 'bg-amber-900/90 border-amber-500/50 text-amber-100'}
            `}>
                <Clock size={14} className={isCritical ? 'animate-bounce' : ''} />
                <div className="flex flex-col items-center leading-none">
                    <span className="font-bold font-tajawal text-xs sm:text-sm">
                        فرصة قيد (Gablak)
                    </span>
                </div>
                <span className="font-mono text-sm font-bold w-8 text-center bg-black/20 rounded px-1">
                    {timeLeft.toFixed(1)}
                </span>
            </div>

            {/* Micro Progress Bar */}
            <div className="w-[80%] h-1 bg-black/40 rounded-full mt-1 overflow-hidden">
                <div
                    className={`h-full transition-all duration-100 ease-linear ${isCritical ? 'bg-red-500' : 'bg-amber-500'}`}
                    style={{ width: `${progress}%` }}
                />
            </div>
        </div>
    );
};

export default GablakTimer;
