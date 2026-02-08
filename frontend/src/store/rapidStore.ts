/**
 * Rapid State Store - Zustand
 * ============================
 * 
 * Isolates frequently-changing UI state from the main React tree.
 * 
 * Mission 4: Speed Demon Performance Optimization
 * 
 * Purpose:
 * - Store rapid-update state (timers, cursors, animations)
 * - Bypass React re-render cascade
 * - Enable selective subscriptions (components only re-render on their slice)
 * 
 * State Categories:
 * 1. Timers: Turn timers, animation timers
 * 2. Cursors: Mouse positions, hover states
 * 3. Animations: Deal phase, trick transitions
 * 4. Transient UI: Speech bubbles, tooltips
 * 
 * Performance Goal: <16ms render time during animations
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import React from 'react';

// ═══════════════════════════════════════════════════════════════════════════
//  TYPE DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════

interface TimerState {
    currentTurnIndex: number;
    timeLeft: number;          // Seconds remaining
    totalTime: number;         // Total turn duration
    timerPaused: boolean;
}

interface CursorState {
    hoveredCardIndex: number | null;
    hoveredPlayerIndex: number | null;
    mouseX: number;
    mouseY: number;
}

interface AnimationState {
    dealPhase: 'IDLE' | 'DEAL_1' | 'DEAL_2' | 'FLOOR' | 'DONE';
    isTrickAnimating: boolean;
    isProjectRevealing: boolean;
    isCuttingDeck: boolean;
}

interface TransientUIState {
    playerSpeech: Record<number, string | null>;  // playerIndex -> speech text
    tooltipText: string | null;
    tooltipPosition: { x: number; y: number } | null;
}

interface RapidState extends TimerState, CursorState, AnimationState, TransientUIState {
    // Actions
    setTimer: (turnIndex: number, timeLeft: number, totalTime: number) => void;
    tickTimer: () => void;
    pauseTimer: () => void;
    resumeTimer: () => void;
    
    setCursor: (x: number, y: number) => void;
    setHoveredCard: (index: number | null) => void;
    setHoveredPlayer: (index: number | null) => void;
    
    setDealPhase: (phase: AnimationState['dealPhase']) => void;
    setTrickAnimating: (animating: boolean) => void;
    setProjectRevealing: (revealing: boolean) => void;
    setCuttingDeck: (cutting: boolean) => void;
    
    setPlayerSpeech: (playerIndex: number, text: string | null) => void;
    clearPlayerSpeech: (playerIndex: number) => void;
    setTooltip: (text: string | null, position?: { x: number; y: number }) => void;
    
    reset: () => void;
}

// ═══════════════════════════════════════════════════════════════════════════
//  INITIAL STATE
// ═══════════════════════════════════════════════════════════════════════════

const initialState = {
    // Timers
    currentTurnIndex: 0,
    timeLeft: 30,
    totalTime: 30,
    timerPaused: false,
    
    // Cursors
    hoveredCardIndex: null,
    hoveredPlayerIndex: null,
    mouseX: 0,
    mouseY: 0,
    
    // Animations
    dealPhase: 'IDLE' as const,
    isTrickAnimating: false,
    isProjectRevealing: false,
    isCuttingDeck: false,
    
    // Transient UI
    playerSpeech: {},
    tooltipText: null,
    tooltipPosition: null,
};

// ═══════════════════════════════════════════════════════════════════════════
//  STORE CREATION
// ═══════════════════════════════════════════════════════════════════════════

export const useRapidStore = create<RapidState>()(
    subscribeWithSelector((set, get) => ({
        ...initialState,
        
        // ═══ TIMER ACTIONS ═══
        setTimer: (turnIndex, timeLeft, totalTime) => set({
            currentTurnIndex: turnIndex,
            timeLeft,
            totalTime,
        }),
        
        tickTimer: () => set((state) => {
            if (state.timerPaused || state.timeLeft <= 0) return {};
            return { timeLeft: state.timeLeft - 1 };
        }),
        
        pauseTimer: () => set({ timerPaused: true }),
        
        resumeTimer: () => set({ timerPaused: false }),
        
        // ═══ CURSOR ACTIONS ═══
        setCursor: (x, y) => set({ mouseX: x, mouseY: y }),
        
        setHoveredCard: (index) => set({ hoveredCardIndex: index }),
        
        setHoveredPlayer: (index) => set({ hoveredPlayerIndex: index }),
        
        // ═══ ANIMATION ACTIONS ═══
        setDealPhase: (phase) => set({ dealPhase: phase }),
        
        setTrickAnimating: (animating) => set({ isTrickAnimating: animating }),
        
        setProjectRevealing: (revealing) => set({ isProjectRevealing: revealing }),
        
        setCuttingDeck: (cutting) => set({ isCuttingDeck: cutting }),
        
        // ═══ TRANSIENT UI ACTIONS ═══
        setPlayerSpeech: (playerIndex, text) => set((state) => ({
            playerSpeech: { ...state.playerSpeech, [playerIndex]: text }
        })),
        
        clearPlayerSpeech: (playerIndex) => set((state) => {
            const newSpeech = { ...state.playerSpeech };
            delete newSpeech[playerIndex];
            return { playerSpeech: newSpeech };
        }),
        
        setTooltip: (text, position) => set({
            tooltipText: text,
            tooltipPosition: position || null
        }),
        
        // ═══ RESET ═══
        reset: () => set(initialState),
    }))
);

// ═══════════════════════════════════════════════════════════════════════════
//  SELECTIVE HOOKS (Performance Optimization)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Use only timer state - components using this won't re-render on cursor/animation changes
 */
