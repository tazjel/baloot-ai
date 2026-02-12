import { useState } from 'react';
import { GameState } from '../types';
import { soundManager } from '../services/SoundManager';

export const useEmotes = (gameState: GameState, addSystemMessage: (msg: string) => void) => {
    const [isEmoteMenuOpen, setIsEmoteMenuOpen] = useState(false);
    const [flyingItems, setFlyingItems] = useState<{ id: string, type: string, startX: number, startY: number, endX: number, endY: number }[]>([]);

    const handleSendEmote = (msg: string) => {
        addSystemMessage(`أنا: ${msg} `);
        setIsEmoteMenuOpen(false);
    };

    const handleThrowItem = (itemId: string) => {
        setIsEmoteMenuOpen(false);
        // Target logic: 0=Me, 1=Right, 2=Top, 3=Left (relative to view)
        // currentTurnIndex is rotated in hook, so it matches visual position relative to "Me" at 0.
        const targetIdx = gameState.currentTurnIndex === 0 ? 3 : gameState.currentTurnIndex;
        let endX = 50, endY = 50;
        switch (targetIdx) {
            case 1: endX = 85; endY = 50; break;
            case 2: endX = 50; endY = 15; break;
            case 3: endX = 15; endY = 50; break;
        }
        const newItem = { id: Date.now().toString(), type: itemId, startX: 50, startY: 90, endX, endY };
        setFlyingItems(prev => [...prev, newItem]);
        soundManager.playShuffleSound();
        setTimeout(() => setFlyingItems(prev => prev.filter(i => i.id !== newItem.id)), 1000);
    };

    const toggleEmoteMenu = () => setIsEmoteMenuOpen(prev => !prev);

    return {
        isEmoteMenuOpen,
        setIsEmoteMenuOpen,
        flyingItems,
        handleSendEmote,
        handleThrowItem,
        toggleEmoteMenu
    };
};
