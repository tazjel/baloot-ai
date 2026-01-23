import React, { useEffect, useState } from 'react';
import { GameState, Player, PlayerPosition, GamePhase, Suit } from '../types';
import Card from './Card';
import { TriangleAlert, Trophy, ShieldAlert, Pause, Menu, Gavel, Sun, WalletCards, PanelRightOpen, ArrowRight, Plus, Megaphone } from 'lucide-react'; // Added Megaphone
import ProjectSelectionModal from './ProjectSelectionModal';
import { Spade, Heart, Club, Diamond } from './SuitIcons';
import { canDeclareAkka, sortHand } from '../utils/gameLogic'; // Added import
import premiumWood from '../assets/premium_wood_texture.png';
import premiumFelt from '../assets/premium_felt_texture.png';
import royalBack from '../assets/royal_card_back.png';
import { soundManager } from '../services/SoundManager';
import SawaModal from './SawaModal';
import ActionBar from './ActionBar';
import GablakTimer from './GablakTimer'; // Added
import { DevLogSidebar } from './DevLogSidebar'; // Added

interface TableProps {
    gameState: GameState;
    onPlayerAction: (action: string, payload?: any) => void;
    onDebugAction?: (action: string, payload?: any) => void;
    onChallenge?: () => void;
    onAddBot?: () => void;
    isCuttingDeck?: boolean;
    tableSkin?: string;
    cardSkin?: string;
    onSawa?: () => void;
    onEmoteClick?: () => void;
    isSendingAction?: boolean;
}

// Avatar Mapping
const AVATAR_MAP: Record<string, string> = {
    'avatar_saad': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Saad&backgroundColor=b6e3f4',
    'avatar_khalid': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Khalid&backgroundColor=c0aede&clothing=blazerAndShirt',
    'avatar_abu_fahad': 'https://api.dicebear.com/7.x/avataaars/svg?seed=AbuFahad&backgroundColor=ffdfbf&facialHair=beardMajestic',
    'bot_1': 'https://api.dicebear.com/7.x/bottts/svg?seed=Bot1'
};

// --- Extracted Components (Moved to Module Scope to fix Shadowing) ---

const ScoreBadge = ({ matchScores }: { matchScores: any }) => {
    if (!matchScores) return null;
    return (
        <div className="absolute top-4 left-4 z-50 flex gap-3">
            {/* Us Score */}
            <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl px-2 py-0.5 shadow-xl border-2 border-white/20 backdrop-blur-sm">
                <div className="text-[9px] text-white/80 font-bold">نحن</div>
                <div className="text-[15px] font-black text-white">{matchScores.us}</div>
            </div>
            {/* Them Score */}
            <div className="bg-gradient-to-br from-red-600 to-red-800 rounded-2xl px-2 py-0.5 shadow-xl border-2 border-white/20 backdrop-blur-sm">
                <div className="text-[9px] text-white/80 font-bold">هم</div>
                <div className="text-[15px] font-black text-white">{matchScores.them}</div>
            </div>
        </div>
    );
};

const TurnTimer = ({ isActive, timeLeft, totalTime }: { isActive: boolean, timeLeft: number, totalTime: number }) => {
    if (!isActive) return null;

    const radius = 36;
    const stroke = 6;
    const circumference = 2 * Math.PI * radius;
    const percentage = timeLeft / totalTime;
    const progress = percentage * circumference;

    let strokeColor = '#22c55e'; // Green
    if (percentage < 0.25) strokeColor = '#ef4444'; // Red
    else if (percentage < 0.5) strokeColor = '#D4AF37'; // Gold

    return (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[84px] h-[84px] pointer-events-none z-50 flex items-center justify-center">
            <svg
                className="-rotate-90 absolute inset-0"
                width="84" height="84"
                viewBox="0 0 84 84"
            >
                <circle cx="42" cy="42" r={radius} stroke="rgba(0,0,0,0.4)" strokeWidth={stroke} fill="none" />
                <circle
                    cx="42" cy="42" r={radius}
                    stroke={strokeColor}
                    strokeWidth={stroke}
                    strokeLinecap="round"
                    fill="none"
                    strokeDasharray={circumference}
                    strokeDashoffset={circumference - progress}
                    className="transition-all duration-1000 ease-linear shadow-lg"
                    style={{ filter: 'drop-shadow(0 0 2px rgba(0,0,0,0.5))' }}
                />
            </svg>
            <span className="text-amber-400 font-black text-sm sm:text-base md:text-lg drop-shadow-md z-50">
                {timeLeft}
            </span>
        </div>
    );
};

