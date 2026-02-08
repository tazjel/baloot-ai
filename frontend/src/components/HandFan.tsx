import React from 'react';
import { motion } from 'framer-motion';
import { CardModel, Suit } from '../types';
import Card from './Card';
import { sortHand } from '../utils/gameLogic';

interface HandFanProps {
    hand: CardModel[];
    selectedCardIndex: number | null;
    isMyTurn: boolean;
    onCardClick: (index: number) => void;
    cardSkin?: string;
    gameMode: 'SUN' | 'HOKUM';
    trumpSuit?: Suit;
    settings?: any; // To be typed strictly later
}

// Layout Constants
const FAN_SPACING = {
    base: '-space-x-8',
    sm: 'sm:-space-x-10',
    md: 'md:-space-x-12'
};

const ELEVATION = {
    base: 'bottom-0',
    elevated: 'bottom-5 sm:bottom-6',
    hoverBase: 'hover:bottom-4',
    hoverElevated: 'hover:bottom-9 sm:hover:bottom-10',
    selected: 'bottom-12 sm:bottom-14'
};

const HandFanComponent: React.FC<HandFanProps> = ({

    hand,
    selectedCardIndex,
    isMyTurn,
    onCardClick,
    cardSkin = 'card_default',
    gameMode,
    trumpSuit,
    settings
}) => {
    // Memoized sort to avoid re-sorting on every render
    const sortedHand = React.useMemo(() => {
        if (!hand) return [];
        return sortHand(hand, gameMode, trumpSuit);
    }, [hand, gameMode, trumpSuit]);

    // Calculate Card Groups for Elevation (Alternating Up/Down)
    const cardGroups = React.useMemo(() => {
        let currentSuit = '';
        let groupIndex = -1;
        const groups: Record<string, number> = {};

        sortedHand.forEach((card) => {
            if (card.suit !== currentSuit) {
                groupIndex++;
                currentSuit = card.suit;
            }
            groups[card.id] = groupIndex;
        });
        return groups;
    }, [sortedHand]);

    // Validation Helper (Duplicated from Table, ideally passed down or in util)
    const isCardPlayable = (card: CardModel) => {
        // Strict validation logic is complex and state-dependent (table cards).
        // For visual interaction, we assume "Playable" unless visually disabled?
        // Actually, Table.tsx handles the actual *logic* check on click.
        // We just render.
        return true;
    };

    if (!hand || hand.length === 0) return null;

    return (
        <div className={`
            absolute bottom-2 sm:bottom-4 left-1/2 -translate-x-1/2 
            flex items-end justify-center 
            ${FAN_SPACING.base} ${FAN_SPACING.sm} ${FAN_SPACING.md} 
            z-50 perspective-1000 w-full px-4 overflow-visible pointer-events-none
        `}>
            {sortedHand.map((card, idx) => {
                // Find original index in unsorted hand to pass back to parent
                const originalIndex = hand.findIndex(c => c.id === card.id);
                const isSelected = selectedCardIndex === originalIndex;

                // Visual Grouping Logic
                const groupIdx = cardGroups[card.id] || 0;
                const isElevated = groupIdx % 2 === 0;

                // Determine Classes based on state
                const baseClass = isElevated ? ELEVATION.elevated : ELEVATION.base;
                const hoverClass = isElevated ? ELEVATION.hoverElevated : ELEVATION.hoverBase;

                return (
                    <motion.div key={`hand-${card.id}`}
                        role="button"
                        tabIndex={0}
                        aria-label={`Play ${card.rank} of ${card.suit}`}
                        initial={{ y: 200, opacity: 0, rotate: 10 }}
                        animate={{
                            y: isSelected ? -50 : 0,
                            opacity: 1,
                            rotate: 0,
                            transition: { delay: idx * 0.05, type: "spring", stiffness: 200, damping: 20 }
                        }}
                        className={`
                            relative transition-all duration-300 pointer-events-auto
                            ${isSelected
                                ? `${ELEVATION.selected} z-[60] scale-110`
                                : `${baseClass} ${hoverClass} hover:z-[55] hover:scale-105`
                            }
                            opacity-100
                        `}
                        style={{
                            transformOrigin: 'bottom center',
                            zIndex: isSelected ? 60 : 50 + (sortedHand.length - idx)
                        }}
                        onClick={() => onCardClick(originalIndex)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                                onCardClick(originalIndex);
                            }
                        }}
                    >
                        <Card
                            card={card}
                            className="w-[3.75rem] h-[5.55rem] sm:w-[4.55rem] sm:h-[6.7rem] md:w-[5.2rem] md:h-[7.9rem] shadow-2xl"
                            selected={isSelected}
                            isPlayable={true}
                            skin={cardSkin}
                        />
                    </motion.div>
                );
            })}
        </div>
    );
};

const HandFan = React.memo(HandFanComponent, (prev, next) => {
    // Custom comparison for performance
    if (prev.isMyTurn !== next.isMyTurn) return false;
    if (prev.selectedCardIndex !== next.selectedCardIndex) return false;
    if (prev.hand.length !== next.hand.length) return false;

    // Deep check card IDs if length is same (to detect played cards)
    const prevIds = prev.hand.map(c => c.id).join(',');
    const nextIds = next.hand.map(c => c.id).join(',');
    if (prevIds !== nextIds) return false;

    return true; // Props are effectively equal, skip render
});

export default HandFan;

