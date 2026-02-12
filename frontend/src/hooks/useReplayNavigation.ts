import { useState, useEffect } from 'react';

export const useReplayNavigation = (fullMatchHistory: any[]) => {
    const [selectedRoundIdx, setSelectedRoundIdx] = useState(0);
    const [selectedTrickIdx, setSelectedTrickIdx] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    const currentRound = (fullMatchHistory && fullMatchHistory.length > 0) ? fullMatchHistory[selectedRoundIdx] : { roundNumber: 0, tricks: [], bid: {}, scores: {} };
    const tricks = currentRound?.tricks || [];
    const currentTrick = tricks[selectedTrickIdx];

    // Auto-Play Logic
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isPlaying) {
            interval = setInterval(() => {
                if (selectedTrickIdx < tricks.length - 1) {
                    setSelectedTrickIdx(prev => prev + 1);
                } else {
                    setIsPlaying(false); // Stop at end of round
                }
            }, 1500); // 1.5s per trick
        }
        return () => clearInterval(interval);
    }, [isPlaying, selectedTrickIdx, tricks.length]);

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
