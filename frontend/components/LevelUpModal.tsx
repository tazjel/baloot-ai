import React, { useEffect } from 'react';
import { Crown, Star, Coins } from 'lucide-react';
import { soundManager } from '../services/SoundManager';

interface LevelUpModalProps {
    newLevel: number;
    rewards: { coins: number };
    onClose: () => void;
}

const LevelUpModal: React.FC<LevelUpModalProps> = ({ newLevel, rewards, onClose }) => {

    useEffect(() => {
        soundManager.playWinSound(); // Re-use win sound or add level up sound
    }, []);

    return (
        <div className="absolute inset-0 z-[400] flex items-center justify-center bg-black/90 backdrop-blur-md animate-in fade-in duration-500">
            <div className="relative bg-gradient-to-b from-[#1a1a1a] to-black border-2 border-yellow-500 rounded-3xl p-10 flex flex-col items-center shadow-[0_0_100px_rgba(234,179,8,0.3)] max-w-sm w-full text-center">

                {/* Radiation Effect */}
                <div className="absolute inset-0 overflow-hidden rounded-3xl pointer-events-none">
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-yellow-500/10 rounded-full blur-3xl animate-pulse"></div>
                </div>

                <div className="relative mb-6">
                    <div className="w-24 h-24 bg-yellow-500 rounded-full flex items-center justify-center shadow-lg animate-bounce">
                        <Crown size={48} className="text-black" />
                    </div>
                    <div className="absolute -bottom-2 -right-2 bg-black border border-yellow-500 text-yellow-500 font-bold px-3 py-1 rounded-full text-xs">
                        LEVEL UP!
                    </div>
                </div>

                <h2 className="text-4xl font-black text-white mb-2 tracking-tighter">LEVEL {newLevel}</h2>
                <p className="text-gray-400 mb-8">You are becoming a legend of Baloot!</p>

                <div className="w-full bg-[#2a2a2a] rounded-xl p-4 mb-8 border border-gray-700 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Coins className="text-yellow-400" />
                        <span className="text-gray-300 font-bold">Reward</span>
                    </div>
                    <span className="text-2xl font-bold text-yellow-400">+{rewards.coins} Coins</span>
                </div>

                <button
                    onClick={onClose}
                    className="w-full py-4 bg-yellow-500 hover:bg-yellow-400 text-black font-black text-xl rounded-xl shadow-xl transition-all hover:scale-105"
                >
                    CLAIM & CONTINUE
                </button>
            </div>
        </div>
    );
};

export default LevelUpModal;