export const useTimerState = () => useRapidStore((state) => ({
    timeLeft: state.timeLeft,
    totalTime: state.totalTime,
    currentTurnIndex: state.currentTurnIndex,
    timerPaused: state.timerPaused,
}));

/**
 * Use only cursor state - won't re-render on timer/animation changes
 */
export const useCursorState = () => useRapidStore((state) => ({
    hoveredCardIndex: state.hoveredCardIndex,
    hoveredPlayerIndex: state.hoveredPlayerIndex,
    mouseX: state.mouseX,
    mouseY: state.mouseY,
}));

/**
 * Use only animation state - won't re-render on timer/cursor changes
 */
export const useAnimationState = () => useRapidStore((state) => ({
    dealPhase: state.dealPhase,
    isTrickAnimating: state.isTrickAnimating,
    isProjectRevealing: state.isProjectRevealing,
    isCuttingDeck: state.isCuttingDeck,
}));

/**
 * Use only speech for a specific player - won't re-render on other players' speech
 */
export const usePlayerSpeech = (playerIndex: number) => 
    useRapidStore((state) => state.playerSpeech[playerIndex] || null);

/**
 * Use tooltip state only
 */
export const useTooltipState = () => useRapidStore((state) => ({
    text: state.tooltipText,
    position: state.tooltipPosition,
}));

// ═══════════════════════════════════════════════════════════════════════════
//  TIMER SYNC HOOK (Integrates with main game state)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Hook to sync rapid store timer with game state
 * Call this in Table.tsx to keep stores in sync
 */
export const useTimerSync = (
    currentTurnIndex: number,
    turnDuration: number,
    isPaused: boolean
) => {
    const setTimer = useRapidStore((state) => state.setTimer);
    const pauseTimer = useRapidStore((state) => state.pauseTimer);
    const resumeTimer = useRapidStore((state) => state.resumeTimer);
    const tickTimer = useRapidStore((state) => state.tickTimer);
    
    // Sync on turn change
    React.useEffect(() => {
        setTimer(currentTurnIndex, turnDuration, turnDuration);
    }, [currentTurnIndex, turnDuration, setTimer]);
    
    // Sync pause state
    React.useEffect(() => {
        if (isPaused) {
            pauseTimer();
        } else {
            resumeTimer();
        }
    }, [isPaused, pauseTimer, resumeTimer]);
    
    // Timer tick (1 second interval)
    React.useEffect(() => {
        const interval = setInterval(() => {
            tickTimer();
        }, 1000);
        
        return () => clearInterval(interval);
    }, [tickTimer]);
};

// ═══════════════════════════════════════════════════════════════════════════
//  DEVTOOLS INTEGRATION
// ═══════════════════════════════════════════════════════════════════════════

if (process.env.NODE_ENV === 'development') {
    // @ts-ignore - Zustand devtools
    useRapidStore.subscribe((state) => {
        // Log rapid state changes for debugging
        if (typeof window !== 'undefined' && (window as any).__RAPID_STATE_DEBUG__) {
            console.log('[RapidStore]', state);
        }
    });
}

export default useRapidStore;
