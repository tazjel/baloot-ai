import React from 'react';
import { Player, PlayerPosition, Suit } from '../../types';
import { Sun, Gavel } from 'lucide-react';
import { Spade, Heart, Club, Diamond } from '../SuitIcons';

interface ContractIndicatorProps {
    bid: any;
    players: Player[];
    doublingLevel: number;
}

const ContractIndicator = ({ bid, players, doublingLevel }: ContractIndicatorProps) => {
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

export default ContractIndicator;