const ContractIndicator = ({ bid, players, doublingLevel }: { bid: any, players: Player[], doublingLevel: number }) => {
    if (!bid || !bid.type) return null;
    const isDoubled = doublingLevel >= 2;
    const bidder = players.find(p => p.position === bid.bidder);
    if (!bidder) return null;
    const isOurTeam = bidder.position === PlayerPosition.Bottom || bidder.position === PlayerPosition.Top;
    const teamBg = isOurTeam ? 'bg-blue-600' : 'bg-red-600';

    return (
        <div className={`${teamBg} rounded-full shadow-xl px-2 py-0.5 border-2 border-white/20 backdrop-blur-sm flex items-center gap-1`}>
            <span className="text-[9px] sm:text-[10px] font-bold text-white">{bidder.name}</span>
            <div className="flex items-center gap-1 bg-white/20 rounded-full px-1 py-0.5">
                {bid.type === 'SUN' ? <Sun size={10} className="text-amber-300" /> : <Gavel size={10} className="text-white" />}
                <span className="text-[9px] font-black text-white uppercase">{bid.type}</span>
            </div>
            {bid.suit && (
                <div className="bg-white/20 rounded-full p-0.5">
                    {bid.suit === Suit.Spades && <Spade size={10} className="text-white" />}
                    {bid.suit === Suit.Hearts && <Heart size={10} className="text-red-300" />}
                    {bid.suit === Suit.Clubs && <Club size={10} className="text-green-300" />}
                    {bid.suit === Suit.Diamonds && <Diamond size={10} className="text-blue-300" />}
                </div>
            )}
            {isDoubled && (
                <div className="bg-red-600 text-white text-[8px] font-black px-1 py-0 rounded-full border border-white/20 shadow-lg animate-pulse">
                    x{doublingLevel}
                </div>
            )}
        </div>
    );
};

