import { useCallback, useEffect, useRef } from 'react';
import { GameState, GamePhase } from '../types';
import { soundManager } from '../services/SoundManager';
import { ToastType } from './useGameToast';

type AddToastFn = (message: string, type: ToastType, icon: string) => void;

interface UseGameAudioReturn {
    speakAction: (text: string) => void;
    playCardSound: () => void;
    playWinSound: () => void;
    playAkkaSound: () => void;
    playErrorSound: () => void;
}

/**
 * useGameAudio - Manages all audio/sound effects AND toast notifications
 *
 * Responsibilities:
 * - Text-to-speech for actions
 * - Sound effects (card play, trick win, akka, errors)
 * - Auto-playing sounds + toasts based on game state changes
 */
export const useGameAudio = (gameState: GameState, addToast?: AddToastFn): UseGameAudioReturn => {
    // Track previous state to detect changes
    const prevPhaseRef = useRef<GamePhase | null>(null);
    const prevTableLengthRef = useRef<number>(0);
    const prevAkkaRef = useRef<any>(null);
    const prevTurnRef = useRef<number>(-1);
    const prevSawaRef = useRef<boolean>(false);
    const prevProjectRevealRef = useRef<boolean>(false);

    // Cancel any in-progress speech synthesis on unmount
    useEffect(() => {
        return () => {
            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
        };
    }, []);

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
     * Auto-play sounds + toasts based on game state changes
     */

    // 1. YOUR TURN detection (human player = index 0)
    useEffect(() => {
        const currentTurn = gameState.currentTurnIndex;
        const isMyTurn = currentTurn === 0;
        const wasMyTurn = prevTurnRef.current === 0;

        if (isMyTurn && !wasMyTurn && gameState.phase === GamePhase.Playing) {
            soundManager.playTurnSound();
            addToast?.('دورك — العب ورقة', 'turn', '🎯');
        }

        prevTurnRef.current = currentTurn;
    }, [gameState.currentTurnIndex, gameState.phase, addToast]);

    // 2. Trick completion (when all 4 cards played → table clears)
    useEffect(() => {
        const currentTableLength = gameState.tableCards?.length || 0;

        if (prevTableLengthRef.current === 4 && currentTableLength === 0) {
            playWinSound();

            // Determine trick winner from lastTrick
            const winner = gameState.lastTrick?.winner;
            if (winner) {
                const isMyTeam = winner === 'Bottom' || winner === 'Top';
                addToast?.(
                    isMyTeam ? `${winner} أخذ اللّمّة ✨` : `${winner} أخذ اللّمّة`,
                    'trick',
                    isMyTeam ? '✨' : '📥'
                );
            }
        }

        prevTableLengthRef.current = currentTableLength;
    }, [gameState.tableCards, gameState.lastTrick, playWinSound, addToast]);

    // 3. Akka declared
    useEffect(() => {
        const akka = gameState.akkaState;
        if (akka && akka.claimer && !prevAkkaRef.current?.claimer) {
            playAkkaSound();
            const suits = akka.suits?.join(' ') || '';
            addToast?.(`${akka.claimer} أعلن أكّة ${suits}`, 'akka', '👑');
        }

        prevAkkaRef.current = akka;
    }, [gameState.akkaState, playAkkaSound, addToast]);

    // 4. Sawa claimed
    useEffect(() => {
        const sawaActive = gameState.sawaState?.active || false;

        if (sawaActive && !prevSawaRef.current) {
            const claimer = gameState.sawaState?.claimer || '';
            addToast?.(`${claimer} طلب سوا!`, 'sawa', '🏆');
        }

        prevSawaRef.current = sawaActive;
    }, [gameState.sawaState, addToast]);

    // 5. Project reveal
    useEffect(() => {
        const isRevealing = gameState.isProjectRevealing || false;

        if (isRevealing && !prevProjectRevealRef.current) {
            addToast?.('مشاريع!', 'project', '📜');
        }

        prevProjectRevealRef.current = isRevealing;
    }, [gameState.isProjectRevealing, addToast]);

    // 6. Phase transitions
    useEffect(() => {
        if (prevPhaseRef.current !== null && prevPhaseRef.current !== gameState.phase) {
            if (gameState.phase === GamePhase.Playing && prevPhaseRef.current !== GamePhase.Playing) {
                addToast?.('بداية اللعب', 'info', '🃏');
            }
        }

        prevPhaseRef.current = gameState.phase;
    }, [gameState.phase, addToast]);

    return {
        speakAction,
        playCardSound,
        playWinSound,
        playAkkaSound,
        playErrorSound
    };
};
