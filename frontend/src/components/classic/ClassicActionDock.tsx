import React, { useState } from 'react';
import { motion, AnimatePresence, Variants, HTMLMotionProps } from 'framer-motion';
import { GameState, GamePhase, Player } from '../../types';
import { canDeclareAkka, canDeclareKawesh, scanHandForAkka } from '../../utils/gameLogic';
import { soundManager } from '../../services/SoundManager';
import { Trophy, Megaphone, RefreshCw, Gavel, Smile, Sun } from 'lucide-react';

interface ClassicActionDockProps {
    gameState: GameState;
    me: Player;
    isMyTurn: boolean;
    onPlayerAction: (action: string, payload?: any) => void;
    availableProjects: string[];
    selectedCardIndex: number | null;
    settings?: any;
    onEmoteClick?: () => void;
}

const PROJECT_LABELS: Record<string, string> = {
    'SIRA': 'سرا',
    'FIFTY': '50',
    'HUNDRED': '100',
    'FOUR_HUNDRED': '400',
};

export default function ClassicActionDock({
    gameState,
    me,
    isMyTurn,
    onPlayerAction,
    availableProjects,
    selectedCardIndex,
    settings,
    onEmoteClick
}: ClassicActionDockProps) {
    const { phase } = gameState;
    const [showProjectMenu, setShowProjectMenu] = useState(false);

    const hasProjects = availableProjects.length > 0;

    let canAkka = false;
    if (isMyTurn && phase === GamePhase.Playing && gameState.bid.type === 'HOKUM') {
        const trumpSuit = gameState.trumpSuit || gameState.bid.suit || gameState.floorCard?.suit || null;
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

    const dockVariants: Variants = {
        hidden: { y: 80, opacity: 0 },
        visible: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 300, damping: 30 } },
        exit: { y: 80, opacity: 0, transition: { duration: 0.2 } }
    };

    // ─── Bidding Dock ───
    if (phase === GamePhase.Bidding || gameState.biddingPhase === 'GABLAK_WINDOW') {
        return (
            <motion.div
                key="km-bidding"
                variants={dockVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="classic-dock km-glass-strong"
            >
                <button className="km-bid-btn sun" onClick={() => onPlayerAction('SUN')} disabled={!isMyTurn}>
                    <Sun size={18} style={{ marginBottom: 2 }} /> صن
                </button>
                <button className="km-bid-btn hokum" onClick={() => onPlayerAction('HOKUM')} disabled={!isMyTurn}>
                    <Gavel size={18} style={{ marginBottom: 2 }} /> حكم
                </button>
                <button className="km-bid-btn" onClick={() => onPlayerAction('PASS')} disabled={!isMyTurn}>
                    ✕ بس
                </button>
                {canDeclareKawesh(me.hand) && (
                    <button
                        className="km-bid-btn"
                        onClick={() => onPlayerAction('KAWESH')}
                        disabled={!isMyTurn}
                        style={{ background: 'linear-gradient(135deg, rgba(147, 51, 234, 0.3), rgba(126, 34, 206, 0.2))', borderColor: 'rgba(147, 51, 234, 0.4)' }}
                    >
                        <RefreshCw size={18} /> كوش
                    </button>
                )}
            </motion.div>
        );
    }

    // ─── Doubling Dock ───
    if (phase === GamePhase.Doubling) {
        const canDouble = gameState.doublingLevel === 1;
        const canTriple = gameState.doublingLevel === 2;
        const canFour = gameState.doublingLevel === 3;
        const canGahwa = gameState.doublingLevel === 4;

        return (
            <motion.div
                key="km-doubling"
                variants={dockVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="classic-dock km-glass-strong"
            >
                <button className="km-bid-btn" onClick={() => onPlayerAction('PASS')} disabled={!isMyTurn}>✕ بس</button>
                <button className="km-bid-btn" onClick={() => onPlayerAction('DOUBLE')} disabled={!isMyTurn || !canDouble}>x2 دبل</button>
                <button className="km-bid-btn" onClick={() => onPlayerAction('TRIPLE')} disabled={!isMyTurn || !canTriple}>x3</button>
                <button className="km-bid-btn" onClick={() => onPlayerAction('FOUR')} disabled={!isMyTurn || !canFour}>x4</button>
                <button className="km-bid-btn" onClick={() => onPlayerAction('GAHWA')} disabled={!isMyTurn || !canGahwa}
                    style={{ background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.4), rgba(180, 100, 10, 0.3))' }}>
                    ☕ قهوة
                </button>
            </motion.div>
        );
    }

    // ─── Variant Selection Dock ───
    if (phase === GamePhase.VariantSelection) {
        return (
            <motion.div
                key="km-variant"
                variants={dockVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="classic-dock km-glass-strong"
            >
                <button className="km-bid-btn" onClick={() => onPlayerAction('OPEN')} disabled={!isMyTurn}
                    style={{ background: 'linear-gradient(135deg, rgba(39, 174, 96, 0.3), rgba(22, 160, 80, 0.2))', borderColor: 'rgba(39, 174, 96, 0.4)' }}>
                    🔓 مفتوح
                </button>
                <button className="km-bid-btn" onClick={() => onPlayerAction('CLOSED')} disabled={!isMyTurn}>
                    🔒 مغلق
                </button>
            </motion.div>
        );
    }

    // ─── Playing Dock ───
    if (phase !== GamePhase.Playing) return null;

    return (
        <AnimatePresence mode="wait">
            <motion.div
                key="km-playing"
                variants={dockVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="classic-dock km-glass-strong"
            >
                {/* Projects */}
                <div style={{ position: 'relative' }}>
                    <button
                        className="km-dock-btn"
                        onClick={() => { if (hasProjects && isMyTurn) setShowProjectMenu(!showProjectMenu); }}
                        disabled={!hasProjects || !isMyTurn}
                    >
                        <span className="km-dock-icon" style={{ color: 'var(--km-gold)' }}>
                            <Trophy size={20} />
                        </span>
                        <span className="km-dock-label">المشاريع</span>
                        {hasProjects && (
                            <span className="km-trick-badge">{availableProjects.length}</span>
                        )}
                    </button>

                    {showProjectMenu && (
                        <motion.div
                            initial={{ opacity: 0, y: 10, scale: 0.9 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            style={{
                                position: 'absolute',
                                bottom: '110%',
                                left: '50%',
                                transform: 'translateX(-50%)',
                                background: 'var(--km-bg-panel)',
                                borderRadius: 12,
                                border: '1px solid var(--km-border-active)',
                                padding: 8,
                                display: 'flex',
                                flexDirection: 'column',
                                gap: 4,
                                minWidth: 80,
                                zIndex: 200
                            }}
                        >
                            {availableProjects.map(p => (
                                <button
                                    key={p}
                                    onClick={() => { onPlayerAction('DECLARE_PROJECT', { type: p }); setShowProjectMenu(false); }}
                                    style={{
                                        padding: '6px 14px',
                                        borderRadius: 8,
                                        background: 'linear-gradient(135deg, rgba(212, 168, 83, 0.3), rgba(139, 105, 20, 0.2))',
                                        border: '1px solid var(--km-border)',
                                        color: 'var(--km-gold-bright)',
                                        fontWeight: 700,
                                        fontSize: 13,
                                        cursor: 'pointer'
                                    }}
                                >
                                    {PROJECT_LABELS[p] || p}
                                </button>
                            ))}
                        </motion.div>
                    )}
                </div>

                {/* Akka */}
                <button
                    className="km-dock-btn"
                    onClick={() => { if (canAkka) { soundManager.playAkkaSound(); onPlayerAction('AKKA'); } }}
                    disabled={!canAkka}
                >
                    <span className="km-dock-icon" style={{ color: '#e74c3c' }}><Megaphone size={20} /></span>
                    <span className="km-dock-label">أكة</span>
                </button>

                {/* Sawa */}
                <button
                    className="km-dock-btn"
                    onClick={() => onPlayerAction('SAWA_CLAIM')}
                    disabled={!canSawa}
                >
                    <span className="km-dock-icon" style={{ color: 'var(--km-accent-blue)' }}><RefreshCw size={20} /></span>
                    <span className="km-dock-label">سوا</span>
                </button>

                {/* Qayd */}
                <button
                    className="km-dock-btn"
                    onClick={() => { soundManager.playClick(); onPlayerAction('QAYD_TRIGGER'); }}
                    disabled={phase !== GamePhase.Playing || gameState.isLocked}
                >
                    <span className="km-dock-icon" style={{ color: 'var(--km-text-muted)' }}><Gavel size={20} /></span>
                    <span className="km-dock-label">قيدها</span>
                </button>

                {/* Emotes */}
                {onEmoteClick && (
                    <button className="km-dock-btn" onClick={onEmoteClick}>
                        <span className="km-dock-icon" style={{ color: 'var(--km-gold)' }}><Smile size={20} /></span>
                        <span className="km-dock-label">تعابير</span>
                    </button>
                )}
            </motion.div>
        </AnimatePresence>
    );
}
