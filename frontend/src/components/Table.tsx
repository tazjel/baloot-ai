import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GameState, Player, PlayerPosition, GamePhase, Suit } from '../types';
import CardVector from './CardVector';
import { TriangleAlert, ShieldAlert, Pause, Menu, Plus, Megaphone, Eye, EyeOff, LineChart as ChartIcon, Gavel } from 'lucide-react';
import { ProfessorOverlay } from './overlays/ProfessorOverlay';
import { ForensicOverlay } from './overlays/ForensicOverlay';
import { QaydOverlay } from './overlays/QaydOverlay';
import { useGameTension } from '../hooks/useGameTension';
import { HeartbeatLayer } from './effects/HeartbeatLayer';
import ProjectSelectionModal from './ProjectSelectionModal';
import { canDeclareAkka, sortHand } from '../utils/gameLogic';
import { VISUAL_ASSETS } from '../constants';
import premiumWood from '../assets/premium_wood_texture.png';
import premiumFelt from '../assets/premium_felt_texture.png';
import royalBack from '../assets/royal_card_back.png';
import { soundManager } from '../services/SoundManager';
import SawaModal from './SawaModal';
import ActionBar from './ActionBar';
import GablakTimer from './GablakTimer';
import { DevLogSidebar } from './DevLogSidebar';
import { useVoice, VoicePersonality } from '../hooks/useVoice';
import socketService from '../services/SocketService';
import HandFan from './HandFan';
import { getPlayedCardAnimation } from '../utils/animationUtils';

// Imported modular components
import { useGameRules } from '../hooks/useGameRules';
import PlayerAvatar from './table/PlayerAvatar';
import ScoreBadge from './table/ScoreBadge';
import ContractIndicator from './table/ContractIndicator';
import { DirectorOverlay } from './DirectorOverlay'; // Commissioner
import TurnTimer from './table/TurnTimer';
import MindMapOverlay from './overlays/MindMapOverlay';

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
    // Mind Map Props (Lifted)
    showMindMap?: boolean;
    setShowMindMap?: (show: boolean) => void;
}

