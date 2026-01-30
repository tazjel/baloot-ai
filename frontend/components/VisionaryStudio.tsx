import React, { useState, useCallback } from 'react';

interface VisionaryStudioProps {
    onBack: () => void;
}

export const VisionaryStudio: React.FC<VisionaryStudioProps> = ({ onBack }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [uploadQueue, setUploadQueue] = useState<{ name: string, progress: number, status: 'pending' | 'processing' | 'done' | 'error' }[]>([]);
    const [selectedProfile, setSelectedProfile] = useState<'EXTERNAL_APP_WEB' | 'EXTERNAL_APP_ARCHIVE'>('EXTERNAL_APP_WEB');

    const [urlInput, setUrlInput] = useState("");
    const [isFetchingUrl, setIsFetchingUrl] = useState(false);

    const processFile = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);

        setUploadQueue(prev => [...prev, { name: file.name, progress: 10, status: 'processing' }]);

        try {
            const response = await fetch('/api/visionary/ingest', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (response.ok) {
                setUploadQueue(prev => prev.map(item => item.name === file.name ? { ...item, status: 'done', progress: 100 } : item));
            } else {
                console.error("Upload failed", data);
                setUploadQueue(prev => prev.map(item => item.name === file.name ? { ...item, status: 'error', progress: 100 } : item));
            }
        } catch (e) {
            console.error(e);
            setUploadQueue(prev => prev.map(item => item.name === file.name ? { ...item, status: 'error', progress: 100 } : item));
        }
    };

    const handleUrlFetch = async () => {
        if (!urlInput) return;
        setIsFetchingUrl(true);
        const name = "URL Video: " + urlInput.substring(0, 20) + "...";

        setUploadQueue(prev => [...prev, { name, progress: 20, status: 'processing' }]);

        try {
            const formData = new FormData();
            formData.append('url', urlInput);

            const response = await fetch('/api/visionary/ingest', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (response.ok) {
                setUploadQueue(prev => prev.map(item => item.name === name ? { ...item, status: 'done', progress: 100, name: data.path || item.name } : item));
                setUrlInput("");
            } else {
                setUploadQueue(prev => prev.map(item => item.name === name ? { ...item, status: 'error', progress: 100 } : item));
                alert("Ingest Failed: " + (data.message || data.error));
            }
        } catch (e) {
            console.error(e);
            setUploadQueue(prev => prev.map(item => item.name === name ? { ...item, status: 'error', progress: 100 } : item));
        } finally {
            setIsFetchingUrl(false);
        }
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const files = Array.from(e.dataTransfer.files);

        files.forEach(file => {
            processFile(file);
        });
    }, []);

    // Also handle click to upload
    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            Array.from(e.target.files).forEach(f => processFile(f));
        }
    };

    return (
        <div className="flex flex-col h-full w-full bg-slate-900 text-white font-tajawal p-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-4xl font-black text-[#CDA434] tracking-tighter flex items-center gap-3">
                        <span className="text-5xl">👁️</span> VISIONARY <span className="text-white font-light">STUDIO</span>
                    </h1>
                    <p className="text-slate-400 mt-2">Ingest. Analyze. Learn. Steal Skills from Human Gameplay.</p>
                </div>
                <button onClick={onBack} className="px-6 py-2 bg-white/5 hover:bg-white/10 rounded-lg border border-white/10 transition-all">
                    Exit Studio
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 flex-1">
                {/* Left Panel: Configuration */}
                <div className="bg-black/40 rounded-2xl p-6 border border-white/5">
                    <h3 className="text-xl font-bold text-[#CDA434] mb-6">Target Profile</h3>

                    <div className="space-y-4">
                        <div
                            onClick={() => setSelectedProfile('EXTERNAL_APP_WEB')}
                            className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedProfile === 'EXTERNAL_APP_WEB' ? 'bg-[#CDA434]/10 border-[#CDA434]' : 'bg-white/5 border-transparent hover:bg-white/10'}`}
                        >
                            <div className="font-bold mb-1">ExternalApp Web (Live)</div>
                            <div className="text-xs text-slate-400">Extracts POV Hand, Table, and Scores from standard desktop view.</div>
                        </div>

                        <div
                            onClick={() => setSelectedProfile('EXTERNAL_APP_ARCHIVE')}
                            className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedProfile === 'EXTERNAL_APP_ARCHIVE' ? 'bg-[#CDA434]/10 border-[#CDA434]' : 'bg-white/5 border-transparent hover:bg-white/10'}`}
                        >
                            <div className="font-bold mb-1">ExternalApp Archive</div>
                            <div className="text-xs text-slate-400">Extracts from historic replay viewer (Timeline, Full Table).</div>
                        </div>

                        <div className="p-4 rounded-xl border border-white/5 bg-black/20 opacity-50 cursor-not-allowed">
                            <div className="font-bold mb-1">Real Life (Beta)</div>
                            <div className="text-xs text-slate-400">Computer Vision for physical card tables (Coming Soon).</div>
                        </div>
                    </div>

                    <h3 className="text-xl font-bold text-[#CDA434] mt-8 mb-6">Output Settings</h3>
                    <div className="flex items-center gap-3 text-sm text-slate-300">
                        <input type="checkbox" checked readOnly className="rounded accent-[#CDA434]" />
                        <span>Generate Replay JSON</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-slate-300 mt-2">
                        <input type="checkbox" checked readOnly className="rounded accent-[#CDA434]" />
                        <span>Run "The Professor" Audit</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-slate-300 mt-2">
                        <input type="checkbox" className="rounded accent-[#CDA434]" />
                        <span>Auto-Train "YOLO" Model</span>
                    </div>
                </div>

                {/* Center: Drop Zone */}
                <div className="md:col-span-2 flex flex-col gap-6">
                    <label
                        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                        onDragLeave={() => setIsDragging(false)}
                        onDrop={handleDrop}
                        className={`flex-1 border-4 border-dashed rounded-3xl flex flex-col items-center justify-center transition-all cursor-pointer ${isDragging ? 'border-[#CDA434] bg-[#CDA434]/5 scale-[0.99]' : 'border-white/10 bg-black/20 hover:border-white/20'}`}
                    >
                        <input type="file" multiple className="hidden" onChange={handleFileSelect} accept="image/*,video/*" />
                        <div className="text-6xl mb-4 opacity-50">📤</div>
                        <div className="text-2xl font-bold">Drag Screenshots or Video Here</div>
                        <div className="text-slate-500 mt-2">Supports .PNG, .JPG, .MP4</div>
                    </label>

                    {/* URL Input */}
                    <div className="bg-black/40 rounded-2xl p-4 border border-white/5 flex gap-4">
                        <input
                            type="text"
                            placeholder="Paste YouTube or TikTok URL..."
                            value={urlInput}
                            onChange={(e) => setUrlInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleUrlFetch()}
                            disabled={isFetchingUrl}
                            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-[#CDA434] focus:outline-none transition-all placeholder:text-slate-600 disabled:opacity-50"
                        />
                        <button
                            onClick={handleUrlFetch}
                            disabled={isFetchingUrl || !urlInput}
                            className="px-6 py-2 bg-[#CDA434]/10 hover:bg-[#CDA434]/20 text-[#CDA434] border border-[#CDA434]/30 font-bold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {isFetchingUrl ? (
                                <span className="animate-spin">⏳</span>
                            ) : 'Fetch'}
                        </button>
                    </div>

                    {/* Queue */}
                    <div className="h-64 bg-black/40 rounded-2xl p-6 border border-white/5 overflow-y-auto">
                        <h3 className="text-lg font-bold text-slate-300 mb-4 sticky top-0 bg-black/0 backdrop-blur-md">Ingestion Queue</h3>
                        {uploadQueue.length === 0 ? (
                            <div className="text-center text-slate-600 mt-10 italic">No media pending...</div>
                        ) : (
                            <div className="space-y-3">
                                {uploadQueue.map((item, idx) => (
                                    <div key={idx} className="flex items-center gap-4 p-3 bg-white/5 rounded-lg">
                                        <div className="text-2xl">
                                            {item.name.indexOf('video') > -1 || item.name.endsWith('mp4') ? '🎬' : '🖼️'}
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex justify-between mb-1">
                                                <span className="text-sm font-bold truncate max-w-[200px]" title={item.name}>{item.name}</span>
                                                <span className={`text-xs uppercase font-bold ${item.status === 'done' ? 'text-green-400' : item.status === 'error' ? 'text-red-400' : 'text-[#CDA434]'}`}>
                                                    {item.status}
                                                </span>
                                            </div>
                                            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full transition-all duration-500 ${item.status === 'done' ? 'bg-green-500' : item.status === 'error' ? 'bg-red-500' : 'bg-[#CDA434]'}`}
                                                    style={{ width: `${item.progress}%` }}
                                                />
                                            </div>
                                        </div>
                                        {item.status === 'done' && (
                                            <button className="px-3 py-1 bg-[#CDA434] text-black text-xs font-bold rounded hover:bg-yellow-400">
                                                Review
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
