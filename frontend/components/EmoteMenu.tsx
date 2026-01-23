import React from 'react';
import { MessageSquare, Smile, Zap } from 'lucide-react';

interface EmoteMenuProps {
    onSelectEmote: (msg: string) => void;
    onSelectThrowable: (item: string) => void;
    onClose: () => void;
}

const QUICK_CHATS = ["كفو", "العب", "ما عليك", "جبت العيد", "سري", "هلا"];
const THROWABLES = [
    { id: 'slipper', icon: '🩴', label: 'نعال' },
    { id: 'tomato', icon: '🍅', label: 'طماطم' },
    { id: 'flower', icon: '🌹', label: 'وردة' },
    { id: 'egg', icon: '🥚', label: 'بيض' },
];

const EmoteMenu: React.FC<EmoteMenuProps> = ({ onSelectEmote, onSelectThrowable, onClose }) => {
    return (
        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 bg-[#1e1e1e] border border-gray-600 rounded-xl shadow-2xl p-4 w-72 z-50 animate-in fade-in slide-in-from-bottom-4">

            {/* Header */}
            <div className="flex justify-between items-center mb-4 text-xs font-bold text-gray-400 uppercase tracking-wider">
                <span>Quick Chat</span>
                <button onClick={onClose} className="hover:text-white">✕</button>
            </div>

            {/* Quick Chat Grid */}
            <div className="grid grid-cols-3 gap-2 mb-4">
                {QUICK_CHATS.map(msg => (
                    <button
                        key={msg}
                        onClick={() => onSelectEmote(msg)}
                        className="bg-[#2a2a2a] hover:bg-yellow-600 hover:text-white text-gray-300 py-2 rounded text-sm font-bold transition-colors"
                    >
                        {msg}
                    </button>
                ))}
            </div>

            {/* Throwables Section */}
            <div className="border-t border-gray-700 pt-3">
                <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                    <Zap size={12} className="text-yellow-500" />
                    Throw Item
                </div>
                <div className="flex justify-between">
                    {THROWABLES.map(item => (
                        <button
                            key={item.id}
                            onClick={() => onSelectThrowable(item.id)}
                            className="flex flex-col items-center gap-1 group"
                        >
                            <div className="w-10 h-10 bg-[#2a2a2a] rounded-full flex items-center justify-center text-xl group-hover:scale-110 group-hover:bg-yellow-500/20 transition-all">
                                {item.icon}
                            </div>
                            <span className="text-[10px] text-gray-500">{item.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Triangle Pointer */}
            <div className="absolute left-1/2 -translate-x-1/2 bottom-[-6px] w-3 h-3 bg-[#1e1e1e] border-b border-r border-gray-600 transform rotate-45"></div>
        </div>
    );
};

export default EmoteMenu;
