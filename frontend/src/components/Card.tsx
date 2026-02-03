import React, { useMemo } from 'react';
import { CardModel, Suit, Rank } from '../types';
import { Spade, Heart, Club, Diamond } from './SuitIcons';
import { motion } from 'framer-motion';

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
  isAccessibilityMode?: boolean;
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
const getSuitColor = (suit: Suit, isFourColorMode: boolean = false, isHighContrast: boolean = false, isAccessibilityMode: boolean = false): string => {
  if (isAccessibilityMode) {
    switch (suit) {
      case Suit.Diamonds: return '#3ABEF9'; // Light Blue
      case Suit.Spades: return '#55AD9B'; // Green
      case Suit.Hearts: return '#dc2626'; // Standard Red
      case Suit.Clubs: return '#111111'; // Standard Black
    }
  }

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
  isAkka = false,
  isAccessibilityMode = false
}) => {
  if (!card) return null;

  const isCourtCard = [Rank.King, Rank.Queen, Rank.Jack].includes(card.rank);
  const suitColor = getSuitColor(card.suit, isFourColorMode, isHighContrast, isAccessibilityMode);
  const rankSymbol = cardLanguage === 'AR' ? getRankSymbolAR(card.rank) : getRankSymbolEN(card.rank);
  const fontFamily = cardLanguage === 'AR' ? '"Tajawal", "Segoe UI", sans-serif' : '"Roboto Slab", serif';

  const SuitIcon = ({ size, className }: { size: number, className?: string }) => {
    switch (card.suit) {
      case Suit.Spades: return <Spade size={size} color={suitColor} className={className} />;
      case Suit.Hearts: return <Heart size={size} color={suitColor} className={className} />;
      case Suit.Clubs: return <Club size={size} color={suitColor} className={className} />;
      case Suit.Diamonds: return <Diamond size={size} color={suitColor} className={className} />;
    }
  };

  const containerClasses = `
    relative 
    w-full h-full
    aspect-[5/7]
    flex flex-col items-center justify-center 
    rounded-[10%] 
    select-none 
    bg-white
    ${disabled ? 'grayscale opacity-60 pointer-events-none' : ''}
    ${!disabled && isPlayable ? 'cursor-pointer' : ''}
    ${!isPlayable && !disabled ? 'opacity-90 brightness-95' : ''}
    ${className}
  `;

  // Motion Variants
  const variants = {
    hidden: { opacity: 0, y: 50, scale: 0.8 },
    visible: {
      opacity: 1,
      y: selected ? -30 : 0,
      scale: 1,
      transition: { delay: animationDelay / 1000, type: "spring", stiffness: 300, damping: 20 }
    },
    hover: (!disabled && isPlayable) ? {
      y: -15,
      scale: 1.05,
      boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2)"
    } : {},
    tap: (!disabled && isPlayable) ? { scale: 0.95 } : {}
  };

  if (isHidden) {
    return (
      <motion.div
        className={`${containerClasses} overflow-hidden`}
        onClick={onClick}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: animationDelay / 1000 }}
        style={{
          boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
          border: '1px solid #ddd',
          backgroundImage: 'linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)', // Simple Back
        }}
      >
        <div className="w-full h-full border-4 border-white/20 rounded-[8%] m-1"></div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className={containerClasses}
      onClick={onClick}
      variants={variants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      whileTap="tap"
      style={{
        boxShadow: selected
          ? '0 0 0 3px #d4af37, 0 10px 20px rgba(0,0,0,0.3)'
          : '0 2px 6px rgba(0,0,0,0.15)',
        border: '1px solid #e5e5e5',
        zIndex: selected ? 50 : 'auto'
      }}
    >
      {/* Akka Badge */}
      {isAkka && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -top-3 -right-3 z-50 bg-rose-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-md border-2 border-white"
        >
          أكة
        </motion.div>
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
    </motion.div>
  );
};

export default Card;