import React from 'react';
import { motion } from 'framer-motion';
import { GameState, GamePhase, Player, PlayerPosition, Bid, CardModel } from '../../types';
import Card from '../Card';
import { Plus } from 'lucide-react';
import { VISUAL_ASSETS } from '../../constants';
import premiumWood from '../../assets/premium_wood_texture.png';
import premiumFelt from '../../assets/premium_felt_texture.png';
import { getPlayedCardAnimation } from '../../utils/animationUtils';
import PlayerAvatar from './PlayerAvatar';

interface GameArenaProps {
    gameState: GameState;
    players: Player[];
    me: Player;
    currentTurnIndex: number;
    tableCards: GameState['tableCards'];
    floorCard: CardModel | null;
    bid: Bid;
    declarations: GameState['declarations'];
    akkaState: GameState['akkaState'];
    // Visual
    tableSkin: string;
    cardSkin: string;
    dealPhase: 'IDLE' | 'DEAL_1' | 'DEAL_2' | 'FLOOR' | 'DONE';
    // Timer
    timeLeft: number;
    turnDuration: number;
    // Projects
    showProjects: boolean;
    isProjectRevealing: boolean;
    trickCount: number;
    // Speech
    playerSpeech: Record<number, string | null>;
    // Actions
    onAddBot?: () => void;
    isPaused: boolean;
}

export default function GameArena({
    gameState,
    players,
    me,
    currentTurnIndex,
    tableCards,
    floorCard,
    bid,
    declarations,
    akkaState,
    tableSkin,
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
}: GameArenaProps) {
    const partner = players[2];
    const rightPlayer = players[1];
    const leftPlayer = players[3];

    return (
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

                    {/* --- PLAYERS (Top, Left, Right) --- */}
                    {partner && (
                        <PlayerAvatar
                            player={partner}
                            isCurrentTurn={currentTurnIndex === partner.index}
                            position="top"
                            timeLeft={timeLeft}
                            totalTime={turnDuration}
                            declarations={declarations}
                            isProjectRevealing={isProjectRevealing}
                            bid={bid}
                            doublingLevel={gameState.doublingLevel}
                            showProjects={showProjects}
                            trickCount={trickCount}
                            speechText={playerSpeech[partner.index]}
                            isPaused={isPaused}
                        />
                    )}

                    {leftPlayer && (
                        <PlayerAvatar
                            player={leftPlayer}
                            isCurrentTurn={currentTurnIndex === leftPlayer.index}
                            position="left"
                            timeLeft={timeLeft}
                            totalTime={turnDuration}
                            declarations={declarations}
                            isProjectRevealing={isProjectRevealing}
                            bid={bid}
                            doublingLevel={gameState.doublingLevel}
                            showProjects={showProjects}
                            trickCount={trickCount}
                            speechText={playerSpeech[leftPlayer.index]}
                            akkaState={akkaState}
                        />
                    )}

                    {rightPlayer && (
                        <PlayerAvatar
                            player={rightPlayer}
                            isCurrentTurn={currentTurnIndex === rightPlayer.index}
                            position="right"
                            timeLeft={timeLeft}
                            totalTime={turnDuration}
                            declarations={declarations}
                            isProjectRevealing={isProjectRevealing}
                            bid={bid}
                            doublingLevel={gameState.doublingLevel}
                            showProjects={showProjects}
                            trickCount={trickCount}
                            speechText={playerSpeech[rightPlayer.index]}
                            akkaState={akkaState}
                        />
                    )}

                    {/* --- FLOOR CARD --- */}
                    {floorCard && dealPhase !== 'IDLE' && dealPhase !== 'DEAL_1' && dealPhase !== 'DEAL_2' && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-30 pb-32 sm:pb-40">
                            <div className="relative animate-floor-reveal">
                                <div className="absolute -inset-4 sm:-inset-5 md:-inset-6 bg-gradient-to-r from-yellow-300 via-amber-400 to-yellow-500 rounded-xl blur-xl opacity-70 animate-pulse"></div>
                                <div className="absolute -inset-3 sm:-inset-4 bg-yellow-400/40 rounded-lg blur-lg"></div>
                                <div className="absolute -inset-2 rounded-lg border-3 sm:border-4 border-yellow-400 opacity-60 animate-ping"></div>
                                <div className="absolute -inset-1 rounded-lg border-2 border-amber-300 opacity-40 animate-ping" style={{ animationDelay: '0.5s' }}></div>
                                <Card
                                    card={floorCard}
                                    className="h-32 w-24 sm:h-36 sm:w-26 md:h-40 md:w-28 shadow-2xl"
                                    isPlayable={false}
                                    skin={cardSkin}
                                />
                            </div>
                        </div>
                    )}

                    {/* --- PLAYED CARDS (CROSS FORMATION) --- */}
                    <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                        {/* Active Cards */}
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

                            const isTrumpCard = gameState.gameMode === 'HOKUM' && gameState.trumpSuit && played.card.suit === gameState.trumpSuit;

                            return (
                                <motion.div key={`played-${idx}-${played.card.id}`}
                                    initial={initial}
                                    animate={animate}
                                    exit={exit}
                                    transition={{ type: "spring", stiffness: 350, damping: 25, mass: 0.8 }}
                                    className={`${animClass} ${isTrumpCard ? 'trump-glow' : ''}`}
                                    style={style}>
                                    <Card
                                        card={played.card}
                                        className="w-full h-full shadow-xl"
                                        isPlayable={false}
                                        skin={cardSkin}
                                    />
                                </motion.div>
                            );
                        })}

                        {/* Sweeping Cards */}
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
                                <div key={`swept-${idx}`}
                                    className={`absolute ${sweepClass}`}
                                    style={{
                                        ...style,
                                        zIndex: 50 + idx
                                    }}>
                                    <Card
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
    );
}
