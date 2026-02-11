import React, { useState } from 'react';
import { GameState, GamePhase, Suit, Player } from '../types';
import { Spade, Heart, Club, Diamond } from './SuitIcons';
import { Gavel, Megaphone, Sun, RefreshCw, X, Trophy, Smile } from 'lucide-react';
import { canDeclareAkka, canDeclareKawesh, scanHandForAkka } from '../utils/gameLogic';
import { soundManager } from '../services/SoundManager';
import { motion, AnimatePresence } from 'framer-motion';

interface ActionBarProps {
    gameState: GameState;
    me: Player;
    isMyTurn: boolean;
    onPlayerAction: (action: string, payload?: any) => void;
    availableProjects: string[];
    selectedCardIndex: number | null;
    settings?: any;
    onEmoteClick?: () => void;
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

    // --- BUTTON STYLES ---
    const dockBtnBase = "flex flex-col items-center justify-center w-[2.0rem] h-[2.0rem] sm:w-[2.5rem] sm:h-[2.5rem] rounded-2xl backdrop-blur-md border border-white/10 shadow-lg relative overflow-hidden";
    const dockBtnActive = "bg-zinc-800 text-white";
    const dockBtnDisabled = "bg-zinc-900/40 text-white/20 cursor-not-allowed grayscale";

    // --- ANIMATION VARIANTS ---
    const dockVariants = {
        hidden: { y: 100, opacity: 0, x: "-50%" },
        visible: {
            y: 0,
            opacity: 1,
            x: "-50%",
            transition: { type: "spring", stiffness: 300, damping: 30 }
        } as any,
        exit: {
            y: 100,
            opacity: 0,
            x: "-50%",
            transition: { duration: 0.2 }
        }
    };

    const btnVariants = {
        hover: { scale: 1.1, backgroundColor: "#3f3f46" }, // zinc-700
        tap: { scale: 0.95 },
        disabled: { scale: 1 }
    };

    // --- ACTIONS ---
    const handleSawa = () => onPlayerAction('SAWA_CLAIM');
    const handleRecord = () => {
        soundManager.playClick();
        onPlayerAction('QAYD_TRIGGER');
    };

    const ActionButton = ({ onClick, disabled, className, children, activeClass = dockBtnActive, ...props }: any) => (
        <motion.button
            onClick={onClick}
            disabled={disabled}
            variants={btnVariants}
            whileHover={!disabled ? "hover" : "disabled"}
            whileTap={!disabled ? "tap" : "disabled"}
            className={`${dockBtnBase} ${!disabled ? activeClass : dockBtnDisabled} ${className || ''}`}
            {...props}
        >
            {children}
            {!disabled && (
                <motion.div
                    className="absolute inset-0 bg-white/10"
                    initial={{ scale: 0, opacity: 0 }}
                    whileTap={{ scale: 2, opacity: 0.3 }}
                    transition={{ duration: 0.4 }}
                />
            )}
        </motion.button>
    );

    // --- PROJECT LABELS MAP ---
    const PROJECT_LABELS: Record<string, string> = {
        'SIRA': 'سرا',
        'FIFTY': '50',
        'HUNDRED': '100',
        'FOUR_HUNDRED': '400',
    };

    // --- PROJECT MENU STATE ---
    const [showProjectMenu, setShowProjectMenu] = useState(false);

