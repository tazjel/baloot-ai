
import React, { useState, useEffect, useCallback } from 'react';

interface VisionaryVerifierProps {
    onBack: () => void;
}

export const VisionaryVerifier: React.FC<VisionaryVerifierProps> = ({ onBack }) => {
    const [currentImage, setCurrentImage] = useState<{ filename: string, url: string } | null>(null);
    const [loading, setLoading] = useState(false);
    const [correctionMode, setCorrectionMode] = useState(false);
    const [customLabel, setCustomLabel] = useState("");
    
    // Stats
    const [stats, setStats] = useState({ verified: 0, trash: 0 });

    const fetchNext = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/visionary/verify/next');
            const data = await res.json();
            
            if (data.done) {
                alert("All images verified! Great job.");
                setCurrentImage(null);
            } else if (data.filename) {
                setCurrentImage(data);
                setCustomLabel(""); 
                setCorrectionMode(false);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchNext();
    }, [fetchNext]);

    const submitVerdict = async (verdict: 'valid' | 'invalid' | 'correction', label?: string) => {
        if (!currentImage) return;
        
        // Optimistic UI update could happen here, but we'll wait for sync for safety
        try {
            await fetch('/api/visionary/verify/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: currentImage.filename,
                    verdict,
                    label
                })
            });
            
            // Update stats
            if (verdict === 'invalid') setStats(s => ({ ...s, trash: s.trash + 1 }));
            else setStats(s => ({ ...s, verified: s.verified + 1 }));
            
            fetchNext();
        } catch (e) {
            alert("Error submitting: " + e);
        }
    };

    // Keyboard Shortcuts
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if (correctionMode) return; // Disable shortcuts while typing
            
            if (e.key === 'ArrowRight' || e.key === 'y') submitVerdict('valid');
            if (e.key === 'ArrowLeft' || e.key === 'n') submitVerdict('invalid');
            if (e.key === 'ArrowUp' || e.key === 'Enter') setCorrectionMode(true);
        };
        
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [currentImage, correctionMode]);

    if (!currentImage && !loading) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
                <div className="text-6xl mb-4">🎉</div>
                <div className="text-2xl">No more images to verify!</div>
                <button onClick={onBack} className="mt-8 px-6 py-2 bg-white/10 rounded hover:bg-white/20">
                    Back to Studio
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full w-full bg-slate-900 text-white font-tajawal p-8 relative">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                    <button onClick={onBack} className="text-2xl hover:scale-110 transition-transform">⬅️</button>
                    <h1 className="text-2xl font-bold text-[#CDA434]">Verification Station</h1>
                </div>
                <div className="flex gap-4 text-sm font-mono bg-black/30 p-2 rounded-lg">
                    <div className="text-green-400">Valid: {stats.verified}</div>
                    <div className="text-red-400">Trash: {stats.trash}</div>
                </div>
            </div>

            {/* Main Card Area */}
            <div className="flex-1 flex flex-col items-center justify-center relative">
                {currentImage ? (
                    <div className="relative group">
                        <img 
                            src={currentImage.url} 
                            className="max-h-[60vh] rounded-xl shadow-2xl border-4 border-white/10" 
                            alt="To Verify"
                        />
                        <div className="absolute top-2 left-2 bg-black/60 px-2 py-1 rounded text-xs font-mono opacity-50 group-hover:opacity-100 transition-opacity">
                            {currentImage.filename}
                        </div>
                    </div>
                ) : (
                    <div className="animate-pulse w-96 h-96 bg-white/5 rounded-xl"></div>
                )}
            </div>

            {/* Controls */}
            <div className="h-32 mt-8 flex flex-col items-center justify-center gap-4">
                {correctionMode ? (
                    <div className="flex gap-2 w-full max-w-md animate-in slide-in-from-bottom-4">
                        <input 
                            autoFocus
                            type="text" 
                            placeholder="Enter Card (e.g. 7S, KD)..."
                            className="flex-1 bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-xl focus:border-[#CDA434] outline-none"
                            value={customLabel}
                            onChange={e => setCustomLabel(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && customLabel) submitVerdict('correction', customLabel);
                                if (e.key === 'Escape') setCorrectionMode(false);
                            }}
                        />
                        <button 
                            onClick={() => submitVerdict('correction', customLabel)}
                            className="bg-[#CDA434] text-black font-bold px-6 rounded-lg hover:bg-yellow-400"
                        >
                            Save
                        </button>
                    </div>
                ) : (
                    <div className="flex gap-8 items-center">
                        <button 
                            onClick={() => submitVerdict('invalid')}
                            className="flex flex-col items-center gap-2 group"
                        >
                            <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/50 flex items-center justify-center text-3xl group-hover:bg-red-500 group-hover:text-black transition-all">
                                🗑️
                            </div>
                            <span className="text-xs text-slate-400 font-mono">TRASH (Left)</span>
                        </button>

                        <button 
                            onClick={() => setCorrectionMode(true)}
                            className="flex flex-col items-center gap-2 group"
                        >
                            <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/50 flex items-center justify-center text-xl group-hover:bg-blue-500 group-hover:text-black transition-all">
                                ✏️
                            </div>
                            <span className="text-xs text-slate-400 font-mono">LABEL (Up)</span>
                        </button>

                        <button 
                            onClick={() => submitVerdict('valid')}
                            className="flex flex-col items-center gap-2 group"
                        >
                            <div className="w-16 h-16 rounded-full bg-green-500/10 border border-green-500/50 flex items-center justify-center text-3xl group-hover:bg-green-500 group-hover:text-black transition-all">
                                ✅
                            </div>
                            <span className="text-xs text-slate-400 font-mono">VALID (Right)</span>
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};
