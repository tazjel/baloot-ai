import React from 'react';
import { Player, PlayerPosition, Suit } from '../../types';
import { Sun, Gavel, Trophy, Spade, Heart, Club, Diamond, Megaphone } from 'lucide-react';
// Correct import paths assuming this file is in frontend/components/table/
import { SpeechBubble } from '../SpeechBubble';
import TurnTimer from './TurnTimer';
import ProjectReveal from './ProjectReveal';

// Avatar Mapping moved here as it is specific to PlayerAvatar logic
const AVATAR_MAP: Record<string, string> = {
    'avatar_saad': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Saad&backgroundColor=b6e3f4',
    'avatar_khalid': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Khalid&backgroundColor=c0aede&clothing=blazerAndShirt',
    'avatar_abu_fahad': 'https://api.dicebear.com/7.x/avataaars/svg?seed=AbuFahad&backgroundColor=ffdfbf&facialHair=beardMajestic',
    'bot_1': 'https://api.dicebear.com/7.x/bottts/svg?seed=Bot1'
};

interface PlayerAvatarProps {
    player: Player;
    isCurrentTurn: boolean;
    position: 'top' | 'left' | 'right' | 'bottom';
    timeLeft: number;
    totalTime: number;
    declarations: any;
    isProjectRevealing: boolean;
    showProjects: boolean;
    trickCount: number;
    bid?: any;
    doublingLevel?: number;
    speechText?: string | null;
    isPaused?: boolean;
    akkaState?: any;
}

const PlayerAvatar = ({
    player,
    isCurrentTurn,
    position,
    timeLeft,
    totalTime,
    declarations,
    isProjectRevealing,
    showProjects,
    trickCount,
    bid,
    doublingLevel,
    speechText,
    isPaused,
    akkaState
}: PlayerAvatarProps) => {
    const isPartner = position === 'top';
    let posClass = 'absolute z-30';
    // Adjusted: Less negative offset on mobile to prevent clipping
    if (position === 'left') posClass += ' top-1/2 -translate-y-1/2 left-1 sm:-left-[5rem] md:-left-[5.5rem]';
    else if (position === 'right') posClass += ' top-1/2 -translate-y-1/2 right-1 sm:-right-[5rem] md:-right-[5.5rem]';
    else if (position === 'top') posClass += ' top-1 sm:top-2 left-1/2 -translate-x-1/2';
    else if (position === 'bottom') posClass += ' bottom-14 left-1/2 -translate-x-1/2 z-[200]'; // Lifted slightly


    return (
        <div className={`flex flex-col items-center ${posClass} `}>

            {/* Speech Bubble integration */}
            <SpeechBubble
                text={speechText || null}
                isVisible={!!speechText}
                position={position === 'top' ? 'bottom' : position === 'bottom' ? 'top' : position === 'left' ? 'right' : 'left'}
            />

            <div className="relative">
                {/* Timer rendered for all positions now */}
                <TurnTimer isActive={isCurrentTurn} timeLeft={timeLeft} totalTime={totalTime} isPaused={isPaused} />

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
            {
                player.isDealer && (
                    <div className="absolute -bottom-2 right-1/2 translate-x-1/2 bg-[var(--color-premium-gold)] border border-white/50 rounded-md px-1.5 py-0.5 flex items-center justify-center z-40 shadow-sm">
                        <span className="text-[8px] font-black text-black leading-none">Dealer</span>
                    </div>
                )
            }
            {
                !isPartner && (
                    <div className={`
                    bg-black/80 text-white px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-[10px] sm:text-xs font-bold 
                    -mt-2 sm:-mt-3 z-20 mb-1
                    ${position === 'bottom' ? '-order-1 mb-0 -mt-0 -mb-2' : ''}
                    ${isPartner ? 'border border-amber-500/50' : 'border border-white/20'}
                    ${isCurrentTurn ? 'bg-amber-600/90' : ''}
                `}>
                        {player.name}
                    </div>
                )
            }
            {
                player.actionText && (
                    <div key={player.actionText} className="absolute -top-4 -right-10 bg-white/90 text-black px-2 py-1 rounded-lg rounded-bl-none shadow-md border border-gray-200 z-50 whitespace-nowrap animate-in fade-in zoom-in duration-200">
                        <span className="text-[10px] sm:text-xs font-bold">{player.actionText === 'PASS' ? 'بس' : player.actionText}</span>
                    </div>
                )
            }

            {/* Winning Bid Tag - Rendered BELOW the avatar */}
            {
                bid && bid.bidder === player.position && (
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
                )
            }
            {
                showProjects && declarations?.[player.position] && declarations[player.position].length > 0 && (
                    <ProjectReveal
                        projects={declarations[player.position]}
                        trickCount={trickCount}
                        position={position}
                    />
                )
            }
            {/* AKKA BADGE */}
            {
                akkaState && akkaState.claimer === player.position && (
                    <div className="absolute top-16 left-1/2 -translate-x-1/2 w-max bg-rose-600 text-white font-black text-xs sm:text-sm px-3 py-1 rounded-full shadow-lg border border-white flex items-center gap-1 z-50 animate-pulse">
                        <Megaphone size={14} className="text-white" />
                        <span>أكة!</span>
                    </div>
                )
            }
        </div>
    );
};

export default PlayerAvatar;
