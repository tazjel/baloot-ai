import React from 'react';
import { GameState, GamePhase, Suit, Player } from '../types';
import { Spade, Heart, Club, Diamond } from './SuitIcons';
import { Gavel, Megaphone, Sun, RefreshCw, X, Trophy, Smile } from 'lucide-react';
import { canDeclareAkka, canDeclareKawesh } from '../utils/gameLogic';
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
        },
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
    const handleRecord = () => console.log("Record/Qaydha clicked");

    const ActionButton = ({ onClick, disabled, className, children, activeClass = dockBtnActive }: any) => (
        <motion.button
            onClick={onClick}
            disabled={disabled}
            variants={btnVariants}
            whileHover={!disabled ? "hover" : "disabled"}
            whileTap={!disabled ? "tap" : "disabled"}
            className={`${dockBtnBase} ${!disabled ? activeClass : dockBtnDisabled} ${className || ''}`}
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

    // --- RENDER DOCKS ---
    const renderDock = () => {
        const hasProjects = availableProjects.length > 0;

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
        const canSawa = isMyTurn && phase === GamePhase.Playing;

        return (
            <motion.div
                key="playing-dock"
                variants={dockVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="absolute bottom-2 sm:bottom-4 left-1/2 z-[100] flex items-center gap-3 sm:gap-6 bg-black/20 px-6 py-3 rounded-[2rem] border border-white/5 backdrop-blur-sm"
            >
                {/* 1. PROJECTS */}
                <ActionButton
                    onClick={() => onPlayerAction('DECLARE_PROJECT', { type: availableProjects[0] || 'SIRA' })}
                    disabled={!hasProjects || !isMyTurn}
                >
                    <div className="text-amber-400 mb-1"><Trophy size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">المشاريع</span>
                </ActionButton>

                {/* 2. AKKA */}
                <ActionButton
                    onClick={() => {
                        if (canAkka) {
                            soundManager.playAkkaSound();
                            onPlayerAction('PLAY', { cardIndex: selectedCardIndex, metadata: { akka: true } });
                        }
                    }}
                    disabled={!canAkka}
                >
                    <div className="text-rose-500 mb-1"><Megaphone size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">أكة</span>
                </ActionButton>

                {/* 3. SAWA */}
                <ActionButton
                    onClick={handleSawa}
                    disabled={!canSawa}
                >
                    <div className="text-blue-400 mb-1"><RefreshCw size={20} /></div>
                    <span className="text-[10px] sm:text-xs font-bold font-tajawal">سوا</span>
                </ActionButton>

                {/* 4. RECORD */}
                <ActionButton onClick={handleRecord}>
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
            className="absolute bottom-2 sm:bottom-4 left-1/2 z-[100] flex items-center gap-3 sm:gap-4 bg-black/20 px-6 py-3 rounded-[2rem] border border-white/5 backdrop-blur-sm"
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
                className="absolute bottom-2 sm:bottom-4 left-1/2 z-[100] flex items-center gap-2 sm:gap-4 bg-black/40 px-6 py-3 rounded-[2rem] border border-white/10 backdrop-blur-md shadow-2xl"
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
            className="absolute bottom-2 sm:bottom-4 left-1/2 z-[100] flex items-center gap-4 bg-black/40 px-8 py-4 rounded-[2rem] border border-white/10 backdrop-blur-md shadow-2xl"
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
            {phase === GamePhase.Bidding && renderBiddingDock()}
            {phase === GamePhase.Doubling && renderDoublingDock()}
            {phase === GamePhase.Playing && renderDock()}
            {phase === GamePhase.VariantSelection && renderVariantDock()}
        </AnimatePresence>
    );
};

export default ActionBar;
