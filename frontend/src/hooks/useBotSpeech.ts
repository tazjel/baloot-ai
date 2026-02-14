import { useState, useEffect, useRef, useCallback } from 'react';
import { Player } from '../types';
import { useVoice, VoicePersonality } from './useVoice';
import socketService from '../services/SocketService';

// Helper to map player avatar to voice personality
const getPersonality = (player: Player): VoicePersonality => {
    if (!player.avatar) return 'BALANCED';
    if (player.avatar.includes('khalid')) return 'AGRESSIVE';
    if (player.avatar.includes('abu_fahad')) return 'CONSERVATIVE';
    if (player.avatar.includes('saad')) return 'BALANCED';
    return 'BALANCED';
};

/**
 * Hook to manage bot speech bubbles and voice synthesis.
 * Listens to `bot_speak` socket events and manages speech state per player.
 *
 * @param players - Current player list (used for avatar → voice personality mapping)
 * @returns `playerSpeech` — record mapping player index to their current speech text (or null)
 */
export function useBotSpeech(players: Player[]) {
    const { speak } = useVoice();
    const [playerSpeech, setPlayerSpeech] = useState<Record<number, string | null>>({});

    // Ref for stable access in the socket listener (avoids re-subscribing on every players change)
    const playersRef = useRef(players);
    useEffect(() => { playersRef.current = players; }, [players]);

    // Track active speech timers per player to cancel overlapping timeouts
    const speechTimersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());
    const isMountedRef = useRef(true);

    // Cleanup all timers on unmount + set mounted flag
    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
            speechTimersRef.current.forEach(t => clearTimeout(t));
            speechTimersRef.current.clear();
        };
    }, []);

    useEffect(() => {
        const cleanup = socketService.onBotSpeak((data) => {
            if (!isMountedRef.current) return; // Guard against unmount race
            const { playerIndex, text, emotion } = data;
            setPlayerSpeech(prev => ({ ...prev, [playerIndex]: text }));

            const currentPlayers = playersRef.current;
            const player = currentPlayers.find(p => p.index === playerIndex);
            const personality = player ? getPersonality(player) : 'BALANCED';
            speak(text, personality);

            // Cancel previous timer for this player (prevents overlapping clears)
            const prevTimer = speechTimersRef.current.get(playerIndex);
            if (prevTimer) clearTimeout(prevTimer);

            const timer = setTimeout(() => {
                if (!isMountedRef.current) return; // Guard against unmount race
                speechTimersRef.current.delete(playerIndex);
                setPlayerSpeech(prev => {
                    const newState = { ...prev };
                    if (newState[playerIndex] === text) {
                        newState[playerIndex] = null;
                    }
                    return newState;
                });
            }, 5000);
            speechTimersRef.current.set(playerIndex, timer);
        });

        return () => {
            if (cleanup) cleanup();
        };
    }, [speak]);

    return playerSpeech;
}
