import React from 'react';

// Helper for card display
const MiniCard = ({ card, playedBy, isWinner }: { card: any, playedBy: string, isWinner: boolean }) => {
    if (!card) return <div className="w-12 h-16 bg-white/10 rounded border border-dashed border-white/20" />;

    const getSuitColor = (s: string) => {
        if (s === '♥' || s === '♦') return 'text-red-500';
        return 'text-black';
    };

    return (
        <div className={`flex flex-col items-center gap-1 ${isWinner ? 'scale-110' : ''}`}>
            <div className={`
                w-12 h-16 bg-white rounded shadow-md border 
                ${isWinner ? 'border-[var(--color-premium-gold)] ring-2 ring-[var(--color-premium-gold)]/50' : 'border-gray-300'}
                flex items-center justify-center relative
            `}>
                <span className={`text-xl font-bold ${getSuitColor(card.suit)}`}>{card.rank}</span>
                <span className={`absolute bottom-1 right-1 text-xs ${getSuitColor(card.suit)}`}>{card.suit}</span>
            </div>
            <span className="text-[10px] text-white/80 uppercase font-bold text-center max-w-[4rem] truncate">
                {playedBy}
            </span>
            {isWinner && <span className="text-[8px] bg-[var(--color-premium-gold)] text-black px-1 rounded">WINNER</span>}
        </div>
    );
};

export default MiniCard;
