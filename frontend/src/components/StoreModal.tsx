import React, { useState } from 'react';
import { X, Coins, Check, Lock } from 'lucide-react';
import { UserProfile } from '../types';

interface StoreModalProps {
    userProfile: UserProfile;
    onClose: () => void;
    onPurchase: (itemId: string, cost: number, type: 'card' | 'table') => void;
    onEquip: (itemId: string, type: 'card' | 'table') => void;
    ownedItems: string[];
    equippedItems: { card: string, table: string };
}

interface StoreItem {
    id: string;
    name: string;
    cost: number;
    type: 'card' | 'table';
    previewColor: string;
}

const ITEMS: StoreItem[] = [
    { id: 'card_default', name: 'Classic Blue', cost: 0, type: 'card', previewColor: 'bg-blue-900' },
    { id: 'card_gold', name: 'Royal Gold', cost: 500, type: 'card', previewColor: 'bg-yellow-500' },
    { id: 'card_sadu', name: 'Sadu Pattern', cost: 200, type: 'card', previewColor: 'bg-red-900' },

    { id: 'table_default', name: 'Classic Green', cost: 0, type: 'table', previewColor: 'bg-green-900' },
    { id: 'table_majlis', name: 'Red Majlis', cost: 1000, type: 'table', previewColor: 'bg-red-800' },
    { id: 'table_neon', name: 'Cyber Neon', cost: 1500, type: 'table', previewColor: 'bg-purple-900' },
];

const StoreModal: React.FC<StoreModalProps> = ({ userProfile, onClose, onPurchase, onEquip, ownedItems, equippedItems }) => {
    const [activeTab, setActiveTab] = useState<'card' | 'table'>('card');

    const filteredItems = ITEMS.filter(item => item.type === activeTab);

    return (
        <div className="absolute inset-0 z-[200] flex items-center justify-center bg-black/90 backdrop-blur-md" role="dialog" aria-modal="true" aria-label="Store">
            <div className="w-full max-w-4xl bg-[#1e1e1e] border border-gray-700 rounded-2xl shadow-2xl flex flex-col h-[600px] overflow-hidden">

                {/* Header */}
                <div className="p-6 border-b border-gray-700 flex justify-between items-center bg-[#252525]">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                            <Coins className="text-yellow-500" />
                            Store
                        </h2>
                        <span className="text-gray-400 text-sm">Spend your hard earned coins!</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="bg-black/50 px-4 py-2 rounded-full border border-yellow-500/30 flex items-center gap-2">
                            <Coins size={16} className="text-yellow-500" />
                            <span className="text-yellow-500 font-bold">{userProfile.coins}</span>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors" aria-label="Close store">
                            <X className="text-white" />
                        </button>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-700">
                    <button
                        onClick={() => setActiveTab('card')}
                        className={`flex-1 py-4 text-center font-bold tracking-wider transition-colors ${activeTab === 'card' ? 'bg-[#2a2a2a] text-white border-b-2 border-yellow-500' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        CARD SKINS
                    </button>
                    <button
                        onClick={() => setActiveTab('table')}
                        className={`flex-1 py-4 text-center font-bold tracking-wider transition-colors ${activeTab === 'table' ? 'bg-[#2a2a2a] text-white border-b-2 border-yellow-500' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        TABLE THEMES
                    </button>
                </div>

                {/* Grid */}
                <div className="flex-1 overflow-y-auto p-8 bg-noise">
                    <div className="grid grid-cols-3 gap-6">
                        {filteredItems.map(item => {
                            const isOwned = ownedItems.includes(item.id);
                            const isEquipped = activeTab === 'card' ? equippedItems.card === item.id : equippedItems.table === item.id;
                            const canAfford = userProfile.coins >= item.cost;

                            return (
                                <div key={item.id} className="bg-[#2a2a2a] rounded-xl border border-gray-700 overflow-hidden group hover:border-gray-500 transition-all">
                                    <div className={`h-40 ${item.previewColor} relative flex items-center justify-center`}>
                                        {/* Preview Placeholder */}
                                        <div className="w-16 h-24 bg-white/10 border-2 border-white/20 rounded shadow-lg transform group-hover:scale-110 transition-transform"></div>
                                        {isEquipped && (
                                            <div className="absolute top-2 right-2 bg-green-500 text-black text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1 shadow-lg">
                                                <Check size={12} /> EQUIPPED
                                            </div>
                                        )}
                                    </div>
                                    <div className="p-4">
                                        <h3 className="font-bold text-white mb-1">{item.name}</h3>
                                        <div className="flex justify-between items-center mt-4">
                                            {isOwned ? (
                                                <button
                                                    onClick={() => onEquip(item.id, item.type)}
                                                    disabled={isEquipped}
                                                    className={`w-full py-2 rounded-lg font-bold text-sm transition-all ${isEquipped
                                                            ? 'bg-gray-700 text-gray-400 cursor-default'
                                                            : 'bg-white text-black hover:bg-gray-200'
                                                        }`}
                                                >
                                                    {isEquipped ? 'EQUIPPED' : 'EQUIP'}
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={() => onPurchase(item.id, item.cost, item.type)}
                                                    disabled={!canAfford}
                                                    className={`w-full py-2 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all ${canAfford
                                                            ? 'bg-yellow-600 hover:bg-yellow-500 text-white'
                                                            : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                                                        }`}
                                                >
                                                    {item.cost === 0 ? 'FREE' : item.cost} <Coins size={14} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

            </div>
        </div>
    );
};

export default StoreModal;
