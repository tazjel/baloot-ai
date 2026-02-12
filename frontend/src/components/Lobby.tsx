import React, { useState } from 'react';
import { GameSettings, UserProfile } from '../types';
import { Clock, Shield, ShieldAlert, Play, Gamepad2, User, LogOut } from 'lucide-react';
import { devLogger } from '../utils/devLogger';

interface LobbyProps {
    onStartGame: (settings: GameSettings) => void;
    onMultiplayer: () => void;
    userProfile: UserProfile | null;
    onAuth: () => void;
    onLogout: () => void;
}

const Lobby: React.FC<LobbyProps> = ({ onStartGame, onMultiplayer, userProfile, onAuth, onLogout }) => {
    const [turnDuration, setTurnDuration] = useState<number>(3);
    const [strictMode, setStrictMode] = useState<boolean>(true);

    const handleStart = () => {
        devLogger.log('LOBBY', 'Button Clicked', { turnDuration, strictMode });
        onStartGame({ turnDuration, strictMode, soundEnabled: true, gameSpeed: 'NORMAL' });
    };

    return (
        <div
            className="flex h-full w-full items-center justify-center font-tajawal safe-area-top safe-area-bottom p-4"
            style={{ background: 'linear-gradient(180deg, #F5F3EF 0%, #E8E6E1 50%, #DCD6C8 100%)' }}
        >
            {/* Subtle texture overlay - REMOVED for Stability */}

            <div className="w-full max-w-md glass-premium p-6 sm:p-8 relative overflow-hidden">

                {/* User Profile / Auth Button */}
                <div className="absolute top-4 right-4 z-20">
                    {userProfile ? (
                        <div className="flex items-center gap-2 bg-white/80 p-2 pl-3 rounded-full shadow-sm group">
                            <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center text-white font-bold">
                                {userProfile.firstName?.[0]?.toUpperCase() || 'U'}
                            </div>
                            <div className="flex flex-col">
                                <span className="text-xs font-bold text-gray-800 leading-tight">{userProfile.firstName}</span>
                                <span className="text-[10px] text-gray-500 leading-tight">{userProfile.tier}</span>
                            </div>
                            <button
                                onClick={onLogout}
                                className="ml-1 p-1 hover:bg-red-100 rounded-full text-gray-400 hover:text-red-500 transition-colors"
                                title="Logout"
                            >
                                <LogOut size={14} />
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={onAuth}
                            className="flex items-center gap-1 bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-full text-xs font-bold transition-all shadow-md hover:shadow-lg"
                        >
                            <User size={14} />
                            <span>دخول / تسجيل</span>
                        </button>
                    )}
                </div>

                {/* Background Glow - Gold accent */}
                <div className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] bg-[radial-gradient(circle,rgba(212,175,55,0.15)_0%,transparent_60%)] pointer-events-none" />

                <div className="relative z-10 flex flex-col items-center">
                    {/* Logo/Title */}
                    <div className="mb-2 flex items-center gap-3">
                        <Gamepad2 size={36} className="text-amber-600" />
                        <h1 className="text-3xl sm:text-4xl font-bold text-gray-800">بلوت</h1>
                    </div>
                    <p className="text-gray-500 mb-6 sm:mb-8 text-sm sm:text-base">إعدادات الجلسة</p>

                    {/* Timer Settings */}
                    <div className="w-full mb-5 sm:mb-6">
                        <div className="flex items-center gap-2 mb-2 sm:mb-3 text-gray-700">
                            <Clock size={18} className="text-blue-500" />
                            <span className="font-bold text-sm sm:text-base">وقت اللعب (ثواني)</span>
                        </div>
                        <div className="grid grid-cols-4 gap-2">
                            {[3, 5, 10, 15].map((seconds) => (
                                <button
                                    key={seconds}
                                    onClick={() => setTurnDuration(seconds)}
                                    className={`py-2.5 sm:py-3 rounded-xl text-sm font-bold transition-all touch-target ${turnDuration === seconds
                                        ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                                        : 'bg-white/60 text-gray-600 hover:bg-white border border-gray-200'
                                        }`}
                                >
                                    {seconds}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Strict Mode Settings */}
                    <div className="w-full mb-6 sm:mb-8">
                        <div className="flex items-center justify-between mb-2 sm:mb-3 text-gray-700">
                            <div className="flex items-center gap-2">
                                {strictMode ? <Shield size={18} className="text-green-500" /> : <ShieldAlert size={18} className="text-orange-500" />}
                                <span className="font-bold text-sm sm:text-base">نظام اللعب</span>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${strictMode ? 'bg-green-100 text-green-600' : 'bg-orange-100 text-orange-600'}`}>
                                {strictMode ? 'صارم (آلي)' : 'تحدي (يدوي)'}
                            </span>
                        </div>

                        <div className="flex bg-white/60 p-1 rounded-xl border border-gray-200">
                            <button
                                onClick={() => setStrictMode(true)}
                                className={`flex-1 py-2.5 rounded-lg text-xs sm:text-sm font-bold transition-all touch-target ${strictMode ? 'bg-white text-gray-800 shadow-md' : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                منع الغش تلقائياً
                            </button>
                            <button
                                onClick={() => setStrictMode(false)}
                                className={`flex-1 py-2.5 rounded-lg text-xs sm:text-sm font-bold transition-all touch-target ${!strictMode ? 'bg-white text-gray-800 shadow-md' : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                نظام التحدي
                            </button>
                        </div>
                        <p className="text-xs text-gray-500 mt-2 text-right">
                            {strictMode
                                ? "يمنع النظام لعب أي ورقة مخالفة للقوانين بشكل آلي."
                                : "يمكن للاعبين لعب أي ورقة. يجب على الخصم الاعتراض لكشف الغش."}
                        </p>
                    </div>

                    {/* Start Button - Premium Gold */}
                    <button
                        onClick={handleStart}
                        className="w-full btn-premium flex items-center justify-center gap-2 mb-3"
                    >
                        <Play size={20} fill="currentColor" />
                        <span>ابدأ اللعب (ضد الكمبيوتر)</span>
                    </button>

                    {/* Multiplayer Button */}
                    <button
                        onClick={onMultiplayer}
                        className="w-full py-3 bg-white/60 border border-gray-300 hover:bg-white text-gray-700 font-bold rounded-full transition-all flex items-center justify-center gap-2 touch-target"
                    >
                        <span>🌐 اللعب اونلاين (تجريبي)</span>
                    </button>



                </div>
            </div>
        </div>
    );
};

export default Lobby;

