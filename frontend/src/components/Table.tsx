import React, { useEffect, useState, useMemo, useRef } from 'react';
import { GameState, Player, PlayerPosition, GamePhase, Suit } from '../types';

import { useBotSpeech } from '../hooks/useBotSpeech';
import { useGameTension } from '../hooks/useGameTension';
import { useGameToast } from '../hooks/useGameToast';
import { canDeclareAkka, sortHand } from '../utils/gameLogic';
import { soundManager } from '../services/SoundManager';
import ActionBar from './ActionBar';
import GameToast from './GameToast';

import HandFan from './HandFan';

// Modular sub-components
import { useGameRules } from '../hooks/useGameRules';
import PlayerAvatar from './table/PlayerAvatar';
import GameArena from './table/GameArena';
import TableHUD from './table/TableHUD';
import { devLogger } from '../utils/devLogger';


interface TableProps {
    gameState: GameState;
    onPlayerAction: (action: string, payload?: any) => void;
    onDebugAction?: (action: string, payload?: any) => void;
    onChallenge?: () => void;
    onAddBot?: () => void;
    isCuttingDeck?: boolean;
    tableSkin?: string;
    cardSkin?: string;
    onFastForward?: () => void;
    onEmoteClick?: () => void;
    isSendingAction?: boolean;
    isPaused?: boolean;
}



