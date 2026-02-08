/**
 * RapidStateStore - Zustand store for frequently changing UI state
 * 
 * Purpose: Isolate rapidly changing state (timers, animations, speech)
 * from structural game state to prevent unnecessary re-renders.
 * 
 * Performance Target: <16ms render time during animations
 * 
 * Architecture:
 * - This store updates at 60fps or higher
 * - Components subscribe ONLY to slices they need
 * - Structural state (GameState) remains in useGameState
 */

import React from 'react';
import { create } from 'zustand';

interface SpeechBubble {
    playerId: number;
    text: string;
    timestamp: number;
}

interface AnimationState {
    isTrickTransitioning: boolean;
    isProjectRevealing: boolean;
    isFastForwarding: boolean;
    isRoundTransitioning: boolean;
    isCuttingDeck: boolean;
}

interface TimerState {
    timeLeft: number;
    totalTime: number;
    isPaused: boolean;
}

interface RapidState {
    // Timer state (updates every second)
    timer: TimerState;
    
    // Animation flags (changes during trick transitions)
    animations: AnimationState;
    
    // Speech bubbles (temporary UI feedback)
    speechBubbles: SpeechBubble[];
    
    // Mouse cursors (for multiplayer - future)
    cursors: Record<number, { x: number; y: number }>;
    
    // Actions
    setTimer: (timer: Partial<TimerState>) => void;
    setAnimations: (animations: Partial<AnimationState>) => void;
    addSpeech: (playerId: number, text: string) => void;
    clearSpeech: (playerId: number) => void;
    updateCursor: (playerId: number, x: number, y: number) => void;
    reset: () => void;
}

const INITIAL_STATE = {
    timer: {
        timeLeft: 0,
        totalTime: 30,
        isPaused: false,
    },
    animations: {
        isTrickTransitioning: false,
        isProjectRevealing: false,
        isFastForwarding: false,
        isRoundTransitioning: false,
        isCuttingDeck: false,
    },
    speechBubbles: [],
    cursors: {},
};

export const useRapidStore = create<RapidState>((set) => ({
    ...INITIAL_STATE,
    
    setTimer: (timer) => set((state) => ({
        timer: { ...state.timer, ...timer }
    })),
    
    setAnimations: (animations) => set((state) => ({
        animations: { ...state.animations, ...animations }
    })),
    
    addSpeech: (playerId, text) => set((state) => ({
        speechBubbles: [
            ...state.speechBubbles.filter(s => s.playerId !== playerId),
            { playerId, text, timestamp: Date.now() }
        ]
    })),
    
    clearSpeech: (playerId) => set((state) => ({
        speechBubbles: state.speechBubbles.filter(s => s.playerId !== playerId)
    })),
    
    updateCursor: (playerId, x, y) => set((state) => ({
        cursors: { ...state.cursors, [playerId]: { x, y } }
    })),
    
    reset: () => set(INITIAL_STATE),
}));

// Selector hooks for granular subscriptions
export const useTimer = () => useRapidStore((state) => state.timer);
export const useAnimations = () => useRapidStore((state) => state.animations);
export const useSpeechBubbles = () => useRapidStore((state) => state.speechBubbles);
export const useSpeechForPlayer = (playerId: number) => 
    useRapidStore((state) => state.speechBubbles.find(s => s.playerId === playerId));

/**
 * Hook to sync timer with game state
 * Call this once in Table.tsx to bridge useGameState → RapidStore
 */
export const useTimerSync = (
    currentTurnIndex: number,
    phase: string,
    turnDuration: number,
    timerPaused: boolean
) => {
    const setTimer = useRapidStore((state) => state.setTimer);
    
    React.useEffect(() => {
        if (!turnDuration || timerPaused) return;
        
        let startTime = Date.now();
        let animationFrame: number;
        
        const tick = () => {
            const elapsed = (Date.now() - startTime) / 1000;
            const remaining = Math.max(0, turnDuration - elapsed);
            
            setTimer({ 
                timeLeft: remaining, 
                totalTime: turnDuration,
                isPaused: timerPaused
            });
            
            if (remaining > 0) {
                animationFrame = requestAnimationFrame(tick);
            }
        };
        
        tick();
        
        return () => {
            if (animationFrame) cancelAnimationFrame(animationFrame);
        };
    }, [currentTurnIndex, phase, turnDuration, timerPaused, setTimer]);
};
