import React, { useState } from 'react';
import { GameSettings } from '../types';
import { X, Volume2, VolumeX, Zap, ShieldAlert, Clock, Globe, Palette, Sliders } from 'lucide-react';
import { VISUAL_ASSETS } from '../constants';

interface SettingsModalProps {
    settings: GameSettings;
    equippedItems: { card: string, table: string };
    onUpdate: (newSettings: GameSettings) => void;
    onEquip: (itemId: string, type: 'card' | 'table') => void;
    onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ settings, equippedItems, onUpdate, onEquip, onClose }) => {
    const [activeTab, setActiveTab] = useState<'SETTINGS' | 'VISUALS'>('SETTINGS');

    const toggleSound = () => onUpdate({ ...settings, soundEnabled: !settings.soundEnabled });
    const toggleStrict = () => onUpdate({ ...settings, strictMode: !settings.strictMode });
    const toggleSpeed = () => onUpdate({ ...settings, gameSpeed: settings.gameSpeed === 'NORMAL' ? 'FAST' : 'NORMAL' });
    const cycleDuration = () => {
        const next = settings.turnDuration === 10 ? 15 :
            (settings.turnDuration === 15 ? 30 :
                (settings.turnDuration === 30 ? 3 :
                    (settings.turnDuration === 3 ? 5 : 10)));
        onUpdate({ ...settings, turnDuration: next });
    };

    return (
        <div className="absolute inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200" role="dialog" aria-modal="true" aria-label="Settings">
            <div className="w-96 bg-[#1a1a1a] border border-gray-700 rounded-2xl shadow-2xl relative flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-800">
                    <h2 className="text-xl font-bold text-white">Settings</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors" aria-label="Close settings">
                        <X size={24} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-800">
                    <button
                        onClick={() => setActiveTab('SETTINGS')}
                        className={`flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 transition-colors ${activeTab === 'SETTINGS' ? 'text-amber-500 border-b-2 border-amber-500 bg-white/5' : 'text-gray-400 hover:text-white'}`}
                    >
                        <Sliders size={16} /> Game
                    </button>
                    <button
                        onClick={() => setActiveTab('VISUALS')}
                        className={`flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 transition-colors ${activeTab === 'VISUALS' ? 'text-cyan-500 border-b-2 border-cyan-500 bg-white/5' : 'text-gray-400 hover:text-white'}`}
                    >
                        <Palette size={16} /> Visuals
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar space-y-4">

                    {activeTab === 'SETTINGS' ? (
                        <div className="space-y-4">
                            {/* Sound Toggle */}
                            <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" role="switch" aria-checked={settings.soundEnabled} aria-label="Sound effects" tabIndex={0} onClick={toggleSound} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSound(); } }}>
                                <div className="flex items-center gap-3">
                                    {settings.soundEnabled ? <Volume2 className="text-green-500" /> : <VolumeX className="text-red-500" />}
                                    <span className="text-gray-200">Sound Effects</span>
                                </div>
                                <div className={`w-10 h-5 rounded-full relative transition-colors ${settings.soundEnabled ? 'bg-green-600' : 'bg-gray-600'}`}>
                                    <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-all ${settings.soundEnabled ? 'translate-x-5' : ''}`} />
                                </div>
                            </div>

                            {/* Strict Mode Toggle */}
                            <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" role="switch" aria-checked={settings.strictMode} aria-label="Strict rules mode" tabIndex={0} onClick={toggleStrict} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleStrict(); } }}>
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
                            <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" role="button" aria-label={`Turn timer: ${settings.turnDuration} seconds`} tabIndex={0} onClick={cycleDuration} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); cycleDuration(); } }}>
                                <div className="flex items-center gap-3">
                                    <Clock className="text-amber-500" />
                                    <span className="text-gray-200">Turn Timer</span>
                                </div>
                                <span className="text-amber-500 font-bold font-mono">{settings.turnDuration}s</span>
                            </div>

                            {/* Game Speed */}
                            <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" role="button" aria-label={`Game speed: ${settings.gameSpeed}`} tabIndex={0} onClick={toggleSpeed} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSpeed(); } }}>
                                <div className="flex items-center gap-3">
                                    <Zap className={settings.gameSpeed === 'FAST' ? "text-yellow-400" : "text-gray-500"} />
                                    <span className="text-gray-200">Game Speed</span>
                                </div>
                                <span className="text-xs font-bold px-2 py-1 rounded bg-black/50 text-gray-400">{settings.gameSpeed}</span>
                            </div>

                            {/* Card Language Toggle */}
                            <div className="flex items-center justify-between p-3 bg-[#252525] rounded-xl hover:bg-[#2a2a2a] transition-colors cursor-pointer" role="button" aria-label={`Card language: ${settings.cardLanguage || 'EN'}`} tabIndex={0} onClick={() => onUpdate({ ...settings, cardLanguage: settings.cardLanguage === 'EN' ? 'AR' : 'EN' })} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onUpdate({ ...settings, cardLanguage: settings.cardLanguage === 'EN' ? 'AR' : 'EN' }); } }}>
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
                    ) : (
                        <div className="space-y-6">
                            {/* Card Selection */}
                            <div>
                                <h3 className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-3">Card Style</h3>
                                <div className="grid grid-cols-2 gap-3">
                                    {VISUAL_ASSETS.CARDS.map(asset => (
                                        <button
                                            key={asset.id}
                                            onClick={() => onEquip(asset.id, 'card')}
                                            className={`relative group overflow-hidden rounded-lg border-2 transition-all p-1 ${equippedItems.card === asset.id ? 'border-cyan-500 bg-cyan-500/10' : 'border-gray-700 hover:border-gray-500 bg-[#252525]'}`}
                                        >
                                            <div className="w-full aspect-[2.5/3.5] rounded bg-gray-900 overflow-hidden relative mb-2">
                                                {asset.type === 'image' ? (
                                                    <img src={asset.value} className="w-full h-full object-cover" alt={asset.name} />
                                                ) : (
                                                    <div className="w-full h-full" style={{ background: asset.value }}></div>
                                                )}
                                            </div>
                                            <span className={`text-xs font-bold ${equippedItems.card === asset.id ? 'text-cyan-400' : 'text-gray-400'}`}>{asset.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Table Selection */}
                            <div>
                                <h3 className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-3">Table Style</h3>
                                <div className="grid grid-cols-2 gap-3">
                                    {VISUAL_ASSETS.TABLES.map(asset => (
                                        <button
                                            key={asset.id}
                                            onClick={() => onEquip(asset.id, 'table')}
                                            className={`relative group overflow-hidden rounded-lg border-2 transition-all p-1 ${equippedItems.table === asset.id ? 'border-amber-500 bg-amber-500/10' : 'border-gray-700 hover:border-gray-500 bg-[#252525]'}`}
                                        >
                                            <div className="w-full h-16 rounded bg-gray-900 overflow-hidden relative mb-2">
                                                {asset.type === 'image' ? (
                                                    <div className="w-full h-full bg-cover bg-center" style={{ backgroundImage: `url('/assets/premium_wood_texture.png')` }}></div>
                                                ) : (
                                                    <div className="w-full h-full" style={{ background: asset.value }}></div>
                                                )}
                                            </div>
                                            <span className={`text-xs font-bold ${equippedItems.table === asset.id ? 'text-amber-400' : 'text-gray-400'}`}>{asset.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-4 border-t border-gray-800 text-center text-xs text-gray-600">
                    Version 1.2.0 • Build 2025.12
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