export default function Table({
    gameState,
    onPlayerAction,
    onChallenge,
    onAddBot,
    onDebugAction,
    isCuttingDeck = false,
    tableSkin = 'table_default',
    cardSkin = 'card_default',
    onFastForward,
    onEmoteClick,
    isSendingAction = false,
    isPaused = false
}: TableProps) {
    // --- HOOKS ---
    const { players = [], currentTurnIndex = 0, phase, tableCards = [], floorCard, bid, settings, declarations, matchScores = { us: 0, them: 0 }, sawaState, isProjectRevealing, akkaState } = gameState || {};

    // Bot Speech Hook (socket listener + voice synthesis)
    const playerSpeech = useBotSpeech(players);

    // Toast Notifications
    const { toasts, addToast, dismissToast } = useGameToast();

    // Refs for event detection
    const prevTurnRef = useRef<number>(-1);
    const prevAkkaRef = useRef<any>(null);
    const prevSawaRef = useRef<boolean>(false);
    const prevTableLenRef = useRef<number>(0);
    const prevProjectRef = useRef<boolean>(false);

    // Project Reveal Persistence
    const [showProjects, setShowProjects] = useState(false);
    const [showProfessor, setShowProfessor] = useState(false);

    const { tension, bpm } = useGameTension(gameState);

    // ═══ EVENT DETECTION → TOASTS ═══

    // Your Turn
    useEffect(() => {
        const isMyTurn = currentTurnIndex === 0;
        const wasMyTurn = prevTurnRef.current === 0;
        if (isMyTurn && !wasMyTurn && phase === GamePhase.Playing) {
            soundManager.playTurnSound();
            addToast('دورك — العب ورقة', 'turn', '🎯');
        }
        prevTurnRef.current = currentTurnIndex;
    }, [currentTurnIndex, phase, addToast]);

    // Akka Declared
    useEffect(() => {
        if (akkaState && akkaState.claimer && !prevAkkaRef.current?.claimer) {
            const suits = akkaState.suits?.join(' ') || '';
            addToast(`${akkaState.claimer} أعلن أكّة ${suits}`, 'akka', '👑');
        }
        prevAkkaRef.current = akkaState;
    }, [akkaState, addToast]);

    // Sawa Claimed
    useEffect(() => {
        const active = sawaState?.active || false;
        if (active && !prevSawaRef.current) {
            addToast(`${sawaState?.claimer || ''} طلب سوا!`, 'sawa', '🏆');
        }
        prevSawaRef.current = active;
    }, [sawaState, addToast]);

    // Trick Completed
    useEffect(() => {
        const len = tableCards?.length || 0;
        if (prevTableLenRef.current === 4 && len === 0 && gameState.lastTrick?.winner) {
            const w = gameState.lastTrick.winner;
            const mine = w === 'Bottom' || w === 'Top';
            addToast(mine ? `${w} أخذ اللّمّة ✨` : `${w} أخذ اللّمّة`, 'trick', mine ? '✨' : '📥');
        }
        prevTableLenRef.current = len;
    }, [tableCards, gameState.lastTrick, addToast]);

    // Project Reveal
    useEffect(() => {
        const revealing = isProjectRevealing || false;
        if (revealing && !prevProjectRef.current) {
            addToast('مشاريع!', 'project', '📜');
        }
        prevProjectRef.current = revealing;
    }, [isProjectRevealing, addToast]);

    // --- Qayd / Forensic Logic ---
    const handleAccusation = (crime: any, proof: any, type: string) => {
        devLogger.log('FORENSIC', 'Accusation Submitted', { crime, proof, type });
        onPlayerAction('QAYD_ACCUSATION', { accusation: { crime_card: crime, proof_card: proof, violation_type: type } });
    };

    const handleQaydTrigger = () => {
        devLogger.log('FORENSIC', 'Qayd Trigger Button Clicked');
        onPlayerAction('QAYD_TRIGGER');
    };

    useEffect(() => {
        if (isProjectRevealing) {
            setShowProjects(true);
        } else {
            const timer = setTimeout(() => setShowProjects(false), 3000);
            return () => clearTimeout(timer);
        }
    }, [isProjectRevealing]);



    // Sync timer with Game Settings
    const turnDuration = settings?.turnDuration || 10;
    const [timeLeft, setTimeLeft] = useState(turnDuration);
    const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
    const [selectedCardIndex, setSelectedCardIndex] = useState<number | null>(null);
    const [showProjectModal, setShowProjectModal] = useState(false);

    // Telemetry: Log Table Mount
    useEffect(() => {
        devLogger.log('TABLE', 'Table Component Mounted', { phase: gameState?.phase });
        return () => { devLogger.log('TABLE', 'Table Unmounted'); };
    }, []);

    // Reset modals and selection on turn change
    useEffect(() => {
        setShowProjectModal(false);
        setSelectedCardIndex(null);
    }, [currentTurnIndex]);

    useEffect(() => {
        setTimeLeft(turnDuration);
        const timer = setInterval(() => {
            setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
        }, 1000);
        return () => clearInterval(timer);
    }, [currentTurnIndex, turnDuration]);

    // --- Derived State ---
    const me = players[0];
    const rightPlayer = players[1];
    const partner = players[2];
    const leftPlayer = players[3];

    const { availableProjects, isCardPlayable, sortedHand } = useGameRules(gameState, me);

    const [dealPhase, setDealPhase] = useState<'IDLE' | 'DEAL_1' | 'DEAL_2' | 'FLOOR' | 'DONE'>('IDLE');

    useEffect(() => {
        if (gameState?.phase === GamePhase.Bidding && gameState?.biddingRound === 1 && dealPhase === 'IDLE' && me && me.hand.length > 0) {
            setDealPhase('DEAL_1');
            soundManager.playDealSequence();
            setTimeout(() => { setDealPhase('DEAL_2'); soundManager.playDealSequence(); }, 600);
            setTimeout(() => { setDealPhase('FLOOR'); }, 1200);
            setTimeout(() => { setDealPhase('DONE'); }, 1800);
        } else if (gameState?.phase !== GamePhase.Bidding) {
            setDealPhase('IDLE');
        }
    }, [gameState?.phase, gameState?.biddingRound, me?.hand?.length]);

    useEffect(() => {
        if (gameState?.isProjectRevealing) {
            soundManager.playProjectSound();
        }
    }, [gameState?.isProjectRevealing]);

    // --- LOADING CHECKS ---
    if (!gameState || !gameState.players || gameState.players.length < 4 || !me || !rightPlayer || !partner || !leftPlayer) {
        // @ts-ignore
        return <div className="w-full h-full flex items-center justify-center text-black">Loading Game Table...</div>;
    }

    const isMyTurn = currentTurnIndex === me.index;

    // --- EVENT HANDLERS ---
    const handleCardClick = (idx: number) => {
        devLogger.log('UI', 'Card Clicked Raw', { idx, phase, isMyTurn, currentTurnIndex });

        if (phase === GamePhase.Playing && isMyTurn) {
            if (selectedCardIndex === idx) {
                const card = me.hand[idx];
                if (isCardPlayable(card)) {
                    onPlayerAction('PLAY', { cardIndex: idx, cardId: card.id });
                    setSelectedCardIndex(null);
                }
            } else {
                setSelectedCardIndex(idx);
            }
        } else {
            if (selectedIndices.includes(idx)) {
                setSelectedIndices(prev => prev.filter(i => i !== idx));
            } else {
                setSelectedIndices(prev => [...prev, idx]);
            }
        }
    };

    const handleAkkaPlay = () => {
        if (selectedCardIndex !== null) {
            const card = me.hand[selectedCardIndex];
            soundManager.playAkkaSound();
            onPlayerAction('PLAY', {
                cardIndex: selectedCardIndex,
                cardId: card?.id,
                metadata: { akka: true }
            });
            setSelectedCardIndex(null);
        }
    }

    const handleProjectSelect = (projectType: string) => {
        onPlayerAction('DECLARE_PROJECT', { type: projectType });
        setShowProjectModal(false);
    };

    const handleSawaResponse = (response: 'ACCEPT' | 'REFUSE') => {
        onPlayerAction('SAWA_RESPONSE', { response });
    };

    // --- RENDER ---
    return (
        <div className="relative w-full h-full flex flex-col overflow-hidden select-none safe-area-top safe-area-bottom font-sans" style={{ background: '#F5F3EF' }}>

            {/* Toast Notifications */}
            <GameToast toasts={toasts} onDismiss={dismissToast} />

            <TableHUD
                gameState={gameState}
                players={players}
                bid={bid}
                matchScores={matchScores}
                tension={tension}
                bpm={bpm}
                onPlayerAction={onPlayerAction}
                onSawaResponse={handleSawaResponse}
            />

            {/* --- ZONE 2: ARENA (Delegated to GameArena) --- */}
            <GameArena
                gameState={gameState}
                players={players}
                me={me}
                currentTurnIndex={currentTurnIndex}
                tableCards={tableCards}
                floorCard={floorCard || null}
                bid={bid}
                declarations={declarations}

                akkaState={akkaState}
                tableSkin={tableSkin}
                cardSkin={cardSkin}
                dealPhase={dealPhase}
                timeLeft={timeLeft}
                turnDuration={turnDuration}
                showProjects={showProjects}
                isProjectRevealing={gameState.isProjectRevealing || false}
                playerSpeech={playerSpeech}
                onAddBot={onAddBot}
                isPaused={isPaused}
            />

            {/* --- ZONE 3: ACTIONS & HAND --- */}
            {me && me.hand && (
                <div className={`relative transition-all duration-500 ${
                    isMyTurn && phase === GamePhase.Playing
                        ? 'ring-2 ring-amber-400/60 ring-offset-1 ring-offset-transparent rounded-xl shadow-[0_0_20px_rgba(245,158,11,0.3)]'
                        : ''
                }`}>
                    <HandFan
                        hand={me.hand}
                        selectedCardIndex={selectedCardIndex}
                        isMyTurn={isMyTurn}
                        onCardClick={handleCardClick}
                        cardSkin={cardSkin}
                        gameMode={(gameState.gameMode as 'SUN' | 'HOKUM') || 'SUN'}
                        trumpSuit={gameState.trumpSuit}
                        settings={settings}
                    />
                </div>
            )}

            {/* Bottom Player Avatar */}
            <PlayerAvatar
                player={me}
                isCurrentTurn={isMyTurn}
                position="bottom"
                timeLeft={timeLeft}
                totalTime={turnDuration}
                declarations={declarations}
                isProjectRevealing={gameState.isProjectRevealing || false}
                bid={bid}
                doublingLevel={gameState.doublingLevel}
                showProjects={showProjects}
                speechText={playerSpeech[me.index]}
                akkaState={akkaState}
            />

            <ActionBar
                gameState={gameState}
                me={me}
                isMyTurn={isMyTurn}
                onPlayerAction={onPlayerAction}
                availableProjects={availableProjects}
                selectedCardIndex={selectedCardIndex}
                settings={settings}
                onEmoteClick={onEmoteClick}
            />

            {/* Dealer Badge */}
            {me.isDealer && (
                <div className="absolute top-4 right-4 bg-white/90 px-3 py-1 rounded-full shadow-lg border border-yellow-500 flex items-center gap-2 animate-in fade-in duration-700">
                    <div className="w-5 h-5 bg-[var(--color-premium-gold)] rounded-full flex items-center justify-center font-bold text-xs text-black">D</div>
                    <span className="text-xs font-bold text-gray-800">أنت الموزع</span>
                </div>
            )}

            {/* Sending Indicator Overlay */}
            {isSendingAction && (
                <div className="absolute inset-0 bg-black/20 z-[1000] flex items-center justify-center pointer-events-none">
                    <div className="bg-white/90 backdrop-blur text-black px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 animate-pulse">
                        <div className="w-5 h-5 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
                        <span className="font-bold">Sending...</span>
                        <button
                            onClick={() => window.location.reload()}
                            className="ml-4 text-xs underline text-red-300 hover:text-white"
                        >
                            Stuck? Reload
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};
