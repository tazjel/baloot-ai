
import React, { useEffect, useState } from 'react';
import { X, Brain } from 'lucide-react';
import MindMapCity from '../visualizations/MindMapCity';

interface MindMapOverlayProps {
    gameId: string;
    players: any[];
    isOpen: boolean;
    onClose: () => void;
}

export default function MindMapOverlay({ gameId, players, isOpen, onClose }: MindMapOverlayProps) {
    const [mindMap, setMindMap] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!isOpen || !gameId) return;

        const fetchMindMap = async () => {
            try {
                // Use relative path or config
                const res = await fetch(`http://localhost:8000/api/mind/inference/${gameId}`);
                if (res.ok) {
                    const data = await res.json();
                    setMindMap(data.mind_map);
                }
            } catch (err) {
                console.error("Failed to fetch mind map", err);
            }
        };

        // Initial fetch
        fetchMindMap();

        // Poll every 1s
        const interval = setInterval(fetchMindMap, 1000);
        return () => clearInterval(interval);
    }, [isOpen, gameId]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm animate-in fade-in duration-200">
            {/* Header */}
            <div className="absolute top-4 left-4 right-4 flex justify-between items-center z-50 pointer-events-none">
                <div className="flex items-center gap-2 bg-black/50 p-2 rounded-lg pointer-events-auto">
                    <Brain className="w-6 h-6 text-purple-400" />
                    <div>
                        <h2 className="text-xl font-bold text-white">Neural Mind Map</h2>
                        <p className="text-xs text-gray-400">Real-time Probability Inference (Theory of Mind)</p>
                    </div>
                </div>

                <button
                    onClick={onClose}
                    className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors pointer-events-auto"
                >
                    <X className="w-6 h-6" />
                </button>
            </div>

            {/* 3D Scene */}
            <div className="w-full h-full">
                <MindMapCity mindMap={mindMap} players={players} />
            </div>

            {/* Legend */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-black/60 px-6 py-3 rounded-full flex gap-6 text-sm text-white pointer-events-none">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span>Unlikely</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                    <span>Possible</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span>Certain</span>
                </div>
            </div>
        </div>
    );
}
