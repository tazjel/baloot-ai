import React from 'react';
import { motion } from 'framer-motion';
import { GameState, GamePhase, Player, CardModel, Bid } from '../../types';
import Card from '../Card';
import { Plus } from 'lucide-react';
import { getPlayedCardAnimation } from '../../utils/animationUtils';

interface ClassicArenaProps {
    gameState: GameState;
    players: Player[];
    me: Player;
    currentTurnIndex: number;
    tableCards: GameState['tableCards'];
    floorCard: CardModel | null;
    bid: Bid;
    declarations: GameState['declarations'];
    akkaState: GameState['akkaState'];
    cardSkin: string;
    dealPhase: 'IDLE' | 'DEAL_1' | 'DEAL_2' | 'FLOOR' | 'DONE';
    timeLeft: number;
    turnDuration: number;
    showProjects: boolean;
    isProjectRevealing: boolean;
    trickCount: number;
    playerSpeech: Record<number, string | null>;
    onAddBot?: () => void;
    isPaused: boolean;
}

export default function ClassicArena({
    gameState,
    players,
    me,
    currentTurnIndex,
    tableCards,
    floorCard,
    bid,
    declarations,
    akkaState,
    cardSkin,
    dealPhase,
    timeLeft,
    turnDuration,
    showProjects,
    isProjectRevealing,
    trickCount,
    playerSpeech,
    onAddBot,
    isPaused = false,
}: ClassicArenaProps) {
    const partner = players[2];
    const rightPlayer = players[1];
    const leftPlayer = players[3];

    // Player avatar renderer
    const renderPlayer = (player: Player, position: 'top' | 'left' | 'right') => {
        if (!player) return null;
        const isActive = currentTurnIndex === player.index;
        const posClass = position === 'top' ? 'km-player-top' : position === 'left' ? 'km-player-left' : 'km-player-right';
        const speech = playerSpeech[player.index];

        return (
            <div className={posClass}>
                <div className={`km-avatar-ring ${isActive ? 'active' : ''}`}>
                    <img src={player.avatar} alt={player.name} onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                    }} />
                    {/* Turn timer ring */}
                    {isActive && (
                        <svg style={{ position: 'absolute', inset: -4, width: 64, height: 64 }} viewBox="0 0 64 64">
                            <circle cx="32" cy="32" r="30" fill="none" stroke="rgba(212,168,83,0.2)" strokeWidth="2" />
                            <circle cx="32" cy="32" r="30" fill="none" stroke="var(--km-gold-bright)" strokeWidth="2.5"
                                strokeDasharray={`${(timeLeft / turnDuration) * 188} 188`}
                                strokeLinecap="round"
                                transform="rotate(-90 32 32)"
                                style={{ transition: 'stroke-dasharray 1s linear' }}
                            />
                        </svg>
                    )}
                </div>
                <div className="km-avatar-name">{player.name}</div>
                {player.isBot && (
                    <div className="km-avatar-coins">🤖 بوت</div>
                )}

                {/* Speech Bubble */}
                {speech && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.8, y: 5 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        style={{
                            marginTop: 4,
                            padding: '4px 10px',
                            borderRadius: 10,
                            background: 'var(--km-bg-panel)',
                            border: '1px solid var(--km-border)',
                            fontSize: 11,
                            color: 'var(--km-text-secondary)',
                            maxWidth: 120,
                            textAlign: 'center',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                        }}
                    >
                        {speech}
                    </motion.div>
                )}

                {/* Trick count */}
                {gameState.phase === GamePhase.Playing && (
                    <div className="km-avatar-coins" style={{ marginTop: 2 }}>
                        🃏 {player.score || 0}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="classic-arena">
            {/* Center: Waiting State */}
            {gameState.phase === GamePhase.Waiting && (
                <div className="km-waiting" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 50 }}>
                    <h2>بانتظار اللاعبين...</h2>
                    <div style={{ fontSize: 14 }}>{players.length}/4 لاعبين</div>
                    {onAddBot && (
                        <button onClick={onAddBot}>
                            <Plus size={18} style={{ display: 'inline', verticalAlign: 'middle', marginLeft: 6 }} />
                            إضافة بوت
                        </button>
                    )}
                </div>
            )}

            {/* Players */}
            {renderPlayer(partner, 'top')}
            {renderPlayer(leftPlayer, 'left')}
            {renderPlayer(rightPlayer, 'right')}

            {/* Floor Card */}
            {floorCard && dealPhase !== 'IDLE' && dealPhase !== 'DEAL_1' && dealPhase !== 'DEAL_2' && (
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -70%)', zIndex: 40 }}>
                    <div className="km-floor-glow">
                        <div style={{ width: 90, height: 133 }}>
                            <Card
                                card={floorCard}
                                className="shadow-2xl"
                                isPlayable={false}
                                skin={cardSkin}
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* Played Cards (Cross Formation) */}
            <div className="km-center-cards">
                {tableCards && tableCards.map((played, idx) => {
                    if (!played || !played.card) return null;
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
                        <motion.div key={`km-played-${idx}-${played.card.id}`}
                            initial={initial}
                            animate={animate}
                            exit={exit}
                            transition={{ type: "spring", stiffness: 350, damping: 25, mass: 0.8 }}
                            className={animClass}
                            style={{
                                ...style,
                                position: 'absolute'
                            }}>
                            <div style={{ width: 80, height: 118 }}>
                                <Card
                                    card={played.card}
                                    className="shadow-2xl"
                                    isPlayable={false}
                                    skin={cardSkin}
                                />
                            </div>
                        </motion.div>
                    );
                })}

                {/* Sweeping trick cards */}
                {gameState.lastTrick && gameState.lastTrick.cards && gameState.lastTrick.cards.map((played, idx) => {
                    if (!played || !played.card) return null;
                    const playerObj = players.find(p => p && p.position === played?.playedBy);
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

                    let sweepClass = 'sweep-bottom';
                    if (isPartnerWinner) sweepClass = 'sweep-top';
                    else if (isRightWinner) sweepClass = 'sweep-right';
                    else if (isLeftWinner) sweepClass = 'sweep-left';

                    return (
                        <div key={`km-swept-${idx}`}
                            className={`absolute ${sweepClass}`}
                            style={{ ...style, zIndex: 50 + idx, position: 'absolute' }}>
                            <div style={{ width: 70, height: 103 }}>
                                <Card
                                    card={played.card}
                                    className="shadow-2xl opacity-90"
                                    skin={cardSkin}
                                />
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Contract / GameMode Indicator */}
            {bid?.type && gameState.phase === GamePhase.Playing && (
                <div style={{
                    position: 'absolute',
                    top: 16,
                    left: 16,
                    padding: '6px 14px',
                    borderRadius: 12,
                    background: bid.type === 'SUN' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                    border: `1px solid ${bid.type === 'SUN' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                    color: bid.type === 'SUN' ? '#f59e0b' : '#ef4444',
                    fontSize: 13,
                    fontWeight: 700,
                    zIndex: 10,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6
                }}>
                    {bid.type === 'SUN' ? '☀️' : '⚖️'} {bid.type === 'SUN' ? 'صن' : 'حكم'}
                    {gameState.trumpSuit && <span style={{ fontSize: 16 }}>{gameState.trumpSuit}</span>}
                </div>
            )}
        </div>
    );
}
