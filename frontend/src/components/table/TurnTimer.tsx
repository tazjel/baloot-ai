import React from 'react';
import { Pause } from 'lucide-react';

interface TurnTimerProps {
    isActive: boolean;
    timeLeft: number;
    totalTime: number;
    isPaused?: boolean;
}

const TurnTimer = ({ isActive, timeLeft, totalTime, isPaused = false }: TurnTimerProps) => {
    if (!isActive) return null;

    const radius = 36;
    const stroke = 6;
    const circumference = 2 * Math.PI * radius;
    const percentage = timeLeft / totalTime;
    const progress = percentage * circumference;

    let strokeColor = '#22c55e'; // Green
    if (percentage < 0.25) strokeColor = '#ef4444'; // Red
    else if (percentage < 0.5) strokeColor = '#D4AF37'; // Gold

    return (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[84px] h-[84px] pointer-events-none z-50 flex items-center justify-center">
            <svg
                className="-rotate-90 absolute inset-0"
                width="84" height="84"
                viewBox="0 0 84 84"
            >
                <circle cx="42" cy="42" r={radius} stroke="rgba(0,0,0,0.4)" strokeWidth={stroke} fill="none" />
                <circle
                    cx="42" cy="42" r={radius}
                    stroke={strokeColor}
                    strokeWidth={stroke}
                    strokeLinecap="round"
                    fill="none"
                    strokeDasharray={circumference}
                    strokeDashoffset={circumference - progress}
                    className={`transition-all duration-1000 ease-linear shadow-lg ${isPaused ? 'pause-animation' : ''}`}
                    style={{ filter: 'drop-shadow(0 0 2px rgba(0,0,0,0.5))' }}
                />
            </svg>
            <span className="text-amber-400 font-black text-sm sm:text-base md:text-lg drop-shadow-md z-50">
                {timeLeft}
            </span>
            {isPaused && <Pause size={20} className="absolute text-white animate-pulse" />}
        </div>
    );
};

export default TurnTimer;