// Helper to map name/avatar to personality
const getPersonality = (player: Player): VoicePersonality => {
    if (!player.avatar) return 'BALANCED';
    if (player.avatar.includes('khalid')) return 'AGRESSIVE';
    if (player.avatar.includes('abu_fahad')) return 'CONSERVATIVE';
    if (player.avatar.includes('saad')) return 'BALANCED';
    return 'BALANCED';
};

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
    isPaused = false,
    showMindMap: propShowMindMap,
    setShowMindMap: propSetShowMindMap
}: TableProps) {
    // --- HOOKS ---
    const { players = [], currentTurnIndex = 0, phase, tableCards = [], floorCard, bid, settings, declarations, matchScores = { us: 0, them: 0 }, sawaState, isProjectRevealing, akkaState } = gameState || {};

    // Voice Hook
    const { speak } = useVoice();
    const [playerSpeech, setPlayerSpeech] = useState<Record<number, string | null>>({});

    // Accessibility Mode
    const [isAccessibilityMode, setIsAccessibilityMode] = useState(false);

    // Project Reveal Persistence
    const [showProjects, setShowProjects] = useState(false);
    const [showProfessor, setShowProfessor] = useState(false);

    const [showDirector, setShowDirector] = useState(false); // Commissioner

    // Use Prop if available, else local state (fallback)
    const [localShowMindMap, setLocalShowMindMap] = useState(false);
    const showMindMap = propShowMindMap !== undefined ? propShowMindMap : localShowMindMap;
    const setShowMindMap = propSetShowMindMap || setLocalShowMindMap;

    const { tension, bpm } = useGameTension(gameState);

    // --- Qayd / Forensic Logic ---
    const handleAccusation = (crime: any, proof: any, type: string) => {
        console.log('[Table] detailed: handleAccusation called', { crime, proof, type });
        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => devLogger.log('FORENSIC', 'Accusation Submitted', { crime, proof, type }));
        onPlayerAction('QAYD_ACCUSATION', { accusation: { crime_card: crime, proof_card: proof, violation_type: type } });
    };

    const handleQaydTrigger = () => {
        console.log('[Table] detailed: handleQaydTrigger called');
        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => devLogger.log('FORENSIC', 'Qayd Trigger Button Clicked'));
        onPlayerAction('QAYD_TRIGGER');
    };

    const handleDirectorUpdate = async (config: any) => {
        try {
            await fetch(`${window.location.origin}/react-py4web/game/director/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            // Ideally we should also optimistically update local state or wait for socket push
        } catch (e) {
            console.error("Director Update Failed", e);
        }
    };

    useEffect(() => {
        if (isProjectRevealing) {
            setShowProjects(true);
        } else {
            // Delay hiding to ensure visibility
            const timer = setTimeout(() => setShowProjects(false), 3000);
            return () => clearTimeout(timer);
        }
    }, [isProjectRevealing]);

    // Fix: Use Ref for players to avoid re-subscribing when players array reference changes
    const playersRef = React.useRef(players);
    useEffect(() => { playersRef.current = players; }, [players]);

    // Listen for Bot Speak Events
    useEffect(() => {
        // Subscribe
        const cleanup = socketService.onBotSpeak((data) => {
            const { playerIndex, text, emotion } = data;

            // 1. Update Visuals
            setPlayerSpeech(prev => ({ ...prev, [playerIndex]: text }));

            // 2. Play Audio
            // use ref to get latest players without re-running effect
            const currentPlayers = playersRef.current;
            const player = currentPlayers.find(p => p.index === playerIndex);
            const personality = player ? getPersonality(player) : 'BALANCED';

            // Speak!
            speak(text, personality);

            // 3. Auto-clear after delay (SpeechBubble handles internal timer, but we sync state)
            setTimeout(() => {
                setPlayerSpeech(prev => {
                    const newState = { ...prev };
                    if (newState[playerIndex] === text) {
                        newState[playerIndex] = null;
                    }
                    return newState;
                });
            }, 5000);
        });

        return () => {
            if (cleanup) cleanup();
        };
    }, [speak]); // Removed players dependency


    // Sync timer with Game Settings
    const turnDuration = settings?.turnDuration || 10;
    const [timeLeft, setTimeLeft] = useState(turnDuration);
    const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
    const [selectedCardIndex, setSelectedCardIndex] = useState<number | null>(null);

    const [showProjectModal, setShowProjectModal] = useState(false);
    const [showAnalytics, setShowAnalytics] = useState(false);

    // Telemetry: Log Table Mount
    useEffect(() => {
        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => {
            devLogger.log('TABLE', 'Table Component Mounted', { phase: gameState?.phase });
        });
        return () => {
            // @ts-ignore
            import('../utils/devLogger').then(({ devLogger }) => devLogger.log('TABLE', 'Table Unmounted'));
        };
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
    const isFourColor = settings?.fourColorMode || false;
    const isHighContrast = settings?.highContrastMode || false;
    const cardLang = settings?.cardLanguage || 'EN';

    const me = players[0];
    const rightPlayer = players[1];
    const partner = players[2];
    const leftPlayer = players[3];

    // --- Game Rules Hook ---
    const { availableProjects, isCardPlayable, sortedHand } = useGameRules(gameState, me);

    // Calculate Card Groups for Elevation (Alternating Up/Down)
    const cardGroups = React.useMemo(() => {
        let currentSuit = '';
        let groupIndex = -1;
        const groups: Record<string, number> = {};

        sortedHand.forEach((card) => {
            // Check if suit changed (or first card)
            if (card.suit !== currentSuit) {
                groupIndex++;
                currentSuit = card.suit;
            }
            groups[card.id] = groupIndex;
        });
        return groups;
    }, [sortedHand]);

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

    // --- LOADING CHECKS (Render Content or Loading) ---
    if (!gameState || !gameState.players || gameState.players.length < 4 || !me || !rightPlayer || !partner || !leftPlayer) {
        // @ts-ignore
        return <div className="w-full h-full flex items-center justify-center text-black">Loading Game Table...</div>;
    }

    const isMyTurn = currentTurnIndex === me.index;

    const handleCardClick = (idx: number) => {
        // Raw Click Log
        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => devLogger.log('UI', 'Card Clicked Raw', { idx, phase, isMyTurn, currentTurnIndex }));

        if (phase === GamePhase.Playing && isMyTurn) {
            if (selectedCardIndex === idx) {
                // Double Click -> Play Normal
                const card = me.hand[idx];
                if (isCardPlayable(card)) {
                    // Send cardId for robust validation
                    onPlayerAction('PLAY', { cardIndex: idx, cardId: card.id });
                    setSelectedCardIndex(null);
                }
            } else {
                // First Click -> Select
                setSelectedCardIndex(idx);
            }
        } else {
            // Toggle selection (Bidding/Waiting)
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
            // Include cardId here too
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



    return (
        <div className="relative w-full h-full flex flex-col overflow-hidden select-none safe-area-top safe-area-bottom font-sans" style={{ background: '#F5F3EF' }}>

            <DevLogSidebar />

            {/* --- ZONE 1: HUD - Phase 1 UI Elements --- */}
            <ScoreBadge matchScores={matchScores} />

            {/* Ghost of Baloot Past HUD */}
            {gameState.metadata?.original_final_scores && (
                <div className="absolute top-28 left-4 z-40 bg-black/60 backdrop-blur-md p-2 rounded-lg border border-purple-500/50 shadow-lg flex flex-col gap-1 animate-in slide-in-from-left duration-700">
                    <div className="text-[10px] text-purple-300 font-bold uppercase tracking-wider flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse"></span>
                        Ghost of Past
                    </div>
                    {(() => {
                        // Current Scores
                        const curUs = matchScores.us;
                        const curThem = matchScores.them;

                        const origUs = gameState.metadata.original_final_scores.us;
                        const origThem = gameState.metadata.original_final_scores.them;

                        const diffUs = curUs - origUs;

                        return (
                            <div className="flex flex-col">
                                <span className="text-white text-xs font-medium">Original Final: {origUs} - {origThem}</span>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className={`text-sm font-bold ${diffUs >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        {diffUs > 0 ? '+' : ''}{diffUs}
                                    </span>
                                    <span className="text-[10px] text-gray-400">vs Final</span>
                                </div>
                            </div>
                        );
                    })()}
                </div>
            )}

            <div className="absolute top-16 left-4 z-50">
                <ContractIndicator bid={bid} players={players} doublingLevel={gameState.doublingLevel || 1} />
            </div>

            {/* Accessibility Toggle */}
            <button
                onClick={() => setIsAccessibilityMode(!isAccessibilityMode)}
                className="absolute top-4 left-32 z-50 bg-white/20 hover:bg-white/40 backdrop-blur-md p-1.5 rounded-full border border-white/30 text-white transition-all shadow-lg"
                title="Toggle Card Colors"
            >
                {isAccessibilityMode ? <Eye size={18} className="text-cyan-300" /> : <EyeOff size={18} />}
            </button>

            {/* Analytics Toggle (War Room) */}
            <button
                onClick={() => setShowAnalytics(!showAnalytics)}
                className={`absolute top-4 left-44 z-50 p-1.5 rounded-full border transition-all shadow-lg ${showAnalytics ? 'bg-yellow-500/80 border-yellow-300 text-white' : 'bg-white/20 border-white/30 text-white hover:bg-white/40'}`}
                title="Toggle War Room"
            >
                <ChartIcon size={18} />
            </button>

            {/* Commissioner Button */}
            <button
                onClick={() => setShowDirector(true)}
                className={`absolute top-4 left-56 z-50 p-1.5 rounded-full border transition-all shadow-lg ${showDirector ? 'bg-amber-600 border-amber-400 text-white' : 'bg-white/20 border-white/30 text-white hover:bg-white/40'}`}
                title="Commissioner's Desk"
            >
                <Gavel size={18} />
            </button>

            {/* Analytics Overlay */}
            {/* Overlays */}
            <HeartbeatLayer tension={tension} bpm={bpm} />
            <AnimatePresence>
                {/* Fixed SawaModal Props */}
                {gameState?.sawaState && gameState.sawaState.active && (
                    <SawaModal
                        isOpen={gameState.sawaState.active || false}
                        claimerName={players.find(p => p.position === gameState.sawaState?.claimer)?.name || 'Unknown Player'}
                        onAccept={() => handleSawaResponse('ACCEPT')}
                        onRefuse={() => handleSawaResponse('REFUSE')}
                    />
                )}
            </AnimatePresence>
            {/* TODO: Restore War Room / Professor Overlay logic */}
            {/* <ProfessorOverlay intervention={null} onUndo={() => {}} onInsist={() => {}} /> */}
            {showDirector && (
                <DirectorOverlay
                    gameState={gameState}
                    onClose={() => setShowDirector(false)}
                    onUpdate={handleDirectorUpdate}
                    onOpenMindMap={() => {
                        setShowDirector(false);
                        setShowMindMap(true); // Switch to Mind Map
                    }}
                />
            )}

            {/* Qayd Trigger Button (Floating) - REMOVED to prevent ghost triggers during Bidding
                Access via ActionBar -> Gavel Icon instead.
             */}

            {/* Qayd Overlay (Replaces Forensic) */}
            {gameState.qaydState?.active && (
                <QaydOverlay
                    gameState={gameState}
                    isHokum={(gameState.gameMode as 'SUN' | 'HOKUM') === 'HOKUM'}
                    isClosedDouble={(gameState.doublingLevel || 0) >= 2}
                    onPlayerAction={onPlayerAction}
                    onAccusation={(type, card, trickNum, player) => {
                         onPlayerAction('QAYD_ACCUSATION', { 
                             accusation: { crime_card: card, proof_card: null, violation_type: type } 
                         });
                    }}
                    onCancel={() => onPlayerAction('QAYD_CANCEL')}
                    onConfirm={() => onPlayerAction('QAYD_CONFIRM')}
                />
            )}

            <MindMapOverlay
                gameId={gameState.gameId || (gameState as any).roomId}
                players={gameState.players}
                isOpen={showMindMap || false}
                onClose={() => setShowMindMap(false)}
            />

            {/* --- ZONE 2: ARENA (Fills remaining space) --- */}
            <div className="relative w-full flex-1 flex items-center justify-center perspective-1000 z-10 transition-all duration-500">
                {/* The PREMIUM Table */}
                <div className={`
                    relative
                    w-[98%] sm:w-[95%] md:w-[85%] lg:w-[80%]
                    h-[92%] sm:h-[90%] md:h-[88%]
                    rounded-[2rem] sm:rounded-[2.5rem] md:rounded-[3rem]
                    shadow-[0_20px_40px_-12px_rgba(0,0,0,0.5)] md:shadow-[0_30px_60px_-12px_rgba(0,0,0,0.6)]
                    bg-cover bg-center
                    p-[8px] sm:p-[10px] md:p-[12px]
                    flex items-center justify-center
                `}
                    style={{
                        backgroundImage: (tableSkin === 'table_default' || !VISUAL_ASSETS.TABLES.find(t => t.id === tableSkin)?.type) ? `url(${premiumWood})` : undefined,
                        background: (VISUAL_ASSETS.TABLES.find(t => t.id === tableSkin)?.type === 'css') ? VISUAL_ASSETS.TABLES.find(t => t.id === tableSkin)?.value : undefined,
                        backgroundSize: 'cover'
                    }}
                >
                    {/* Inner Carpet */}
                    <div className="w-full h-full rounded-[1.5rem] sm:rounded-[2rem] md:rounded-[2.5rem] overflow-visible shadow-inner relative border-4 border-[#3e2723]">
                        {/* Background Premium Felt Texture */}
                        <div className="absolute inset-0 bg-cover bg-center rounded-[1.2rem] sm:rounded-[1.7rem] md:rounded-[2.2rem] overflow-hidden shadow-[inset_0_0_80px_rgba(0,0,0,0.6)]"
                            style={{ backgroundImage: `url(${premiumFelt})` }}
                        />

                        {/* Center Logo/Decor OR Waiting State */}
                        {gameState.phase === GamePhase.Waiting ? (
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center z-50">
                                <h2 className="text-white text-xl font-bold mb-4 drop-shadow-md">Waiting for Players...</h2>
                                <div className="flex gap-4">
                                    <div className="text-white/70 text-sm bg-black/40 px-3 py-1 rounded-full">{players.length}/4 Players</div>
                                </div>
                                {onAddBot && (
                                    <button
                                        onClick={onAddBot}
                                        className="mt-6 px-6 py-2 bg-gradient-to-r from-blue-500 to-blue-700 text-white font-bold rounded-full shadow-lg hover:scale-105 active:scale-95 transition-all border-2 border-white/20 flex items-center gap-2"
                                    >
                                        <Plus size={18} /> Add Bot
                                    </button>
                                )}
                            </div>
                        ) : (
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 opacity-10 rounded-full border-4 border-white/20" />
                        )}

                        {/* --- PLAYERS & HANDS (Using PlayerAvatar Component) --- */}
                        {/* UPDATE: Pass speechText to all avatars */}

                        {/* Partner (Top) */}
                        {partner && (
                            <PlayerAvatar
                                player={partner}
                                isCurrentTurn={currentTurnIndex === partner.index}
                                position="top"
                                timeLeft={timeLeft}
                                totalTime={turnDuration}
                                declarations={declarations}
                                isProjectRevealing={gameState.isProjectRevealing}
                                bid={bid}
                                doublingLevel={gameState.doublingLevel}
                                showProjects={showProjects}
                                speechText={playerSpeech[partner.index]}
                                isPaused={isPaused}
                            />
                        )}

                        {/* Left Player */}
                        {leftPlayer && (
                            <PlayerAvatar
                                player={leftPlayer}
                                isCurrentTurn={currentTurnIndex === leftPlayer.index}
                                position="left"
                                timeLeft={timeLeft}
                                totalTime={turnDuration}
                                declarations={declarations}
                                isProjectRevealing={gameState.isProjectRevealing}
                                bid={bid}
                                doublingLevel={gameState.doublingLevel}
                                showProjects={showProjects}
                                speechText={playerSpeech[leftPlayer.index]}
                                akkaState={akkaState}
                            />
                        )}

                        {/* Right Player */}
                        {rightPlayer && (
                            <PlayerAvatar
                                player={rightPlayer}
                                isCurrentTurn={currentTurnIndex === rightPlayer.index}
                                position="right"
                                timeLeft={timeLeft}
                                totalTime={turnDuration}
                                declarations={declarations}
                                isProjectRevealing={gameState.isProjectRevealing}
                                bid={bid}
                                doublingLevel={gameState.doublingLevel}
                                showProjects={showProjects}
                                speechText={playerSpeech[rightPlayer.index]}
                                akkaState={akkaState}
                            />
                        )}



                        {/* --- FLOOR CARD (BUYER) - Phase I/II --- */}
                        {gameState.floorCard && dealPhase !== 'IDLE' && dealPhase !== 'DEAL_1' && dealPhase !== 'DEAL_2' && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-30 pb-32 sm:pb-40">
                                {/* Enhanced Card Container */}
                                <div className="relative animate-floor-reveal">
                                    {/* Intense Outer Glow */}
                                    <div className="absolute -inset-4 sm:-inset-5 md:-inset-6 bg-gradient-to-r from-yellow-300 via-amber-400 to-yellow-500 rounded-xl blur-xl opacity-70 animate-pulse"></div>
                                    <div className="absolute -inset-3 sm:-inset-4 bg-yellow-400/40 rounded-lg blur-lg"></div>
                                    <div className="absolute -inset-2 rounded-lg border-3 sm:border-4 border-yellow-400 opacity-60 animate-ping"></div>
                                    <div className="absolute -inset-1 rounded-lg border-2 border-amber-300 opacity-40 animate-ping" style={{ animationDelay: '0.5s' }}></div>
                                    <CardVector
                                        card={gameState.floorCard}
                                        className="h-32 w-24 sm:h-36 sm:w-26 md:h-40 md:w-28 shadow-2xl"
                                        isPlayable={false}
                                        skin={cardSkin}
                                    />
                                </div>
                            </div>
                        )}

                        {/* --- PLAYED CARDS (CROSS FORMATION) --- */}
                        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                            {/* 1. Active Cards (Playing) */}
                            {tableCards && tableCards.map((played, idx) => {
                                if (!played || !played.card) return null; // Safety Check
                                const playerObj = players.find(p => p && p.position === played?.playedBy);
                                const pIdx = playerObj?.index ?? 0;
                                const isLatest = idx === tableCards.length - 1;
                                const { initial, animate, exit, style, animClass } = getPlayedCardAnimation({
                                    playerIndex: pIdx,
                                    isLatest,
                                    myIndex: me?.index ?? 0,
                                    players,
                                    tableCards: gameState.tableCards
                                });

                                return (
                                    <motion.div key={`played-${idx}-${played.card.id}`}
                                        initial={initial}
                                        animate={animate}
                                        exit={exit}
                                        transition={{ type: "spring", stiffness: 350, damping: 25, mass: 0.8 }}
                                        className={`${animClass}`}
                                        style={style}>
                                        <CardVector
                                            card={played.card}
                                            className="w-full h-full shadow-xl"
                                            isPlayable={false}
                                            skin={cardSkin}
                                        />
                                    </motion.div>
                                );
                            })}
                            {/* 2. Sweeping Cards (Trick done) */}
                            {gameState.lastTrick && gameState.lastTrick.cards && gameState.lastTrick.cards.map((played, idx) => {
                                if (!played || !played.card) return null; // Safety Check
                                const playerObj = players.find(p => p && p.position === (played as any)?.playedBy);
                                const pIdx = playerObj?.index ?? 0;
                                const { style } = getPlayedCardAnimation({
                                    playerIndex: pIdx,
                                    isLatest: false,
                                    myIndex: me?.index ?? 0,
                                    players,
                                    tableCards: gameState.tableCards
                                });

                                const winnerPos = gameState.lastTrick!.winner;
                                const isPartnerWinner = winnerPos === players[2].position;
                                const isRightWinner = winnerPos === players[1].position;
                                const isLeftWinner = winnerPos === players[3].position;

                                let sweepClass = 'sweep-bottom'; // Default to me
                                if (isPartnerWinner) sweepClass = 'sweep-top';
                                else if (isRightWinner) sweepClass = 'sweep-right';
                                else if (isLeftWinner) sweepClass = 'sweep-left';

                                return (
                                    <div key={`swept-${idx}`}
                                        className={`absolute ${sweepClass}`}
                                        style={{
                                            ...style,
                                            zIndex: 50 + idx
                                        }}>
                                        <CardVector
                                            card={played.card}
                                            className="h-[25%] w-auto aspect-[2.5/3.5] shadow-2xl played-card-mobile opacity-90"
                                            skin={cardSkin}
                                        />
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>

            {/* --- ZONE 3: ACTIONS & HAND (Unified Action Bar) --- */}

            {/* USER HAND RENDER (Refactored to HandFan) */}
            {me && me.hand && (
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
            )}
            {/* NEW LOCATION: HUD - Bottom Center Avatar (Top Level) */}
            <PlayerAvatar
                player={me}
                isCurrentTurn={isMyTurn}
                position="bottom"
                timeLeft={timeLeft}
                totalTime={turnDuration}
                declarations={declarations}
                isProjectRevealing={gameState.isProjectRevealing}
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

            {/* Dealer Badge for Me */}
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
                        {/* Debug: Manual Unlock */}
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