    // --- RENDER DOCKS ---
    const renderDock = () => {
        const hasProjects = availableProjects.length > 0;

        let canAkka = false;
        if (isMyTurn && phase === GamePhase.Playing && gameState.bid.type === 'HOKUM') {
            // Akka is HOKUM-only. Determine trump suit.
            const trumpSuit = gameState.trumpSuit || gameState.bid.suit || gameState.floorCard?.suit || null;

            // Only show Akka button when leading (table empty) — scanHandForAkka checks this too
            if ((gameState.tableCards || []).length === 0) {
                canAkka = scanHandForAkka(
                    me.hand,
                    gameState.tableCards || [],
                    'HOKUM',
                    trumpSuit,
                    gameState.currentRoundTricks || []
                );
            }
        }
        const canSawa = isMyTurn && phase === GamePhase.Playing;

        return (
            <motion.div
                key="playing-dock"
                variants={dockVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="absolute bottom-0 sm:bottom-1 left-1/2 z-[1000] flex items-center gap-3 sm:gap-6 bg-black/20 px-6 py-3 rounded-t-[2rem] border-t border-x border-white/5 backdrop-blur-sm"
            >
                {/* 1. PROJECTS */}
                <div className="relative">
                    <ActionButton
                        onClick={() => {
                            if (hasProjects && isMyTurn) {
                                setShowProjectMenu(!showProjectMenu);
                            }
                        }}
                        disabled={!hasProjects || !isMyTurn}
                        data-testid="btn-projects"
                    >
                        <div className="text-amber-400 mb-1"><Trophy size={20} /></div>
                        <span className="text-[10px] sm:text-xs font-bold font-tajawal">المشاريع</span>
                        {hasProjects && (
                            <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-black text-[8px] font-black rounded-full flex items-center justify-center shadow">
                                {availableProjects.length}
                            </span>
                        )}
                    </ActionButton>

                    {/* Project Type Popup */}
                    {showProjectMenu && (
                        <motion.div
                            initial={{ opacity: 0, y: 10, scale: 0.9 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 10, scale: 0.9 }}
                            className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-zinc-900/95 backdrop-blur-lg rounded-xl border border-amber-500/30 shadow-2xl p-2 flex flex-col gap-1 min-w-[5rem] z-[1100]"
                        >
                            {availableProjects.map((projType) => (
                                <button
                                    key={projType}
                                    onClick={() => {
                                        onPlayerAction('DECLARE_PROJECT', { type: projType });
                                        setShowProjectMenu(false);
                                    }}
                                    className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-600/80 to-yellow-600/80 hover:from-amber-500 hover:to-yellow-500 text-white font-bold text-sm transition-all hover:scale-105 active:scale-95 text-center font-tajawal"
                                >
                                    {PROJECT_LABELS[projType] || projType}
                                </button>
                            ))}
                        </motion.div>
                    )}
                </div>

                {/* 2. AKKA */}
                <ActionButton
                    onClick={() => {
                        if (canAkka) {
                            soundManager.playAkkaSound();
                            // Standalone Akka Action
                            onPlayerAction('AKKA');
                        }
                    }}
                    disabled={!canAkka}
                    data-testid="btn-akka"
                >
                    <div className="text-rose-500 mb-1"><Megaphone size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">أكة</span>
                </ActionButton>

                {/* 3. SAWA */}
                <ActionButton
                    onClick={handleSawa}
                    disabled={!canSawa}
                    data-testid="btn-sawa"
                >
                    <div className="text-blue-400 mb-1"><RefreshCw size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">سوا</span>
                </ActionButton>

                {/* 4. RECORD (Qayd) — Only during PLAYING, not while locked */}
                <ActionButton
                    onClick={handleRecord}
                    disabled={phase !== GamePhase.Playing || gameState.isLocked}
                    data-testid="btn-qayd"
                >
                    <div className="text-zinc-400 mb-1"><Gavel size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">قيدها</span>
                </ActionButton>

                {/* 5. EMOTE */}
                {onEmoteClick && (
                    <ActionButton onClick={onEmoteClick}>
                        <div className="text-yellow-400 mb-1"><Smile size={20} /></div>
                        <span className="text-[10px] sm:text-xs font-bold font-tajawal">تعابير</span>
                    </ActionButton>
                )}
            </motion.div>
        );
    };

    const renderBiddingDock = () => (
        <motion.div
            key="bidding-dock"
            variants={dockVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute bottom-0 sm:bottom-1 left-1/2 z-[100] flex items-center gap-3 sm:gap-4 bg-black/20 px-6 py-3 rounded-t-[2rem] border-t border-x border-white/5 backdrop-blur-sm"
        >
            <ActionButton onClick={() => onPlayerAction('SUN')} disabled={!isMyTurn}>
                <Sun size={20} className="text-amber-400 mb-1" />
                <span className="text-[10px] sm:text-xs font-bold">SUN</span>
            </ActionButton>

            <ActionButton onClick={() => onPlayerAction('HOKUM')} disabled={!isMyTurn}>
                <Gavel size={20} className="text-rose-500 mb-1" />
                <span className="text-[10px] sm:text-xs font-bold">HOKUM</span>
            </ActionButton>

            <ActionButton onClick={() => onPlayerAction('PASS')} disabled={!isMyTurn}>
                <div className="text-zinc-400 mb-1 font-bold">X</div>
                <span className="text-[10px] sm:text-xs font-bold">PASS</span>
            </ActionButton>

            {canDeclareKawesh(me.hand) && (
                <ActionButton
                    onClick={() => onPlayerAction('KAWESH')}
                    disabled={!isMyTurn}
                    activeClass="bg-purple-600 text-white animate-pulse"
                >
                    <RefreshCw size={20} className="text-purple-200 mb-1" />
                    <span className="text-[10px] sm:text-xs font-bold">KAWESH</span>
                </ActionButton>
            )}
        </motion.div>
    );

    const renderDoublingDock = () => {
        const canDouble = gameState.doublingLevel === 1;
        const canTriple = gameState.doublingLevel === 2;
        const canFour = gameState.doublingLevel === 3;
        const canGahwa = gameState.doublingLevel === 4;

        return (
            <motion.div
                key="doubling-dock"
                variants={dockVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="absolute bottom-0 sm:bottom-1 left-1/2 z-[100] flex items-center gap-2 sm:gap-4 bg-black/40 px-6 py-3 rounded-t-[2rem] border-t border-x border-white/10 backdrop-blur-md shadow-2xl"
            >
                <ActionButton onClick={() => onPlayerAction('PASS')} disabled={!isMyTurn}>
                    <div className="text-zinc-400 font-bold">X</div>
                    <span className="text-[9px] font-bold">PASS</span>
                </ActionButton>

                <ActionButton onClick={() => onPlayerAction('DOUBLE')} disabled={!isMyTurn || !canDouble}>
                    <div className="text-amber-400 font-bold text-lg">x2</div>
                    <span className="text-[9px] font-bold">DOUBLE</span>
                </ActionButton>

                <ActionButton onClick={() => onPlayerAction('TRIPLE')} disabled={!isMyTurn || !canTriple}>
                    <div className="text-orange-500 font-bold text-lg">x3</div>
                    <span className="text-[9px] font-bold">TRIPLE</span>
                </ActionButton>

                <ActionButton onClick={() => onPlayerAction('FOUR')} disabled={!isMyTurn || !canFour}>
                    <div className="text-red-500 font-bold text-lg">x4</div>
                    <span className="text-[9px] font-bold">FOUR</span>
                </ActionButton>

                <ActionButton
                    onClick={() => onPlayerAction('GAHWA')}
                    disabled={!isMyTurn || !canGahwa}
                    activeClass="bg-amber-600 text-white animate-pulse"
                >
                    <div className="text-yellow-200 font-bold text-lg">☕</div>
                    <span className="text-[9px] font-bold">GAHWA</span>
                </ActionButton>
            </motion.div>
        );
    };

    const renderVariantDock = () => (
        <motion.div
            key="variant-dock"
            variants={dockVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute bottom-0 sm:bottom-1 left-1/2 z-[100] flex items-center gap-4 bg-black/40 px-8 py-4 rounded-t-[2rem] border-t border-x border-white/10 backdrop-blur-md shadow-2xl"
        >
            <h3 className="absolute -top-10 left-1/2 -translate-x-1/2 text-white font-bold bg-black/50 px-3 py-1 rounded-full text-xs">Choose Variant</h3>

            <ActionButton
                onClick={() => onPlayerAction('OPEN')}
                disabled={!isMyTurn}
                className="w-20"
                activeClass="bg-emerald-600 hover:bg-emerald-500"
            >
                <div className="text-white font-bold text-lg">🔓</div>
                <span className="text-[9px] font-bold text-white">OPEN</span>
            </ActionButton>

            <ActionButton
                onClick={() => onPlayerAction('CLOSED')}
                disabled={!isMyTurn}
                className="w-20"
                activeClass="bg-zinc-700 hover:bg-zinc-600"
            >
                <div className="text-zinc-300 font-bold text-lg">🔒</div>
                <span className="text-[9px] font-bold text-zinc-300">CLOSED</span>
            </ActionButton>
        </motion.div>
    );

    return (
        <AnimatePresence mode="wait">
            {(phase === GamePhase.Bidding || gameState.biddingPhase === 'GABLAK_WINDOW') && renderBiddingDock()}
            {phase === GamePhase.Doubling && renderDoublingDock()}
            {phase === GamePhase.Playing && renderDock()}
            {phase === GamePhase.VariantSelection && renderVariantDock()}
        </AnimatePresence>
    );
};

export default ActionBar;