const PlayerAvatar = ({ player, isCurrentTurn, position, timeLeft, totalTime, declarations, isProjectRevealing, bid, doublingLevel }: {
    player: Player,
    isCurrentTurn: boolean,
    position: 'top' | 'left' | 'right' | 'bottom',
    timeLeft: number,
    totalTime: number,
    declarations: any,
    isProjectRevealing: boolean,
    bid?: any,
    doublingLevel?: number
}) => {
    const isPartner = position === 'top';
    let posClass = 'absolute z-30';
    // Adjusted: Less negative offset on mobile to prevent clipping
    if (position === 'left') posClass += ' top-1/2 -translate-y-1/2 left-1 sm:-left-[5rem] md:-left-[5.5rem]';
    else if (position === 'right') posClass += ' top-1/2 -translate-y-1/2 right-1 sm:-right-[5rem] md:-right-[5.5rem]';
    else if (position === 'top') posClass += ' top-1 sm:top-2 left-1/2 -translate-x-1/2';
    else if (position === 'bottom') posClass += ' bottom-14 left-1/2 -translate-x-1/2 z-[200]'; // Lifted slightly


    return (
        <div className={`flex flex-col items-center ${posClass}`}>
            <div className="relative">
                {/* Timer rendered for all positions now */}
                <TurnTimer isActive={isCurrentTurn} timeLeft={timeLeft} totalTime={totalTime} />

                {/* Dark Overlay for Active Player to boost Timer contrast */}
                {isCurrentTurn && (
                    <div className="absolute inset-0 z-40 bg-black/60 rounded-full animate-in fade-in duration-300"></div>
                )}



                <div className={`
                    w-[1.7rem] h-[1.7rem] sm:w-[2.0rem] sm:h-[2.0rem] md:w-[2.35rem] md:h-[2.35rem] 
                    rounded-full bg-white shadow-xl overflow-hidden relative z-10
                    ${isCurrentTurn ? 'halo-active' : ''}
                    ${isPartner ? 'border-2 border-[var(--color-premium-gold)]' : 'border-2 border-white/80'}
                `}>
                    <img
                        src={player.avatar && player.avatar.startsWith('http') ? player.avatar : (AVATAR_MAP[player.avatar] || player.avatar)}
                        className="w-full h-full object-cover"
                        alt={player.name}
                        onError={(e) => {
                            // Fallback if image fails or is missing
                            (e.target as HTMLImageElement).src = `https://api.dicebear.com/7.x/initials/svg?seed=${player.name}`;
                        }}
                    />
                </div>
            </div>
            {player.isDealer && (
                <div className="absolute -bottom-2 right-1/2 translate-x-1/2 bg-[var(--color-premium-gold)] border border-white/50 rounded-md px-1.5 py-0.5 flex items-center justify-center z-40 shadow-sm">
                    <span className="text-[8px] font-black text-black leading-none">Dealer</span>
                </div>
            )}
            {!isPartner && (
                <div className={`
                    bg-black/80 text-white px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-[10px] sm:text-xs font-bold 
                    -mt-2 sm:-mt-3 z-20 mb-1
                    ${position === 'bottom' ? '-order-1 mb-0 -mt-0 -mb-2' : ''}
                    ${isPartner ? 'border border-amber-500/50' : 'border border-white/20'}
                    ${isCurrentTurn ? 'bg-amber-600/90' : ''}
                `}>
                    {player.name}
                </div>
            )}
            {player.actionText && (
                <div key={player.actionText} className="absolute -top-4 -right-10 bg-white/90 text-black px-2 py-1 rounded-lg rounded-bl-none shadow-md border border-gray-200 z-50 whitespace-nowrap animate-in fade-in zoom-in duration-200">
                    <span className="text-[10px] sm:text-xs font-bold">{player.actionText === 'PASS' ? 'بس' : player.actionText}</span>
                </div>
            )}

            {/* Winning Bid Tag - Rendered BELOW the avatar */}
            {bid && bid.bidder === player.position && (
                <div className={`
                    absolute -bottom-5 left-1/2 -translate-x-1/2 
                    flex items-center gap-1 px-3 py-0.5 rounded-full shadow-lg z-50
                    animate-in fade-in slide-in-from-top-2 duration-500
                    ${(player.position === PlayerPosition.Bottom || player.position === PlayerPosition.Top) ? 'bg-blue-600' : 'bg-red-600'}
                    border border-white/30
                 `}>
                    {/* Simplified: No Name, just Icon + Text */}
                    {bid.type === 'SUN' ? <Sun size={12} className="text-amber-300" /> : <Gavel size={12} className="text-white" />}

                    <span className="text-[10px] sm:text-xs font-black text-white uppercase tracking-wider">
                        {bid.type}
                    </span>

                    {/* Suit Icon if applicable */}
                    {bid.suit && (
                        <div className="bg-white/20 rounded-full p-0.5 ml-1">
                            {bid.suit === Suit.Spades && <Spade size={10} className="text-white" />}
                            {bid.suit === Suit.Hearts && <Heart size={10} className="text-red-300" />}
                            {bid.suit === Suit.Clubs && <Club size={10} className="text-green-300" />}
                            {bid.suit === Suit.Diamonds && <Diamond size={10} className="text-blue-300" />}
                        </div>
                    )}
                    {/* Multiplier Badge */}
                    {(doublingLevel && doublingLevel >= 2) && (
                        <div className="bg-red-500 text-white text-[9px] font-black px-1.5 rounded-full ml-1 animate-pulse border border-white/20">
                            x{doublingLevel}
                        </div>
                    )}
                </div>
            )}
            {isProjectRevealing && declarations?.[player.position] && declarations[player.position].length > 0 && (
                <div className="absolute top-10 left-1/2 -translate-x-1/2 w-max flex flex-col items-center gap-1 z-50 animate-bounce-in">
                    {declarations[player.position].map((proj: any, idx: number) => {
                        let label = '';
                        switch (proj.type) {
                            case 'SIRA': label = 'سرا'; break;
                            case 'FIFTY': label = '50'; break;
                            case 'HUNDRED': label = '100'; break;
                            case 'FOUR_HUNDRED': label = '400'; break;
                            case 'BALOOT': label = 'بلوت'; break;
                        }
                        return (
                            <div key={idx} className="bg-gradient-to-r from-amber-300 to-yellow-500 text-black font-black text-xs sm:text-sm px-3 py-1 rounded-full shadow-lg border border-white flex items-center gap-1">
                                <Trophy size={14} className="text-amber-800" />
                                <span>{label}</span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

const Table: React.FC<TableProps> = ({ gameState, onPlayerAction, onDebugAction, onChallenge, onAddBot, isCuttingDeck = false, tableSkin = 'table_default', cardSkin = 'card_default', onSawa, onEmoteClick, isSendingAction = false }) => {
    // --- HOOKS (Must be unconditional) ---
    const { players = [], currentTurnIndex = 0, phase, tableCards = [], floorCard, bid, settings, declarations, matchScores = { us: 0, them: 0 }, sawaState } = gameState || {};

    // Sync timer with Game Settings
    const turnDuration = settings?.turnDuration || 10;
    const [timeLeft, setTimeLeft] = useState(turnDuration);
    const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
    const [selectedCardIndex, setSelectedCardIndex] = useState<number | null>(null);
    const [showProjectModal, setShowProjectModal] = useState(false);

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

    // Sorted Hand for Display
    const sortedHand = React.useMemo(() => {
        if (!me?.hand) return [];
        return sortHand(me.hand, gameState.gameMode || 'SUN', gameState.trumpSuit);
    }, [me?.hand, gameState.gameMode, gameState.trumpSuit]);

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

    // --- Hand Scanning for Projects (Trick 1) ---
    const [availableProjects, setAvailableProjects] = useState<string[]>([]);

    useEffect(() => {
        if (phase === GamePhase.Playing && currentTurnIndex === 0 && me && me.hand && me.hand.length === 8) {
            const projs = scanHandJS(me.hand, gameState?.gameMode || 'SUN');
            setAvailableProjects(projs);
        } else {
            setAvailableProjects([]);
        }
    }, [me?.hand, phase, currentTurnIndex, gameState?.gameMode]);

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
        return <div className="w-full h-full flex items-center justify-center text-black">Loading Game Table...</div>;
    }

    const isMyTurn = currentTurnIndex === me.index;

    // --- Validation Logic ---
    const isCardPlayable = (card: any) => {
        if (phase !== GamePhase.Playing || !isMyTurn) return false;
        if (!settings?.strictMode) return true;
        if (tableCards.length === 0) return true;
        const leadSuit = tableCards[0].card.suit;
        const hasLeadSuit = me.hand.some(c => c.suit === leadSuit);
        if (hasLeadSuit) return card.suit === leadSuit;
        return true;
    };

    const handleCardClick = (idx: number) => {
        // Raw Click Log
        // @ts-ignore
        import('../utils/devLogger').then(({ devLogger }) => devLogger.log('UI', 'Card Clicked Raw', { idx, phase, isMyTurn, currentTurnIndex }));

        if (phase === GamePhase.Playing && isMyTurn) {
            if (selectedCardIndex === idx) {
                // Double Click -> Play Normal
                if (isCardPlayable(me.hand[idx])) {
                    onPlayerAction('PLAY', { cardIndex: idx });
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
            soundManager.playAkkaSound();
            onPlayerAction('PLAY', { cardIndex: selectedCardIndex, metadata: { akka: true } });
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

    useEffect(() => {
        setTimeLeft(turnDuration);
        const timer = setInterval(() => {
            setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
        }, 1000);
        return () => clearInterval(timer);
    }, [currentTurnIndex, turnDuration]);

    // --- Hand Scanning for Projects (Trick 1) ---
    // (Moved to top level)

    const scanHandJS = (hand: any[], mode: string) => {
        if (!hand) return [];
        const types = new Set<string>();
        const validCards = hand.filter(c => c && (c.rank || (c.card && c.card.rank))); // Filter valid
        const ranks = validCards.map((c: any) => c.card ? c.card.rank : c.rank);
        const rankCounts: Record<string, number> = {};
        ranks.forEach((r: string) => { if (r) rankCounts[r] = (rankCounts[r] || 0) + 1 });

        // 4 of a Kind
        for (const [r, count] of Object.entries(rankCounts)) {
            if (count === 4) {
                if (r === 'A' && mode === 'SUN') types.add('FOUR_HUNDRED');
                else if (['K', 'Q', 'J', '10', 'A'].includes(r)) types.add('HUNDRED');
            }
        }

        // Sequences
        const suits = ['♠', '♥', '♦', '♣'];
        const order = ['A', 'K', 'Q', 'J', '10', '9', '8', '7'];

        suits.forEach(s => {
            const suitCards = validCards.filter((c: any) => c.card ? c.card.suit === s : c.suit === s); // Frontend Card object structure check
            // Helper to safe get rank
            const getRank = (c: any) => c.card ? c.card.rank : c.rank;

            // Sort
            suitCards.sort((a: any, b: any) => order.indexOf(getRank(a)) - order.indexOf(getRank(b)));

            let currentSeq = 1;
            for (let i = 0; i < suitCards.length - 1; i++) {
                const idx1 = order.indexOf(getRank(suitCards[i]));
                const idx2 = order.indexOf(getRank(suitCards[i + 1]));

                if (idx2 === idx1 + 1) {
                    currentSeq++;
                } else {
                    if (currentSeq >= 5) types.add('HUNDRED');
                    else if (currentSeq === 4) types.add('FIFTY');
                    else if (currentSeq === 3) types.add('SIRA');
                    currentSeq = 1;
                }
            }
            if (currentSeq >= 5) types.add('HUNDRED');
            else if (currentSeq === 4) types.add('FIFTY');
            else if (currentSeq === 3) types.add('SIRA');
        });

        return Array.from(types);
    };

    // --- Helper: Get Relative Position for Played Cards ---
    // --- Helper: Get Relative Position for Played Cards ---
    // Style: Tight cluster in center with slight overlap
    const getPlayedCardAnimation = (playerIndex: number, isLatest: boolean) => {
        // DEFENSIVE: Ensure player exists and has index property
        const playerZeroIndex = players[0]?.index ?? 0;
        const relativeIndex = (playerIndex - playerZeroIndex + 4) % 4; // 0=Me, 1=Right, 2=Partner, 3=Left

        // Card size for played cards - Responsive
        // Mobile: 60x84, Desktop: 85x118
        // We can't easily use Tailwind classes inside inline styles for detailed transform calculations usually,
        // but we can scale the base values or use a hook. 
        // For simplicity, let's assume a smaller base size and rely on CSS scaling or just keep it tight.
        // Let's use smaller fixed pixels for mobile logic if we had width access.
        // Alternative: Use viewport units?
        const cardWidth = window.innerWidth < 640 ? 60 : 85;
        const cardHeight = window.innerWidth < 640 ? 84 : 118;


        // Offsets from center (Reduced for overlap)
        const offsetDistance = window.innerWidth < 640 ? 30 : 45; // Tighter on mobile


        // Base positioning
        let xOffset = 0;
        let yOffset = 0;
        let rotation = 0;

        // Add some "messiness" based on index to look organic? 
        // Or strict "Cross" but tight?
        // User asked for "little overlapping". 
        // Strict relative positioning:

        switch (relativeIndex) {
            case 0: // Me (Bottom) - card is bottom-center
                xOffset = 0;
                yOffset = offsetDistance;
                rotation = -2 + ((playerIndex * 7) % 4); // Deterministic "random"
                break;
            case 1: // Right - card is right-center
                xOffset = offsetDistance * 1.5;
                yOffset = 0;
                rotation = 85 + ((playerIndex * 7) % 4);
                break;
            case 2: // Partner (Top) - card is top-center
                xOffset = 0;
                yOffset = -offsetDistance;
                rotation = 180 + ((playerIndex * 7) % 4);
                break;
            case 3: // Left - card is left-center
                xOffset = -offsetDistance * 1.5;
                yOffset = 0;
                rotation = -85 + ((playerIndex * 7) % 4);
                break;
        }

        // Z-index: later cards on top is standard.
        // But for "pile" feel, maybe they just stack naturally?
        // `tableCards` is ordered by play time. 
        // We find the index of THIS card in the tableCards array to determine Z.
        const playOrder = gameState.tableCards.findIndex(c => (c as any).playedBy === players[playerIndex].position);
        const zIndex = 40 + (playOrder >= 0 ? playOrder : 0);

        const style: React.CSSProperties = {
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: `${cardWidth}px`,
            height: `${cardHeight}px`,
            transform: `translate(calc(-50% + ${xOffset}px), calc(-50% + ${yOffset}px)) rotate(${rotation}deg)`,
            zIndex: zIndex,
            transition: isLatest ? 'transform 0.4s cubic-bezier(0.18, 0.89, 0.32, 1.28)' : 'none', // Pop effect
            boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
        };

        return {
            style,
            animClass: isLatest ? 'animate-throw-pop animate-thump' : '' // Added Thump
        };
    };

    // --- Components ---




    // --- Dealing Animation (Moved) ---

    // --- Sound Effects (Moved) ---

    // --- Juice Animations & Styles ---

    // --- Juice Animations & Styles ---

    return (
        <div className="relative w-full h-full flex flex-col overflow-hidden select-none safe-area-top safe-area-bottom font-sans" style={{ background: '#F5F3EF' }}>

            <DevLogSidebar />

            {/* --- ZONE 1: HUD - Phase 1 UI Elements --- */}
            <ScoreBadge matchScores={matchScores} />



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
                    style={{ backgroundImage: `url(${premiumWood})` }}
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
                            />
                        )}


                        {/* --- YOUR TURN NOTIFICATION --- */}
                        {/* --- YOUR TURN NOTIFICATION --- */}
                        {/* --- YOUR TURN NOTIFICATION --- */}


                        {/* --- PLAYERS & HANDS (Using PlayerAvatar Component) --- */}

                        {/* --- Gablak Timer (Steal Window) --- */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[150%] z-[100] pointer-events-none">
                            <GablakTimer
                                biddingPhase={gameState?.biddingPhase}
                                isActive={isMyTurn}
                                duration={5}
                            />
                        </div>

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
                                    <Card
                                        card={gameState.floorCard}
                                        skin={cardSkin}
                                        className="h-32 w-24 sm:h-36 sm:w-26 md:h-40 md:w-28 shadow-2xl"
                                        isFourColorMode={isFourColor}
                                        isHighContrast={isHighContrast}
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
                                const { style, animClass } = getPlayedCardAnimation(pIdx, isLatest);

                                return (
                                    <div key={`played-${idx}`}
                                        className={`${animClass}`}
                                        style={style}>
                                        <Card
                                            card={played.card}
                                            skin={cardSkin}
                                            className="w-full h-full shadow-xl"
                                            isFourColorMode={isFourColor}
                                            isHighContrast={isHighContrast}
                                            cardLanguage={cardLang}
                                            isAkka={played.metadata?.akka}
                                        />
                                    </div>
                                );
                            })}

                            {/* 2. Sweeping Cards (Trick done) */}
                            {gameState.lastTrick && gameState.lastTrick.cards && gameState.lastTrick.cards.map((played, idx) => {
                                if (!played || !played.card) return null; // Safety Check
                                const playerObj = players.find(p => p && p.position === (played as any)?.playedBy);
                                const pIdx = playerObj?.index ?? 0;
                                const { style } = getPlayedCardAnimation(pIdx, false);

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
                                        <Card
                                            card={played.card}
                                            skin={cardSkin}
                                            className="h-[25%] w-auto aspect-[2.5/3.5] shadow-2xl played-card-mobile opacity-90"
                                            isFourColorMode={isFourColor}
                                            isHighContrast={isHighContrast}
                                            cardLanguage={cardLang}
                                        />
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>

            {/* --- ZONE 3: ACTIONS & HAND (Unified Action Bar) --- */}

            {/* USER HAND RENDER (Restored) */}
            {
                me && me.hand && (
                    <div className="absolute bottom-2 sm:bottom-4 left-1/2 -translate-x-1/2 flex items-end justify-center -space-x-8 sm:-space-x-10 md:-space-x-12 z-50 perspective-1000 w-full px-4 overflow-visible pointer-events-none">
                        {sortedHand.map((card, idx) => {
                            const originalIndex = me.hand.findIndex(c => c.id === card.id);
                            const isSelected = selectedCardIndex === originalIndex;
                            const valid = isCardPlayable(card);

                            // Visual Grouping Logic
                            const groupIdx = cardGroups[card.id] || 0;
                            const isElevated = groupIdx % 2 === 0; // Even groups up, Odd groups down

                            // Base positioning
                            // Up: bottom-5
                            // Down: bottom-0
                            const baseClass = isElevated ? 'bottom-5 sm:bottom-6' : 'bottom-0';
                            const hoverClass = isElevated ? 'hover:bottom-9 sm:hover:bottom-10' : 'hover:bottom-4';

                            // Interactive wrapper
                            return (
                                <div key={`hand-${idx}`}
                                    className={`
                                    relative transition-all duration-300 pointer-events-auto
                                    ${isSelected
                                            ? 'bottom-12 sm:bottom-14 z-[60] scale-110'
                                            : `${baseClass} ${hoverClass} hover:z-[55] hover:scale-105`
                                        }
                                    ${!valid && phase === GamePhase.Playing ? 'opacity-50 grayscale' : 'opacity-100'}
                                `}
                                    style={{
                                        transformOrigin: 'bottom center',
                                        zIndex: isSelected ? 60 : 50 + (sortedHand.length - idx)
                                    }}
                                    onClick={() => handleCardClick(me.hand.findIndex(c => c.id === card.id))}
                                >
                                    <Card
                                        card={card}
                                        skin={cardSkin}
                                        className="w-[3.75rem] h-[5.55rem] sm:w-[4.55rem] sm:h-[6.7rem] md:w-[5.2rem] md:h-[7.9rem] shadow-2xl"
                                        isFourColorMode={isFourColor}
                                        isHighContrast={isHighContrast}
                                        cardLanguage={cardLang}
                                    />
                                </div>
                            );
                        })}
                    </div>
                )
            }
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

            {/* Standalone Bottom Timer for Me */}
            {/* Standalone Bottom Timer REMOVED - Integrated into PlayerAvatar */}


            {/* Dealer Badge for Me */}
            {
                me.isDealer && (
                    <div className="absolute top-4 right-4 bg-white/90 px-3 py-1 rounded-full shadow-lg border border-yellow-500 flex items-center gap-2 animate-in fade-in duration-700">
                        <div className="w-5 h-5 bg-[var(--color-premium-gold-gold)] rounded-full flex items-center justify-center font-bold text-xs text-black">D</div>
                        <span className="text-xs font-bold text-gray-800">أنت الموزع</span>
                    </div>
                )
            }

            {/* Sending Indicator Overlay */}
            {
                isSendingAction && (
                    <div className="absolute inset-0 bg-black/20 z-[1000] flex items-center justify-center pointer-events-none">
                        <div className="bg-white/90 backdrop-blur text-black px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 animate-pulse">
                            <div className="w-5 h-5 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
                            <span className="font-bold">Sending...</span>
                        </div>
                    </div>
                )
            }
        </div >
    );
};



export default Table;