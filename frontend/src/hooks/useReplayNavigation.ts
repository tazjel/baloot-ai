import { useState, useEffect, useRef } from 'react';
import { MatchHistoryRound } from '../types';

export const useReplayNavigation = (fullMatchHistory: MatchHistoryRound[]) => {
    const [selectedRoundIdx, setSelectedRoundIdx] = useState(0);
    const [selectedTrickIdx, setSelectedTrickIdx] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    const currentRound = (fullMatchHistory && fullMatchHistory.length > 0) ? fullMatchHistory[selectedRoundIdx] : null;
    const tricks = currentRound?.tricks || [];
    const currentTrick = tricks[selectedTrickIdx];

    // Use ref for tricks length to avoid interval restarts on every tick
    const tricksLengthRef = useRef(tricks.length);
    useEffect(() => { tricksLengthRef.current = tricks.length; }, [tricks.length]);

    // Auto-Play Logic — stable interval, only restarts when isPlaying or tricks.length changes
    useEffect(() => {
        if (!isPlaying || tricks.length === 0) return;

        const interval = setInterval(() => {
            setSelectedTrickIdx(prev => {
                if (prev < tricksLengthRef.current - 1) {
                    return prev + 1;
                } else {
                    setIsPlaying(false);
                    return prev;
                }
            });
        }, 1500);

        return () => clearInterval(interval);
    }, [isPlaying, tricks.length]);

    const nextTrick = () => {
        if (selectedTrickIdx < tricks.length - 1) setSelectedTrickIdx(prev => prev + 1);
    };

    const prevTrick = () => {
        if (selectedTrickIdx > 0) setSelectedTrickIdx(prev => prev - 1);
    };

    const togglePlay = () => setIsPlaying(!isPlaying);

    const prevRound = () => {
        if (selectedRoundIdx > 0) {
            setSelectedRoundIdx(prev => prev - 1);
            setSelectedTrickIdx(0);
            setIsPlaying(false);
        }
    };

    const nextRound = () => {
        if (selectedRoundIdx < fullMatchHistory.length - 1) {
            setSelectedRoundIdx(prev => prev + 1);
            setSelectedTrickIdx(0);
            setIsPlaying(false);
        }
    };

    const selectRound = (idx: number) => {
        setSelectedRoundIdx(idx);
        setSelectedTrickIdx(0);
        setIsPlaying(false);
    };

    return {
        selectedRoundIdx,
        selectedTrickIdx,
        isPlaying,
        currentRound,
        tricks,
        currentTrick,
        nextTrick,
        prevTrick,
        togglePlay,
        prevRound,
        nextRound,
        selectRound
    };
};
