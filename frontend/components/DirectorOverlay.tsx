import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GameState, Player, GameSettings } from '../types';
import { X, Gavel, Save, Brain, Zap, User, Settings2 } from 'lucide-react';

interface DirectorOverlayProps {
    gameState: GameState;
    onClose: () => void;
    onUpdate: (config: any) => void;
}

export const DirectorOverlay: React.FC<DirectorOverlayProps> = ({ gameState, onClose, onUpdate }) => {
    const [activeTab, setActiveTab] = useState<'rules' | 'bots'>('rules');

    // Local State for Changes
    const [settings, setSettings] = useState<Partial<GameSettings>>({ ...gameState.settings });

    const [botConfigs, setBotConfigs] = useState<{ [key: number]: { strategy: string, profile: string } }>(() => {
        const cfgs: any = {};
        gameState.players.forEach(p => {
            if (p.index !== 0) { // Skip Local Player (0)
                cfgs[p.index] = {
                    strategy: p.strategy || 'heuristic',
                    profile: p.profile || 'Balanced'
                };
            }
        });
        return cfgs;
    });

    const handleSave = () => {
        onUpdate({
            gameId: gameState.gameId || gameState.roomId, // Fallback
            settings,
            botConfigs
        });
        onClose();
    };

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            >
                <motion.div
                    initial={{ scale: 0.95, y: 20 }}
                    animate={{ scale: 1, y: 0 }}
                    className="bg-slate-900 border border-amber-600/30 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
                >
                    {/* Header */}
                    <div className="bg-slate-950 p-6 flex justify-between items-center border-b border-white/10">
                        <div className="flex items-center gap-3">
                            <div className="bg-amber-600/20 p-2 rounded-lg">
                                <Gavel className="w-6 h-6 text-amber-500" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-white">The Commissioner's Desk</h2>
                                <p className="text-xs text-slate-400">Game Director & Bot Control Center</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    {/* Tabs */}
                    <div className="flex border-b border-white/10 bg-slate-900/50">
                        <button
                            onClick={() => setActiveTab('rules')}
                            className={`flex-1 py-4 text-sm font-medium flex items-center justify-center gap-2 transition-all
                  ${activeTab === 'rules' ? 'bg-amber-600/10 text-amber-500 border-b-2 border-amber-500' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            <Settings2 className="w-4 h-4" /> House Rules
                        </button>
                        <button
                            onClick={() => setActiveTab('bots')}
                            className={`flex-1 py-4 text-sm font-medium flex items-center justify-center gap-2 transition-all
                  ${activeTab === 'bots' ? 'bg-indigo-600/10 text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            <Brain className="w-4 h-4" /> Bot Instructions
                        </button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {activeTab === 'rules' ? (
                            <div className="space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="bg-slate-800/50 p-4 rounded-xl border border-white/5 flex justify-between items-center">
                                        <div>
                                            <h3 className="text-white font-semibold">Strict Mode</h3>
                                            <p className="text-xs text-slate-400">Validate every move against rulebook</p>
                                        </div>
                                        <Toggle
                                            checked={!!settings.strictMode}
                                            onChange={(v) => setSettings({ ...settings, strictMode: v })}
                                        />
                                    </div>

                                    <div className="bg-slate-800/50 p-4 rounded-xl border border-white/5 flex justify-between items-center">
                                        <div>
                                            <h3 className="text-white font-semibold">Turn Timer</h3>
                                            <p className="text-xs text-slate-400">Seconds per turn</p>
                                        </div>
                                        <select
                                            className="bg-slate-950 border border-white/10 rounded px-3 py-1 text-white text-sm"
                                            value={settings.turnDuration}
                                            onChange={(e) => setSettings({ ...settings, turnDuration: Number(e.target.value) })}
                                        >
                                            <option value={5}>5s (Blitz)</option>
                                            <option value={10}>10s (Fast)</option>
                                            <option value={15}>15s (Normal)</option>
                                            <option value={30}>30s (Slow)</option>
                                            <option value={60}>60s (Comfy)</option>
                                        </select>
                                    </div>

                                    <div className="bg-slate-800/50 p-4 rounded-xl border border-white/5 flex justify-between items-center">
                                        <div>
                                            <h3 className="text-white font-semibold">Game Speed</h3>
                                            <p className="text-xs text-slate-400">Animation playback rate</p>
                                        </div>
                                        <select
                                            className="bg-slate-950 border border-white/10 rounded px-3 py-1 text-white text-sm"
                                            value={settings.gameSpeed}
                                            onChange={(e) => setSettings({ ...settings, gameSpeed: e.target.value as any })}
                                        >
                                            <option value="NORMAL">Normal</option>
                                            <option value="FAST">Fast</option>
                                        </select>
                                    </div>

                                    <div className="bg-slate-800/50 p-4 rounded-xl border border-white/5 flex justify-between items-center">
                                        <div>
                                            <h3 className="text-white font-semibold">Debug Mode</h3>
                                            <p className="text-xs text-slate-400">Show hidden states</p>
                                        </div>
                                        <Toggle
                                            checked={!!settings.isDebug}
                                            onChange={(v) => setSettings({ ...settings, isDebug: v })}
                                        />
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {gameState.players.filter(p => !p.isActive /* Usually Active=Turn, here we mean Human vs Bot. Index 0 is human */ && p.index !== 0).map(player => (
                                    <div key={player.index} className="bg-slate-800/50 p-4 rounded-xl border border-white/5 flex flex-col md:flex-row gap-4 items-center">
                                        <div className="flex items-center gap-3 w-full md:w-1/4">
                                            <img src={player.avatar} className="w-10 h-10 rounded-full border border-white/10" />
                                            <div>
                                                <div className="text-white font-medium">{player.name}</div>
                                                <div className="text-xs text-slate-400">{player.position}</div>
                                            </div>
                                        </div>

                                        <div className="flex-1 grid grid-cols-2 gap-4 w-full">
                                            <div>
                                                <label className="text-xs text-indigo-300 mb-1 block flex items-center gap-1">
                                                    <Brain className="w-3 h-3" /> Strategy Engine
                                                </label>
                                                <select
                                                    className="w-full bg-slate-950 border border-white/10 rounded px-3 py-2 text-white text-sm focus:border-indigo-500"
                                                    value={botConfigs[player.index]?.strategy || 'heuristic'}
                                                    onChange={(e) => setBotConfigs({
                                                        ...botConfigs,
                                                        [player.index]: { ...botConfigs[player.index], strategy: e.target.value }
                                                    })}
                                                >
                                                    <option value="heuristic">Heuristic (Standard)</option>
                                                    <option value="mcts">MCTS (Deep Search)</option>
                                                    <option value="neural">Neural (Fast)</option>
                                                    <option value="hybrid">Hybrid (Strongest)</option>
                                                </select>
                                            </div>

                                            <div>
                                                <label className="text-xs text-amber-300 mb-1 block flex items-center gap-1">
                                                    <User className="w-3 h-3" /> Personality
                                                </label>
                                                <select
                                                    className="w-full bg-slate-950 border border-white/10 rounded px-3 py-2 text-white text-sm focus:border-amber-500"
                                                    value={botConfigs[player.index]?.profile || 'Balanced'}
                                                    onChange={(e) => setBotConfigs({
                                                        ...botConfigs,
                                                        [player.index]: { ...botConfigs[player.index], profile: e.target.value }
                                                    })}
                                                >
                                                    <option value="Balanced">Balanced</option>
                                                    <option value="Aggressive">Aggressive</option>
                                                    <option value="Conservative">Conservative</option>
                                                </select>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t border-white/10 flex justify-end gap-3 bg-slate-950">
                        <button onClick={onClose} className="px-4 py-2 rounded-lg text-slate-400 hover:text-white transition-colors hover:bg-white/5">
                            Cancel
                        </button>
                        <button onClick={handleSave} className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white flex items-center gap-2 transition-colors font-medium">
                            <Save className="w-4 h-4" /> Apply Changes
                        </button>
                    </div>

                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};

const Toggle = ({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) => (
    <button
        onClick={() => onChange(!checked)}
        className={`w-12 h-6 rounded-full p-1 transition-colors ${checked ? 'bg-emerald-500' : 'bg-slate-700'}`}
    >
        <div className={`w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${checked ? 'translate-x-6' : 'translate-x-0'}`} />
    </button>
);
