import React from 'react';
import { CardModel, Suit, Rank } from '../types';
import cardsSprite from '../assets/cards.png';
import cardBack from '../assets/royal_card_back.png';

interface CardRealProps {
    card: CardModel;
    isHidden?: boolean;
    className?: string;
    selected?: boolean;
    onClick?: () => void;
    isPlayable?: boolean;
    // Legacy props to ignore
    isFourColorMode?: boolean;
    isHighContrast?: boolean;
    cardLanguage?: string;
    isAccessibilityMode?: boolean;
    skin?: string;
    isAkka?: boolean; // We might want to overlay this
}

const CardReal: React.FC<CardRealProps> = ({
    card,
    isHidden = false,
    className = '',
    selected = false,
    onClick,
    isPlayable = true,
    isAkka = false,
}) => {
    if (!card) return null;

    // --- SPRITE SHEET MAPPING ---
    // Dimensions determined: 2600x1120
    // Cols: 13
    // Rows: 4

    const getRankIndex = (rank: Rank): number => {
        // Standard Deck Order: A, 2, 3... 10, J, Q, K
        // Note: Some sprites start with 2 and end with Ace.
        // Let's assume A, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K
        const ranks = [Rank.Ace, '2', '3', '4', '5', '6', '7', Rank.Eight, Rank.Nine, Rank.Ten, Rank.Jack, Rank.Queen, Rank.King];
        return ranks.indexOf(rank);
    };

    const getSuitIndex = (suit: Suit): number => {
        // Common Sprite Order 1: Spades, Hearts, Diamonds, Clubs
        // Common Sprite Order 2: Spades, Hearts, Clubs, Diamonds
        // We will default to: Spades, Hearts, Clubs, Diamonds
        // If user says "Wrong suit", we swap lines here.
        switch (suit) {
            case Suit.Spades: return 0; // Row 0
            case Suit.Hearts: return 1; // Row 1
            case Suit.Clubs: return 2;  // Row 2
            case Suit.Diamonds: return 3; // Row 3
        }
        return 0;
    };

    const rankIdx = getRankIndex(card.rank); // 0..12
    const suitIdx = getSuitIndex(card.suit); // 0..3

    // CSS Logic for Sprites
    // x% = (index / (total - 1)) * 100
    const xPos = (rankIdx / 12) * 100;
    const yPos = (suitIdx / 3) * 100;

    const playStyle = (!isHidden && isPlayable) ? 'cursor-pointer hover:-translate-y-2 hover:shadow-2xl' : '';
    const disabledStyle = (!isHidden && !isPlayable) ? 'opacity-90 brightness-75' : '';

    return (
        <div
            className={`
        relative aspect-[5/7] rounded-[5%] shadow-md transition-all duration-300
        ${selected ? 'ring-4 ring-yellow-400 -translate-y-6 z-50 shadow-[0_0_30px_rgba(255,215,0,0.6)]' : ''}
        ${playStyle}
        ${disabledStyle}
        ${className}
      `}
            onClick={onClick}
            style={{
                backgroundImage: isHidden ? `url(${cardBack})` : `url(${cardsSprite})`,
                backgroundSize: isHidden ? 'cover' : '1300% 400%',
                backgroundPosition: isHidden ? 'center' : `${xPos}% ${yPos}%`,
                backgroundColor: 'white',
                imageRendering: 'high-quality'
            }}
        >
            {/* Akka Badge Overlay */}
            {isAkka && !isHidden && (
                <div className="absolute -top-2 -right-2 bg-gradient-to-r from-red-600 to-rose-600 text-white text-[10px] sm:text-xs font-black px-2 py-0.5 rounded-full border border-white shadow-lg z-20 animate-bounce">
                    أكة
                </div>
            )}
        </div>
    );
};

export default CardReal;
