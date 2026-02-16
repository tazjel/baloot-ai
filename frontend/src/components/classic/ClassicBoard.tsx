import React, { useEffect, useState, useRef } from 'react';
import { GameState, GamePhase, Suit } from '../../types';
import { useBotSpeech } from '../../hooks/useBotSpeech';
import { useGameTension } from '../../hooks/useGameTension';
import { useGameToast } from '../../hooks/useGameToast';
import { useGameRules } from '../../hooks/useGameRules';
import { canDeclareAkka, sortHand } from '../../utils/gameLogic';
import { soundManager } from '../../services/SoundManager';
import { devLogger } from '../../utils/devLogger';
import GameToast from '../GameToast';

import ClassicArena from './ClassicArena';
import ClassicHandFan from './ClassicHandFan';
import ClassicActionDock from './ClassicActionDock';
import ClassicSidebar from './ClassicSidebar';
import './classic.css';

// Uses the same interface as Table.tsx for drop-in swap
interface ClassicBoardProps {
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

export default function ClassicBoard({
    gameState,
    onPlayerAction,
    onChallenge,
    onAddBot,
    onDebugAction,
    isCuttingDeck = false,
    tableSkin = 'table_classic',
    cardSkin = 'card_default',
    onFastForward,
    onEmoteClick,
    isSendingAction = false,
    isPaused = false
}: ClassicBoardProps) {
    // --- HOOKS (identical to Table.tsx) ---
    const { players = [], currentTurnIndex = 0, phase, tableCards = [], floorCard, bid, settings, declarations, matchScores = { us: 0, them: 0 }, sawaState, isProjectRevealing, akkaState } = gameState || {};

    const playerSpeech = useBotSpeech(players);
    const { toasts, addToast, dismissToast } = useGameToast();
    const { tension, bpm } = useGameTension(gameState);

    const prevTurnRef = useRef<number>(-1);
    const prevAkkaRef = useRef<any>(null);
    const prevSawaRef = useRef<boolean>(false);
    const prevTableLenRef = useRef<number>(0);
    const prevProjectRef = useRef<boolean>(false);

    // ═══ EVENT DETECTION → TOASTS ═══
    useEffect(() => {
        const isMyTurn = currentTurnIndex === 0;
        const wasMyTurn = prevTurnRef.current === 0;
        if (isMyTurn && !wasMyTurn && phase === GamePhase.Playing) {
            soundManager.playTurnSound();
            addToast('دورك — العب ورقة', 'turn', '🎯');
        }
        prevTurnRef.current = currentTurnIndex;
    }, [currentTurnIndex, phase, addToast]);

    useEffect(() => {
        if (akkaState && akkaState.claimer && !prevAkkaRef.current?.claimer) {
            const suits = akkaState.suits?.join(' ') || '';
            addToast(`${akkaState.claimer} أعلن أكّة ${suits}`, 'akka', '👑');
        }
        prevAkkaRef.current = akkaState;
    }, [akkaState, addToast]);

    useEffect(() => {
        const active = sawaState?.active || false;
        if (active && !prevSawaRef.current) {
            addToast(`${sawaState?.claimer || ''} طلب سوا!`, 'sawa', '🏆');
        }
        prevSawaRef.current = active;
    }, [sawaState, addToast]);

    useEffect(() => {
        const len = tableCards?.length || 0;
        if (prevTableLenRef.current === 4 && len === 0 && gameState.lastTrick?.winner) {
            const w = gameState.lastTrick.winner;
            const mine = w === 'Bottom' || w === 'Top';
            addToast(mine ? `${w} أخذ اللّمّة ✨` : `${w} أخذ اللّمّة`, 'trick', mine ? '✨' : '📥');
        }
        prevTableLenRef.current = len;
    }, [tableCards, gameState.lastTrick, addToast]);

    useEffect(() => {
        prevProjectRef.current = isProjectRevealing || false;
    }, [isProjectRevealing]);

    // --- Timer + Selection State ---
    const turnDuration = settings?.turnDuration || 10;
    const [timeLeft, setTimeLeft] = useState(turnDuration);
    const [selectedCardIndex, setSelectedCardIndex] = useState<number | null>(null);

    useEffect(() => {
        devLogger.log('CLASSIC', 'ClassicBoard Mounted', { phase: gameState?.phase });
        return () => { devLogger.log('CLASSIC', 'ClassicBoard Unmounted'); };
    }, []);

    useEffect(() => {
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
    const { availableProjects, isCardPlayable, sortedHand } = useGameRules(gameState, me);

    const trickCount = gameState.trickCount ?? 0;
    const hasDeclarations = Object.keys(declarations).length > 0;
    const showProjects = hasDeclarations && trickCount < 2;

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

    // --- LOADING CHECK ---
    if (!gameState || !gameState.players || gameState.players.length < 4 || !me) {
        return (
            <div className="classic-board" style={{ alignItems: 'center', justifyContent: 'center' }}>
                <div className="km-waiting">
                    <h2>Loading...</h2>
                </div>
            </div>
        );
    }

    const isMyTurn = currentTurnIndex === me.index;

    // --- EVENT HANDLERS ---
    const handleCardClick = (idx: number) => {
        devLogger.log('CLASSIC', 'Card Clicked', { idx, phase, isMyTurn });

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
        }
    };

    const handleSawaResponse = (response: 'ACCEPT' | 'REFUSE') => {
        onPlayerAction('SAWA_RESPONSE', { response });
    };

    // --- RENDER ---
    return (
        <div className="classic-board">
            {/* Carpet Background */}
            <div className="classic-carpet" style={{
                background: `
                    radial-gradient(ellipse at 30% 50%, rgba(139, 69, 19, 0.15) 0%, transparent 50%),
                    radial-gradient(ellipse at 70% 30%, rgba(120, 50, 20, 0.1) 0%, transparent 40%),
                    repeating-conic-gradient(from 0deg at 50% 50%, rgba(139, 69, 19, 0.03) 0deg, rgba(160, 82, 45, 0.02) 3deg, rgba(139, 69, 19, 0.04) 6deg),
                    linear-gradient(135deg, #1a0f0a 0%, #2d1810 25%, #3d2015 50%, #2d1810 75%, #1a0f0a 100%)
                `
            }}>
                {/* Decorative border pattern */}
                <div style={{
                    position: 'absolute',
                    inset: 16,
                    border: '2px solid rgba(212, 168, 83, 0.12)',
                    borderRadius: 20,
                    pointerEvents: 'none'
                }} />
                <div style={{
                    position: 'absolute',
                    inset: 24,
                    border: '1px solid rgba(212, 168, 83, 0.06)',
                    borderRadius: 16,
                    pointerEvents: 'none'
                }} />
            </div>

            {/* Toast Notifications */}
            <GameToast toasts={toasts} onDismiss={dismissToast} />

            {/* Main Arena */}
            <ClassicArena
                gameState={gameState}
                players={players}
                me={me}
                currentTurnIndex={currentTurnIndex}
                tableCards={tableCards}
                floorCard={floorCard || null}
                bid={bid}
                declarations={declarations}
                akkaState={akkaState}
                cardSkin={cardSkin}
                dealPhase={dealPhase}
                timeLeft={timeLeft}
                turnDuration={turnDuration}
                showProjects={showProjects}
                isProjectRevealing={gameState.isProjectRevealing || false}
                trickCount={gameState.trickCount ?? 0}
                playerSpeech={playerSpeech}
                onAddBot={onAddBot}
                isPaused={isPaused}
            />

            {/* Bottom Player Avatar */}
            {me && (
                <div className="km-player-bottom">
                    <div className={`km-avatar-ring ${isMyTurn ? 'active' : ''}`}>
                        <img src={me.avatar} alt={me.name} onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                        }} />
                    </div>
                    <div>
                        <div className="km-avatar-name" style={{ textAlign: 'right' }}>{me.name}</div>
                        <div className="km-avatar-coins">🃏 {me.score || 0}</div>
                    </div>
                </div>
            )}

            {/* Hand Fan */}
            {me && me.hand && (
                <div style={{
                    position: 'relative',
                    ...(isMyTurn && phase === GamePhase.Playing ? {
                        filter: 'drop-shadow(0 0 8px rgba(212, 168, 83, 0.2))'
                    } : {})
                }}>
                    <ClassicHandFan
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

            {/* Action Dock */}
            <ClassicActionDock
                gameState={gameState}
                me={me}
                isMyTurn={isMyTurn}
                onPlayerAction={onPlayerAction}
                availableProjects={availableProjects}
                selectedCardIndex={selectedCardIndex}
                settings={settings}
                onEmoteClick={onEmoteClick}
            />

            {/* Sidebar */}
            <ClassicSidebar
                gameState={gameState}
                matchScores={matchScores}
            />

            {/* Dealer Badge */}
            {me.isDealer && (
                <div style={{
                    position: 'absolute',
                    top: 12,
                    right: 316,
                    background: 'var(--km-bg-panel)',
                    border: '1px solid var(--km-border-active)',
                    padding: '4px 12px',
                    borderRadius: 16,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    fontSize: 12,
                    fontWeight: 700,
                    color: 'var(--km-gold)',
                    zIndex: 60
                }}>
                    <div style={{
                        width: 18, height: 18,
                        background: 'var(--km-gold)',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 800,
                        fontSize: 10,
                        color: 'var(--km-bg-primary)'
                    }}>D</div>
                    أنت الموزع
                </div>
            )}

            {/* Sending Indicator */}
            {isSendingAction && (
                <div style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'rgba(0,0,0,0.3)',
                    zIndex: 1000,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none'
                }}>
                    <div style={{
                        background: 'var(--km-bg-panel)',
                        border: '1px solid var(--km-border)',
                        padding: '12px 24px',
                        borderRadius: 20,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        color: 'var(--km-gold)'
                    }}>
                        <div style={{
                            width: 16, height: 16,
                            border: '3px solid var(--km-gold)',
                            borderTopColor: 'transparent',
                            borderRadius: '50%',
                            animation: 'spin 0.8s linear infinite'
                        }} />
                        جاري الإرسال...
                    </div>
                </div>
            )}
        </div>
    );
}
