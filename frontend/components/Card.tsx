import React from 'react';
import { CardModel, Suit, Rank } from '../types';
import { Spade, Heart, Club, Diamond } from './SuitIcons';

interface CardProps {
  card: CardModel;
  isHidden?: boolean;
  isSmall?: boolean;
  onClick?: () => void;
  className?: string;
  selected?: boolean;
  disabled?: boolean;
  skin?: string;
  isFourColorMode?: boolean;
  isHighContrast?: boolean;
  isPlayable?: boolean;
  animationDelay?: number;
  cardLanguage?: 'EN' | 'AR';
  isAkka?: boolean;
}

// Typography: Slab Serif for standard English indices
const getRankSymbolEN = (rank: Rank): string => {
  switch (rank) {
    case Rank.Ace: return 'A';
    case Rank.King: return 'K';
    case Rank.Queen: return 'Q';
    case Rank.Jack: return 'J';
    default: return rank;
  }
};

// Colors: Darker Red (#D32F2F) for Hearts/Diamonds to reduce eye strain
const getSuitColor = (suit: Suit, isFourColorMode: boolean = false, isHighContrast: boolean = false): string => {
  if (isHighContrast) return (suit === Suit.Hearts || suit === Suit.Diamonds) ? '#ff0000' : '#000000';
  if (isFourColorMode) {
    switch (suit) {
      case Suit.Spades: return '#1a1a1a';
      case Suit.Hearts: return '#dc2626';
      case Suit.Clubs: return '#166534';
      case Suit.Diamonds: return '#2563eb';
    }
  }
  // Standard Premium Palette: Dark Red vs Black
  return (suit === Suit.Hearts || suit === Suit.Diamonds) ? '#D32F2F' : '#111111';
};

// Arabic Indices
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

const Card: React.FC<CardProps> = ({
  card,
  isHidden = false,
  isSmall = false,
  onClick,
  className = '',
  selected = false,
  disabled = false,
  isFourColorMode = false,
  isHighContrast = false,
  isPlayable = true,
  animationDelay = 0,

  cardLanguage = 'EN', // Default
  isAkka = false
}) => {
  if (!card) return null;

  const isCourtCard = [Rank.King, Rank.Queen, Rank.Jack].includes(card.rank);
  const suitColor = getSuitColor(card.suit, isFourColorMode, isHighContrast);

  const rankSymbol = cardLanguage === 'AR' ? getRankSymbolAR(card.rank) : getRankSymbolEN(card.rank);
  // Font override for Arabic might be needed if Roboto Slab doesn't support it well, but standard fonts usually do.
  // Using native font stack for Arabic fallback.
  const fontFamily = cardLanguage === 'AR' ? '"Tajawal", "Segoe UI", sans-serif' : '"Roboto Slab", serif';

  const SuitIcon = ({ size, className }: { size: number, className?: string }) => {
    switch (card.suit) {
      case Suit.Spades: return <Spade size={size} color={suitColor} className={className} />;
      case Suit.Hearts: return <Heart size={size} color={suitColor} className={className} />;
      case Suit.Clubs: return <Club size={size} color={suitColor} className={className} />;
      case Suit.Diamonds: return <Diamond size={size} color={suitColor} className={className} />;
    }
  };

  // Premium Style: 5:7 Aspect Ratio, Rounded Corners, Crisp White
  const containerClasses = `
    relative 
    w-full h-full
    aspect-[5/7]
    flex flex-col items-center justify-center 
    rounded-[10%] 
    select-none 
    transition-transform duration-300
    bg-white
    ${selected ? 'z-50 card-selected' : ''}
    ${disabled ? 'grayscale opacity-60 pointer-events-none' : ''}
    ${!disabled && isPlayable ? 'cursor-pointer hover:brightness-105' : ''}
    ${!isPlayable && !disabled ? 'opacity-90 brightness-95' : ''}
    ${className}
  `;

  if (isHidden) {
    return (
      <div
        className={`${containerClasses} overflow-hidden`}
        onClick={onClick}
        style={{
          boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
          border: '1px solid #ddd',
          backgroundImage: 'linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)', // Simple Back
          animationDelay: `${animationDelay}ms`,
        }}
      >
        <div className="w-full h-full border-4 border-white/20 rounded-[8%] m-1"></div>
      </div>
    );
  }

  return (
    <div
      className={containerClasses}
      onClick={onClick}
      style={{
        boxShadow: selected
          ? '0 0 0 2px #d4af37, 0 10px 20px rgba(0,0,0,0.3)'
          : '0 2px 6px rgba(0,0,0,0.15)',
        border: '1px solid #e5e5e5',
        animationDelay: `${animationDelay}ms`,
        transform: selected ? 'translateY(-30px)' : undefined
      }}
    >
      {/* Akka Badge */}
      {isAkka && (
        <div className="absolute -top-3 -right-3 z-50 bg-rose-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-md animate-bounce border-2 border-white">
          أكة
        </div>
      )}

      {/* --- Top-Left Index (Primary) --- */}
      <div className="absolute top-[4%] left-[6%] flex flex-col items-center leading-none">
        <span style={{ color: suitColor, fontFamily }} className="font-bold text-[clamp(1rem,4vw,1.8rem)] tracking-tight">
          {rankSymbol}
        </span>
        <div className="mt-[-2px]">
          <SuitIcon size={isSmall ? 12 : 16} />
        </div>
      </div>

      {/* --- Bottom-Right Index (Rotated) --- */}
      <div className="absolute bottom-[4%] right-[6%] flex flex-col items-center leading-none rotate-180">
        <span style={{ color: suitColor, fontFamily }} className="font-bold text-[clamp(1rem,4vw,1.8rem)] tracking-tight">
          {rankSymbol}
        </span>
        <div className="mt-[-2px]">
          <SuitIcon size={isSmall ? 12 : 16} />
        </div>
      </div>

      {/* --- Center Art (Faded for Court Cards) --- */}
      <div className={`flex-1 flex items-center justify-center w-full h-full ${isCourtCard ? 'opacity-80' : ''}`}>
        {isCourtCard ? (
          <div className="relative flex items-center justify-center w-full h-full overflow-hidden">
            {/* Abstract Court Card Graphic or Big Letter */}
            <span style={{ color: suitColor }} className="text-[clamp(3rem,8vw,5rem)] font-serif font-black opacity-15 absolute">
              {rankSymbol}
            </span>
            <SuitIcon size={48} className="opacity-90" />
          </div>
        ) : (
          <div className="transform scale-[1.8]">
            <SuitIcon size={28} />
          </div>
        )}
      </div>
    </div>
  );
};

export default Card;