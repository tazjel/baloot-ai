import React from 'react';
import { GameSettings } from '../types';
import { X, Volume2, VolumeX, Zap, ShieldAlert, Clock, Globe } from 'lucide-react';

interface SettingsModalProps {
    settings: GameSettings;
    onUpdate: (newSettings: GameSettings) => void;
    onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ settings, onUpdate, onClose }) => {

    const toggleSound = () => onUpdate({ ...settings, soundEnabled: !settings.soundEnabled });
    const toggleStrict = () => onUpdate({ ...settings, strictMode: !settings.strictMode });
    const toggleSpeed = () => onUpdate({ ...settings, gameSpeed: settings.gameSpeed === 'NORMAL' ? 'FAST' : 'NORMAL' });
    const cycleDuration = () => {
        // Cycle: 10 -> 15 -> 30 -> 3 -> 5 -> 10
        const next = settings.turnDuration === 10 ? 15 :
            (settings.turnDuration === 15 ? 30 :
                (settings.turnDuration === 30 ? 3 :
                    (settings.turnDuration === 3 ? 5 : 10)));
        onUpdate({ ...settings, turnDuration: next });
    };

    return (
        <div className="absolute inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-80 bg-[#1a1a1a] border border-gray-700 rounded-2xl p-6 shadow-2xl relative">

                <div className="flex items-center justify-between mb-6 border-b border-gray-800 pb-4">
                    <h2 className="text-xl font-bold text-white">Settings</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white">
                        <X size={24} />
                    </button>
                </div>

                <div className="space-y-4">
                    {/* Sound Toggle */}
                    <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" onClick={toggleSound}>
                        <div className="flex items-center gap-3">
                            {settings.soundEnabled ? <Volume2 className="text-green-500" /> : <VolumeX className="text-red-500" />}
                            <span className="text-gray-200">Sound Effects</span>
                        </div>
                        <div className={`w-10 h-5 rounded-full relative transition-colors ${settings.soundEnabled ? 'bg-green-600' : 'bg-gray-600'}`}>
                            <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-all ${settings.soundEnabled ? 'translate-x-5' : ''}`} />
                        </div>
                    </div>

                    {/* Strict Mode Toggle */}
                    <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" onClick={toggleStrict}>
                        <div className="flex items-center gap-3">
                            <ShieldAlert className={settings.strictMode ? "text-blue-500" : "text-gray-500"} />
                            <div className="flex flex-col">
                                <span className="text-gray-200">Strict Rules</span>
                                <span className="text-xs text-gray-500">{settings.strictMode ? 'Auto-Block Invalid' : 'Allow Cheating'}</span>
                            </div>
                        </div>
                        <div className={`w-10 h-5 rounded-full relative transition-colors ${settings.strictMode ? 'bg-blue-600' : 'bg-gray-600'}`}>
                            <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-all ${settings.strictMode ? 'translate-x-5' : ''}`} />
                        </div>
                    </div>

                    {/* Turn Timer */}
                    <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" onClick={cycleDuration}>
                        <div className="flex items-center gap-3">
                            <Clock className="text-amber-500" />
                            <span className="text-gray-200">Turn Timer</span>
                        </div>
                        <span className="text-amber-500 font-bold font-mono">{settings.turnDuration}s</span>
                    </div>

                    {/* Game Speed */}
                    <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" onClick={toggleSpeed}>
                        <div className="flex items-center gap-3">
                            <Zap className={settings.gameSpeed === 'FAST' ? "text-yellow-400" : "text-gray-500"} />
                            <span className="text-gray-200">Game Speed</span>
                        </div>
                        <span className="text-xs font-bold px-2 py-1 rounded bg-black/50 text-gray-400">{settings.gameSpeed}</span>
                    </div>

                    {/* Card Language Toggle */}
                    <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" onClick={() => onUpdate({ ...settings, cardLanguage: settings.cardLanguage === 'EN' ? 'AR' : 'EN' })}>
                        <div className="flex items-center gap-3">
                            <Globe className="text-cyan-400" />
                            <div className="flex flex-col">
                                <span className="text-gray-200">Card Language</span>
                                <span className="text-xs text-gray-500">English / العربية</span>
                            </div>
                        </div>
                        <span className="text-cyan-400 font-bold font-mono">{settings.cardLanguage || 'EN'}</span>
                    </div>
                </div>

                <div className="mt-8 text-center text-xs text-gray-600">
                    Version 1.2.0 • Build 2025.12
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
