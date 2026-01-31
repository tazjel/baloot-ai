
import React from 'react';
import { CardModel, Suit, Rank } from '../types';
import { Spade, Heart, Club, Diamond } from './SuitIcons';

interface CardV2Props {
    card: CardModel;
    isHidden?: boolean;
    isSmall?: boolean;
    onClick?: () => void;
    className?: string;
    selected?: boolean;
    disabled?: boolean;
    isPlayable?: boolean;
    animationDelay?: number;
}

interface SuitIconProps {
    suit: Suit;
    color: string;
    size: number;
    className?: string;
}

const SuitIconRender: React.FC<SuitIconProps> = ({ suit, color, size, className }) => {
    switch (suit) {
        case Suit.Spades: return <Spade size={size} color={color} className={className} />;
        case Suit.Hearts: return <Heart size={size} color={color} className={className} />;
        case Suit.Clubs: return <Club size={size} color={color} className={className} />;
        case Suit.Diamonds: return <Diamond size={size} color={color} className={className} />;
        default: return null;
    }
};

const getRankSymbolAR = (rank: Rank): string => {
    switch (rank) {
        case Rank.Ace: return 'أ';
        case Rank.King: return 'ك';
        case Rank.Queen: return 'ق';
        case Rank.Jack: return 'ج';
        case Rank.Ten: return '۱۰';
        case Rank.Nine: return '۹';
        case Rank.Eight: return '۸';
        case Rank.Seven: return '۷';
        default: return rank;
    }
};

const getSuitColor = (suit: Suit): string => {
    // Classic Style: Rich Red vs Jet Black
    return (suit === Suit.Hearts || suit === Suit.Diamonds) ? '#D32F2F' : '#111111';
};

const CardV2: React.FC<CardV2Props> = ({
    card,
    isHidden = false,
    isSmall = false,
    onClick,
    className = '',
    selected = false,
    disabled = false,
    isPlayable = true,
    animationDelay = 0,
}) => {
    if (!card) return null;

    const suitColor = getSuitColor(card.suit);
    const rankSymbol = getRankSymbolAR(card.rank); // Default to Arabic for Classic feel
    const isCourtCard = [Rank.King, Rank.Queen, Rank.Jack].includes(card.rank);

    // Premium texture background (CSS only)
    const textureStyle = {
        backgroundImage: `repeating-linear-gradient(45deg, rgba(0,0,0,0.01) 0px, rgba(0,0,0,0.01) 2px, transparent 2px, transparent 4px)`
    };

    // Back Pattern (Arabic Geometric)
    const backStyle = {
        backgroundImage: `
      radial-gradient(circle at center, #1e3a8a 0%, #172554 100%),
      repeating-radial-gradient(circle at 50% 50%, rgba(255,255,255,0.1) 0, rgba(255,255,255,0.1) 2px, transparent 4px, transparent 8px)
    `
    };

    const containerClasses = `
    relative 
    w-full h-full
    aspect-[5/7]
    flex flex-col items-center justify-center 
    rounded-lg
    select-none 
    transition-transform duration-300
    bg-stone-50
    border-2
    shadow-lg
    ${selected ? 'z-50 ring-4 ring-yellow-400 ring-offset-2' : 'border-stone-300'}
    ${disabled ? 'grayscale opacity-60 pointer-events-none' : ''}
    ${!disabled && isPlayable ? 'cursor-pointer hover:-translate-y-4 hover:shadow-xl' : ''}
    ${!isPlayable && !disabled ? 'opacity-90 brightness-95' : ''}
    ${className}
  `;

    if (isHidden) {
        return (
            <div
                className={`${containerClasses} overflow-hidden`}
                onClick={onClick}
                style={{
                    ...backStyle,
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                    animationDelay: `${animationDelay}ms`,
                    border: '2px solid #fff',
                }}
            >
                {/* Inner Border for detail */}
                <div className="absolute inset-2 border border-white/30 rounded-md opacity-50"></div>
                <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center backdrop-blur-sm">
                    {/* Logo or Center Icon placeholder */}
                    <div className="w-8 h-8 border-2 border-white/40 rotate-45"></div>
                </div>
            </div>
        );
    }

    return (
        <div
            className={containerClasses}
            onClick={onClick}
            style={{
                ...textureStyle,
                animationDelay: `${animationDelay}ms`,
                transform: selected ? 'translateY(-30px)' : undefined
            }}
        >
            {/* Gold/Bronze Border Effect inside */}
            <div className="absolute inset-1 border border-yellow-600/20 rounded-[inherit] pointer-events-none"></div>

            {/* Top Left Index */}
            <div className="absolute top-1 left-2 flex flex-col items-center leading-none">
                <span style={{ color: suitColor }} className="font-bold text-[clamp(1.2rem,4vw,2rem)] font-sans">
                    {rankSymbol}
                </span>
                <SuitIconRender suit={card.suit} color={suitColor} size={isSmall ? 10 : 14} />
            </div>

            {/* Bottom Right Index (Rotated) */}
            <div className="absolute bottom-1 right-2 flex flex-col items-center leading-none rotate-180">
                <span style={{ color: suitColor }} className="font-bold text-[clamp(1.2rem,4vw,2rem)] font-sans">
                    {rankSymbol}
                </span>
                <SuitIconRender suit={card.suit} color={suitColor} size={isSmall ? 10 : 14} />
            </div>

            {/* Center Content */}
            <div className={`flex-1 flex items-center justify-center w-full h-full`}>
                {isCourtCard ? (
                    <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
                        {/* Watermark Big Letter */}
                        <span style={{ color: suitColor }} className="absolute text-[6rem] opacity-5 font-serif font-black">
                            {card.rank === Rank.Ten ? '10' : card.rank}
                        </span>

                        {/* Court Icon - Placeholder for now, can use Crown SVG later */}
                        <div className="border-4 double p-4 rounded-full bg-white/50 backdrop-blur-[2px]" style={{ borderColor: suitColor }}>
                            <SuitIconRender suit={card.suit} color={suitColor} size={42} />
                        </div>

                        {/* Crown Hint */}
                        <div className="absolute top-[25%] text-yellow-500 opacity-80">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M5 16L3 5L8.5 10L12 4L15.5 10L21 5L19 16H5M19 19C19 19.6 18.6 20 18 20H6C5.4 20 5 19.6 5 19V18H19V19Z" />
                            </svg>
                        </div>
                    </div>
                ) : (
                    <div className="transform scale-[1.5]">
                        {/* Simple Pips for Numbers */}
                        <div className="grid grid-cols-2 gap-1 p-2 border-2 rounded-lg opacity-80" style={{ borderColor: suitColor }}>
                            {Array.from({ length: 4 }).map((_, i) => (
                                <SuitIconRender key={i} suit={card.suit} color={suitColor} size={12} />
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CardV2;
