import React from 'react';
import { motion } from 'framer-motion';
import { CardModel, Suit } from '../../types';
import Card from '../Card';
import { sortHand } from '../../utils/gameLogic';

interface KammelnaHandFanProps {
    hand: CardModel[];
    selectedCardIndex: number | null;
    isMyTurn: boolean;
    onCardClick: (index: number) => void;
    cardSkin?: string;
    gameMode: 'SUN' | 'HOKUM';
    trumpSuit?: Suit;
    settings?: any;
}

const KammelnaHandFanComponent: React.FC<KammelnaHandFanProps> = ({
    hand,
    selectedCardIndex,
    isMyTurn,
    onCardClick,
    cardSkin = 'card_default',
    gameMode,
    trumpSuit,
    settings
}) => {
    const sortedHand = React.useMemo(() => {
        if (!hand) return [];
        return sortHand(hand, gameMode, trumpSuit);
    }, [hand, gameMode, trumpSuit]);

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

    if (!hand || hand.length === 0) return null;

    const totalCards = sortedHand.length;
    // Wider, more spread out cards for widescreen
    const cardWidth = 90; // px
    const overlap = 38; // px between cards
    const totalWidth = cardWidth + (totalCards - 1) * overlap;

    return (
        <div className="kammelna-hand" style={{ width: totalWidth, height: 140 }}>
            {sortedHand.map((card, idx) => {
                const originalIndex = hand.findIndex(c => c.id === card.id);
                const isSelected = selectedCardIndex === originalIndex;
                const groupIdx = cardGroups[card.id] || 0;
                const isElevated = groupIdx % 2 === 0;

                // Slight arc calculation for natural fan feel
                const centerOffset = idx - (totalCards - 1) / 2;
                const rotation = centerOffset * 1.5; // very subtle rotation
                const yOffset = Math.abs(centerOffset) * 2; // slight arc

                return (
                    <motion.div
                        key={`km-hand-${card.id}`}
                        role="button"
                        tabIndex={0}
                        aria-label={`Play ${card.rank} of ${card.suit}`}
                        initial={{ y: 200, opacity: 0, rotate: 10 }}
                        animate={{
                            y: isSelected ? -40 : (isElevated ? -6 : yOffset),
                            opacity: 1,
                            rotate: rotation,
                            scale: isSelected ? 1.12 : 1,
                            transition: { delay: idx * 0.04, type: "spring", stiffness: 200, damping: 20 }
                        }}
                        style={{
                            position: 'absolute',
                            left: idx * overlap,
                            bottom: 0,
                            transformOrigin: 'bottom center',
                            zIndex: isSelected ? 70 : 50 + idx,
                            cursor: 'pointer',
                            filter: isSelected ? 'drop-shadow(0 0 12px rgba(212, 168, 83, 0.6))' : 'none',
                            transition: 'filter 0.2s'
                        }}
                        whileHover={!isSelected ? {
                            y: isElevated ? -18 : yOffset - 12,
                            scale: 1.06,
                            zIndex: 65
                        } : {}}
                        onClick={() => onCardClick(originalIndex)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') onCardClick(originalIndex);
                        }}
                    >
                        <div style={{ width: cardWidth, height: cardWidth * 1.48 }}>
                            <Card
                                card={card}
                                className="shadow-2xl"
                                selected={isSelected}
                                isPlayable={true}
                                skin={cardSkin}
                            />
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
};

const KammelnaHandFan = React.memo(KammelnaHandFanComponent, (prev, next) => {
    if (prev.isMyTurn !== next.isMyTurn) return false;
    if (prev.selectedCardIndex !== next.selectedCardIndex) return false;
    if (prev.hand.length !== next.hand.length) return false;
    const prevIds = prev.hand.map(c => c.id).join(',');
    const nextIds = next.hand.map(c => c.id).join(',');
    if (prevIds !== nextIds) return false;
    return true;
});

export default KammelnaHandFan;
