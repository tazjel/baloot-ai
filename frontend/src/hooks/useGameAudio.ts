import { useCallback, useEffect, useRef } from 'react';
import { GameState, GamePhase } from '../types';
import { soundManager } from '../services/SoundManager';

interface UseGameAudioReturn {
    speakAction: (text: string) => void;
    playCardSound: () => void;
    playWinSound: () => void;
    playAkkaSound: () => void;
    playErrorSound: () => void;
}

/**
 * useGameAudio - Manages all audio/sound effects in the game
 * 
 * Responsibilities:
 * - Text-to-speech for actions
 * - Sound effects (card play, trick win, akka, errors)
 * - Auto-playing sounds based on game state changes
 */
export const useGameAudio = (gameState: GameState): UseGameAudioReturn => {
    // Track previous state to detect changes
    const prevPhaseRef = useRef<GamePhase | null>(null);
    const prevTableLengthRef = useRef<number>(0);
    const prevAkkaStateRef = useRef<any>(null);

    /**
     * Text-to-speech for bidding actions
     */
    const speakAction = useCallback((text: string) => {
        if (!window.speechSynthesis) return;
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.volume = 1;
        utterance.rate = 1;
        window.speechSynthesis.speak(utterance);
    }, []);

    /**
     * Wrapper functions for sound effects
     */
    const playCardSound = useCallback(() => {
        soundManager.playCardSound();
    }, []);

    const playWinSound = useCallback(() => {
        soundManager.playWinSound();
    }, []);

    const playAkkaSound = useCallback(() => {
        soundManager.playAkkaSound();
    }, []);

    const playErrorSound = useCallback(() => {
        soundManager.playErrorSound();
    }, []);

    /**
     * Auto-play sounds based on game state changes
     */
    
    // 1. Trick completion sound (when all 4 cards played)
    useEffect(() => {
        const currentTableLength = gameState.tableCards?.length || 0;
        
        // Detect trick completion (0 → 1-3 → 4 → 0)
        if (prevTableLengthRef.current === 4 && currentTableLength === 0) {
            // Trick was just cleared (winner determined)
            playWinSound();
        }
        
        prevTableLengthRef.current = currentTableLength;
    }, [gameState.tableCards, playWinSound]);

    // 2. Akka sound (when akka state changes)
    useEffect(() => {
        if (gameState.akkaState && gameState.akkaState !== prevAkkaStateRef.current) {
            // New akka claim detected
            playAkkaSound();
        }
        
        prevAkkaStateRef.current = gameState.akkaState;
    }, [gameState.akkaState, playAkkaSound]);

    // 3. Phase transition sounds (optional - can add round start, game over, etc.)
    useEffect(() => {
        if (prevPhaseRef.current !== null && prevPhaseRef.current !== gameState.phase) {
            // Phase changed - could add specific sounds here
            // e.g., if (gameState.phase === GamePhase.Playing) playRoundStartSound();
        }
        
        prevPhaseRef.current = gameState.phase;
    }, [gameState.phase]);

    return {
        speakAction,
        playCardSound,
        playWinSound,
        playAkkaSound,
        playErrorSound
    };
};
