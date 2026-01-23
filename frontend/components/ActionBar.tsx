import React from 'react';
import { GameState, GamePhase, Suit, Player } from '../types';
import { Spade, Heart, Club, Diamond } from './SuitIcons';
import { Gavel, Megaphone, Sun, RefreshCw, X, Trophy, Smile } from 'lucide-react';
import { canDeclareAkka, canDeclareKawesh } from '../utils/gameLogic';
import { soundManager } from '../services/SoundManager';

interface ActionBarProps {
    gameState: GameState;
    me: Player;
    isMyTurn: boolean;
    onPlayerAction: (action: string, payload?: any) => void;
    availableProjects: string[];
    selectedCardIndex: number | null;
    settings?: any;
    onEmoteClick?: () => void; // New prop for emote button
}

const ActionBar: React.FC<ActionBarProps> = ({
    gameState,
    me,
    isMyTurn,
    onPlayerAction,
    availableProjects,
    selectedCardIndex,
    settings,
    onEmoteClick
}) => {
    const { phase, biddingRound, floorCard, bid } = gameState;

    // Helper: Determine if a button is disabled
    const isActionDisabled = !isMyTurn;

    // --- RENDER HELPERS ---

    const [showScoreSheet, setShowScoreSheet] = React.useState(false);

    // --- BUTTON STYLES ---
    const dockBtnBase = "flex flex-col items-center justify-center w-[2.0rem] h-[2.0rem] sm:w-[2.5rem] sm:h-[2.5rem] rounded-2xl transition-all duration-200 backdrop-blur-md border border-white/10 shadow-lg";
    const dockBtnActive = "bg-zinc-800 text-white hover:bg-zinc-700 hover:scale-105 active:scale-95";
    const dockBtnDisabled = "bg-zinc-900/40 text-white/20 cursor-not-allowed grayscale";

    // --- ACTIONS ---
    const handleSawa = () => {
        onPlayerAction('SAWA_CLAIM');
    };

    const handleRecord = () => {
        // "Qaydha" - In Playing, this likely opens/shows score or is a confirming action.
        // For now, let's make it toggle a simple Score View or just Log.
        console.log("Record/Qaydha clicked");
    };

    // --- RENDER DOCK ---
    const renderDock = () => {
        // Determine States
        const hasProjects = availableProjects.length > 0;

        // Akka Check
        let canAkka = false;
        if (selectedCardIndex !== null && isMyTurn && phase === GamePhase.Playing) {
            const card = me.hand[selectedCardIndex];
            if (card) {
                let trumpSuit = gameState.bid.suit || null;
                if (gameState.bid.type === 'HOKUM' && !trumpSuit) trumpSuit = gameState.floorCard?.suit || null;
                if (canDeclareAkka(card, me.hand, gameState.tableCards, gameState.bid.type === 'SUN' ? 'SUN' : 'HOKUM', trumpSuit, gameState.currentRoundTricks || [])) {
                    canAkka = true;
                }
            }
        }

        // Sawa Check (Simple for now: Active if playing, my turn, few cards?)
        // The user previously wanted "Sawa" button mechanics. 
        // We'll enable it if it's my turn and playing. Backend handles validity.
        const canSawa = isMyTurn && phase === GamePhase.Playing;

        return (
            <div className="absolute bottom-2 sm:bottom-4 left-1/2 -translate-x-1/2 z-[100] flex items-center gap-3 sm:gap-6 bg-black/20 px-6 py-3 rounded-[2rem] border border-white/5 backdrop-blur-sm">

                {/* 1. PROJECTS (المشاريع) */}
                <button
                    onClick={() => onPlayerAction('DECLARE_PROJECT', { type: availableProjects[0] || 'SIRA' })} // Default to first or specific selection logic? Usually opens menu.
                    disabled={!hasProjects || !isMyTurn}
                    className={`${dockBtnBase} ${hasProjects && isMyTurn ? dockBtnActive : dockBtnDisabled}`}
                >
                    <div className="text-amber-400 mb-1"><Trophy size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">المشاريع</span>
                </button>

                {/* 2. AKKA (أكة) */}
                <button
                    onClick={() => {
                        if (canAkka) {
                            soundManager.playAkkaSound();
                            onPlayerAction('PLAY', { cardIndex: selectedCardIndex, metadata: { akka: true } });
                        }
                    }}
                    disabled={!canAkka}
                    className={`${dockBtnBase} ${canAkka ? dockBtnActive : dockBtnDisabled}`}
                >
                    <div className="text-rose-500 mb-1"><Megaphone size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">أكة</span>
                </button>

                {/* 3. SAWA (سوا) */}
                <button
                    onClick={handleSawa}
                    disabled={!canSawa}
                    className={`${dockBtnBase} ${canSawa ? dockBtnActive : dockBtnDisabled}`}
                >
                    <div className="text-blue-400 mb-1"><RefreshCw size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">سوا</span>
                </button>

                {/* 4. RECORD (قيدها) */}
                <button
                    onClick={handleRecord}
                    className={`${dockBtnBase} ${dockBtnActive}`} // Always active as a UI toggle?
                >
                    <div className="text-zinc-400 mb-1"><Gavel size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">قيدها</span>
                </button>

                {/* 5. EMOTE (تعابير) */}
                {onEmoteClick && (
                    <button
                        onClick={onEmoteClick}
                        className={`${dockBtnBase} ${dockBtnActive}`}
                    >
                        <div className="text-yellow-400 mb-1"><Smile size={20} /></div>
                        <span className="text-[10px] sm:text-xs font-bold font-tajawal">تعابير</span>
                    </button>
                )}

            </div>
        );
    };

    const renderBiddingDock = () => {
        // Similar Dock Style but for Bidding
        // Buttons: SUN, HOKUM, PASS, (ASHKAL/KAWESH contextually)
        return (
            <div className="absolute bottom-2 sm:bottom-4 left-1/2 -translate-x-1/2 z-[100] flex items-center gap-3 sm:gap-4 bg-black/20 px-6 py-3 rounded-[2rem] border border-white/5 backdrop-blur-sm">

                {/* SUN */}
                <button
                    onClick={() => onPlayerAction('SUN')}
                    disabled={!isMyTurn}
                    className={`${dockBtnBase} ${isMyTurn ? dockBtnActive : dockBtnDisabled}`}
                >
                    <Sun size={20} className="text-amber-400 mb-1" />
                    <span className="text-[10px] sm:text-xs font-bold">SUN</span>
                </button>

                {/* HOKUM */}
                <button
                    onClick={() => onPlayerAction('HOKUM')}
                    disabled={!isMyTurn}
                    className={`${dockBtnBase} ${isMyTurn ? dockBtnActive : dockBtnDisabled}`}
                >
                    <Gavel size={20} className="text-rose-500 mb-1" />
                    <span className="text-[10px] sm:text-xs font-bold">HOKUM</span>
                </button>

                {/* PASS */}
                <button
                    onClick={() => onPlayerAction('PASS')}
                    disabled={!isMyTurn}
                    className={`${dockBtnBase} ${isMyTurn ? dockBtnActive : dockBtnDisabled}`}
                >
                    <div className="text-zinc-400 mb-1 font-bold">X</div>
                    <span className="text-[10px] sm:text-xs font-bold">PASS</span>
                </button>

                {/* KAWESH (Redeal) */}
                {canDeclareKawesh(me.hand) && (
                    <button
                        onClick={() => onPlayerAction('KAWESH')}
                        disabled={!isMyTurn}
                        className={`${dockBtnBase} ${isMyTurn ? 'bg-purple-600 text-white animate-pulse' : dockBtnDisabled}`}
                    >
                        <RefreshCw size={20} className="text-purple-200 mb-1" />
                        <span className="text-[10px] sm:text-xs font-bold">KAWESH</span>
                    </button>
                )}
            </div>
        )
    }

    const renderDoublingDock = () => {
        // DOUBLING PHASE CONTROLS
        // Buttons: PASS, DOUBLE (x2), TRIPLE (x3), FOUR (x4), GAHWA (Win)

        // Helper to check enable state
        // In real backend, engine validates. Here just visual or simple check?
        // We'll trust backend validation via enabled buttons mostly, or just let user try.
        const canDouble = gameState.doublingLevel === 1;
        const canTriple = gameState.doublingLevel === 2;
        const canFour = gameState.doublingLevel === 3;
        const canGahwa = gameState.doublingLevel === 4;

        return (
            <div className="absolute bottom-2 sm:bottom-4 left-1/2 -translate-x-1/2 z-[100] flex items-center gap-2 sm:gap-4 bg-black/40 px-6 py-3 rounded-[2rem] border border-white/10 backdrop-blur-md shadow-2xl">

                {/* PASS (Available always to skip doubling) */}
                <button onClick={() => onPlayerAction('PASS')} disabled={!isMyTurn} className={`${dockBtnBase} ${isMyTurn ? dockBtnActive : dockBtnDisabled}`}>
                    <div className="text-zinc-400 font-bold">X</div>
                    <span className="text-[9px] font-bold">PASS</span>
                </button>

                {/* DOUBLE (x2) */}
                <button onClick={() => onPlayerAction('DOUBLE')} disabled={!isMyTurn || !canDouble} className={`${dockBtnBase} ${(isMyTurn && canDouble) ? dockBtnActive : dockBtnDisabled}`}>
                    <div className="text-amber-400 font-bold text-lg">x2</div>
                    <span className="text-[9px] font-bold">DOUBLE</span>
                </button>

                {/* TRIPLE (x3) */}
                <button onClick={() => onPlayerAction('TRIPLE')} disabled={!isMyTurn || !canTriple} className={`${dockBtnBase} ${(isMyTurn && canTriple) ? dockBtnActive : dockBtnDisabled}`}>
                    <div className="text-orange-500 font-bold text-lg">x3</div>
                    <span className="text-[9px] font-bold">TRIPLE</span>
                </button>

                {/* FOUR (x4) */}
                <button onClick={() => onPlayerAction('FOUR')} disabled={!isMyTurn || !canFour} className={`${dockBtnBase} ${(isMyTurn && canFour) ? dockBtnActive : dockBtnDisabled}`}>
                    <div className="text-red-500 font-bold text-lg">x4</div>
                    <span className="text-[9px] font-bold">FOUR</span>
                </button>

                {/* GAHWA (WIN) */}
                <button onClick={() => onPlayerAction('GAHWA')} disabled={!isMyTurn || !canGahwa} className={`${dockBtnBase} ${(isMyTurn && canGahwa) ? 'bg-amber-600 text-white animate-pulse' : dockBtnDisabled}`}>
                    <div className="text-yellow-200 font-bold text-lg">☕</div>
                    <span className="text-[9px] font-bold">GAHWA</span>
                </button>

            </div>
        );
    };

    const renderVariantDock = () => {
        // Variant Selection: OPEN (Mashru) vs CLOSED (Magfool)
        return (
            <div className="absolute bottom-2 sm:bottom-4 left-1/2 -translate-x-1/2 z-[100] flex items-center gap-4 bg-black/40 px-8 py-4 rounded-[2rem] border border-white/10 backdrop-blur-md shadow-2xl animate-in fade-in slide-in-from-bottom-4">

                <h3 className="absolute -top-10 left-1/2 -translate-x-1/2 text-white font-bold bg-black/50 px-3 py-1 rounded-full text-xs">Choose Variant</h3>

                {/* OPEN (Mashru) */}
                <button onClick={() => onPlayerAction('OPEN')} disabled={!isMyTurn} className={`${dockBtnBase} w-20 ${isMyTurn ? 'bg-emerald-600 hover:bg-emerald-500' : dockBtnDisabled}`}>
                    <div className="text-white font-bold text-lg">🔓</div>
                    <span className="text-[9px] font-bold text-white">OPEN</span>
                </button>

                {/* CLOSED (Magfool) */}
                <button onClick={() => onPlayerAction('CLOSED')} disabled={!isMyTurn} className={`${dockBtnBase} w-20 ${isMyTurn ? 'bg-zinc-700 hover:bg-zinc-600' : dockBtnDisabled}`}>
                    <div className="text-zinc-300 font-bold text-lg">🔒</div>
                    <span className="text-[9px] font-bold text-zinc-300">CLOSED</span>
                </button>

            </div>
        )
    }

    if (phase === GamePhase.Bidding) {
        return renderBiddingDock();
    }

    if (phase === GamePhase.Doubling) {
        return renderDoublingDock();
    }

    // Default: Playing Dock (Always visible in Playing, even if not my turn, just disabled)
    // Only hide if NOT playing and NOT bidding (e.g. Waiting?)
    // Default: Playing Dock (Always visible in Playing, even if not my turn, just disabled)
    // Only hide if NOT playing and NOT bidding (e.g. Waiting?)
    if (phase === GamePhase.Playing) {
        return renderDock();
    }

    if (phase === GamePhase.VariantSelection) {
        return renderVariantDock();
    }

    return null;
};

export default ActionBar;
