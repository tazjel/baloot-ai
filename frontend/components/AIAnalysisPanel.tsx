import React, { useState, useEffect } from 'react';
import { Player } from '../types';
import { analyzeMatch } from '../services/trainingService';


interface AIAnalysisPanelProps {
    players: Player[];
    gameId?: string;
}

export const AIAnalysisPanel: React.FC<AIAnalysisPanelProps> = ({ players, gameId }) => {
    const [isOpen, setIsOpen] = useState(true); // Default open
    const [thoughts, setThoughts] = useState<Record<string, any>>({});

    // Time Travel State
    const [history, setHistory] = useState<any[]>([]);
    const [historyIndex, setHistoryIndex] = useState<number>(-1); // -1 = Live

    // Import/Scan State
    const [view, setView] = useState<'analysis' | 'import'>('analysis');
    const [importData, setImportData] = useState<string | null>(null);
    const [isUploading, setIsUploading] = useState(false);

    // Deep Analysis State
    const [deepAnalysis, setDeepAnalysis] = useState<any>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    const toggle = () => setIsOpen(!isOpen);

    // Poll for Shadow Thoughts & History
    useEffect(() => {
        if (!gameId) return;

        const fetchThoughts = async () => {
            try {
                const res = await fetch(`http://127.0.0.1:3005/react-py4web/ai_thoughts/${gameId}`);
                const data = await res.json();
                if (data?.thoughts) {
                    setThoughts(data.thoughts);
                }
            } catch (e) {
                console.error("Failed to fetch thoughts", e);
            }
        };

        const fetchHistory = async () => {
            try {
                const res = await fetch(`http://127.0.0.1:3005/react-py4web/match_history/${gameId}`);
                const data = await res.json();
                if (data?.history && Array.isArray(data.history)) {
                    setHistory(data.history);
                }
            } catch (e) {
                console.error("Failed to fetch history", e);
            }
        }

        fetchHistory(); // Fetch once immediately
        const timer = setInterval(() => {
            fetchThoughts();
            // Poll history less frequently or same? Let's do same for simplicity for now
            fetchHistory();
        }, 1500);
        return () => clearInterval(timer);
    }, [gameId]);

    const getThoughtForPlayer = (idx: number) => {
        const t = thoughts[idx];
        if (!t) return null;
        // Format: { explanation: "...", move: "...", reason: "..." }
        return t.explanation || t.reason || JSON.stringify(t);
    };

    const handleFileUpload = async (file: File) => {
        setIsUploading(true);
        setImportData(null);
        try {
            const fd = new FormData();
            fd.append('screenshot', file);

            // Adjust URL if needed (in dev usually proxy handles /react-py4web/...)
            const res = await fetch('http://127.0.0.1:3005/react-py4web/analyze_screenshot', {
                method: 'POST',
                body: fd
            });

            const data = await res.json();
            if (data.error) {
                setImportData("Error: " + data.error);
            } else {
                setImportData(JSON.stringify(data.data, null, 2));
            }
        } catch (e: any) {
            setImportData("Upload Failed: " + e.toString());
        } finally {
            setIsUploading(false);
        }
    };

    const handleDeepAnalysis = async () => {
        if (!gameId) return;
        setIsAnalyzing(true);
        try {
            const res = await analyzeMatch(gameId);
            if (res.analysis) {
                setDeepAnalysis(res.analysis);
            } else if (res.error) {
                alert("Analysis Error: " + res.error);
            }
        } catch (e) {
            console.error(e);
            alert("Analysis Failed");
        } finally {
            setIsAnalyzing(false);
        }
    };

    // Render History State Helper
    const renderHistoryState = () => {
        if (historyIndex === -1 || !history[historyIndex]) return null;

        const round = history[historyIndex];
        return (
            <div style={{
                backgroundColor: '#222',
                border: '1px solid #f59e0b',
                padding: '10px',
                marginBottom: '10px',
                borderRadius: '4px'
            }}>
                <h5 style={{ color: '#f59e0b', marginTop: 0, marginBottom: '5px' }}>
                    REPLAY: Round {round.roundNumber + 1}
                </h5>
                <div style={{ fontSize: '11px', color: '#ccc', marginBottom: '10px' }}>
                    <div><strong>Winner:</strong> {round.scores?.winner}</div>
                    <div><strong>Points:</strong> Us: {round.scores?.us?.gamePoints}, Them: {round.scores?.them?.gamePoints}</div>
                    <div><strong>Bid:</strong> {round.bid?.type} by {round.bid?.bidder}</div>
                </div>

                <h6 style={{ color: '#888', marginTop: '10px', marginBottom: '5px', textTransform: 'uppercase' }}>Trick History</h6>
                <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    {round.tricks?.map((trick: any, tIdx: number) => (
                        <div key={tIdx} style={{ marginBottom: '8px', borderBottom: '1px solid #333', paddingBottom: '4px' }}>
                            <div style={{ color: '#aaa', fontSize: '10px' }}>Trick {tIdx + 1} (Winner: {trick.winner})</div>
                            <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                                {trick.cards?.map((c: any, cIdx: number) => (
                                    <span key={cIdx} style={{
                                        color: ['♥', '♦'].includes(c.suit) ? '#ef4444' : '#e5e7eb',
                                        backgroundColor: '#333',
                                        padding: '2px 4px',
                                        borderRadius: '3px',
                                        fontSize: '10px'
                                    }}>
                                        {c.rank}{c.suit} ({trick.playedBy?.[cIdx] ?? '?'})
                                    </span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (!isOpen) {
        return (
            <div style={{
                position: 'fixed',
                left: 0,
                top: '50%',
                transform: 'translateY(-50%)',
                zIndex: 9998, // Slightly below DevLogs which is 9999
            }}>
                <button
                    onClick={toggle}
                    style={{
                        writingMode: 'vertical-lr', // Left-to-right vertical for left side
                        padding: '10px 5px',
                        backgroundColor: '#222',
                        color: '#f59e0b', // Amber-500 equivalent
                        border: '1px solid #f59e0b',
                        borderLeft: 'none',
                        cursor: 'pointer',
                        fontFamily: 'monospace',
                        fontWeight: 'bold',
                        borderTopRightRadius: '5px',
                        borderBottomRightRadius: '5px'
                    }}
                >
                    AI ANALYSIS
                </button>
            </div>
        );
    }

    return (
        <div style={{
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            width: '350px',
            backgroundColor: 'rgba(0, 0, 0, 0.90)',
            color: '#fff',
            zIndex: 9998,
            display: 'flex',
            flexDirection: 'column',
            borderRight: '2px solid #f59e0b', // Amber border
            fontFamily: 'monospace',
            fontSize: '12px',
            boxShadow: '5px 0 15px rgba(0,0,0,0.5)'
        }}>
            {/* Header */}
            <div style={{
                padding: '0', // Removed padding to use tabs
                borderBottom: '1px solid #444',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: '#1a1a1a',
                height: '40px'
            }}>
                <div style={{ display: 'flex', height: '100%' }}>
                    <button
                        onClick={() => setView('analysis')}
                        style={{
                            background: view === 'analysis' ? '#f59e0b' : 'transparent',
                            color: view === 'analysis' ? '#000' : '#888',
                            border: 'none',
                            fontWeight: 'bold',
                            padding: '0 15px',
                            cursor: 'pointer',
                            fontSize: '12px',
                            height: '100%'
                        }}
                    >
                        LIVE
                    </button>
                    <button
                        onClick={() => setView('import')}
                        style={{
                            background: view === 'import' ? '#a855f7' : 'transparent',
                            color: view === 'import' ? '#fff' : '#888',
                            border: 'none',
                            fontWeight: 'bold',
                            padding: '0 15px',
                            cursor: 'pointer',
                            fontSize: '12px',
                            height: '100%',
                            borderLeft: '1px solid #333'
                        }}
                    >
                        IMPORT
                    </button>
                </div>

                <button onClick={toggle} style={{ background: 'transparent', border: 'none', color: '#666', cursor: 'pointer', padding: '0 10px', fontSize: '16px' }}>×</button>
            </div>

            {/* Analysis Area */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '15px',
                wordBreak: 'break-word'
            }}>
                {/* Time Travel Controls (Only in Analysis View) */}
                {view === 'analysis' && history.length > 0 && (
                    <div style={{ marginBottom: '20px', borderBottom: '1px solid #444', paddingBottom: '15px' }}>
                        <h4 style={{ color: '#888', marginBottom: '10px', textTransform: 'uppercase', fontSize: '10px', letterSpacing: '1px' }}>
                            Time Travel ({historyIndex === -1 ? 'LIVE' : `Round ${historyIndex + 1}`})
                        </h4>
                        <input
                            type="range"
                            min="-1"
                            max={history.length - 1}
                            value={historyIndex}
                            onChange={(e) => setHistoryIndex(parseInt(e.target.value))}
                            style={{ width: '100%', cursor: 'pointer', accentColor: '#f59e0b' }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#666' }}>
                            <span>Live</span>
                            <span>Past Rounds</span>
                        </div>
                    </div>
                )}

                {/* IMPORT VIEW */}
                {view === 'import' && (
                    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <div style={{
                            border: '2px dashed #444',
                            borderRadius: '8px',
                            padding: '20px',
                            textAlign: 'center',
                            marginBottom: '20px',
                            backgroundColor: isUploading ? 'rgba(168, 85, 247, 0.1)' : 'transparent',
                            transition: 'all 0.2s',
                            cursor: 'pointer'
                        }}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={async (e) => {
                                e.preventDefault();
                                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                                    const file = e.dataTransfer.files[0];
                                    await handleFileUpload(file);
                                }
                            }}
                        >
                            <div style={{ fontSize: '24px', marginBottom: '10px' }}>📸 / 🎥</div>
                            <p style={{ margin: '0 0 10px 0', color: '#aaa' }}>Drag Game Screenshot or Video</p>
                            <input
                                type="file"
                                accept="image/*,video/*"
                                onChange={(e) => e.target.files && handleFileUpload(e.target.files[0])}
                                style={{ fontSize: '10px', color: '#666' }}
                            />
                            {isUploading && <div style={{ color: '#a855f7', marginTop: '10px' }}>Analyzing with Gemini Vision...</div>}
                        </div>

                        {importData && (
                            <div style={{ flex: 1, overflow: 'auto', borderTop: '1px solid #333', paddingTop: '10px' }}>
                                <h4 style={{ color: '#fff', fontSize: '12px' }}>Analysis Result:</h4>
                                <pre style={{ fontSize: '10px', color: '#ccc', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                                    {importData}
                                </pre>
                            </div>
                        )}
                    </div>
                )}

                {/* Historical State View (Only in Analysis View) */}
                {view === 'analysis' && historyIndex !== -1 && renderHistoryState()}

                {/* Live Analysis (Only show if LIVE and Analysis View) */}
                {view === 'analysis' && historyIndex === -1 && (
                    <div style={{ marginBottom: '20px' }}>

                        {/* Deep Analysis Button */}
                        <div style={{ marginBottom: '15px' }}>
                            {!deepAnalysis ? (
                                <button
                                    onClick={handleDeepAnalysis}
                                    disabled={isAnalyzing}
                                    style={{
                                        width: '100%',
                                        padding: '10px',
                                        backgroundColor: '#7c3aed', // violet
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: isAnalyzing ? 'not-allowed' : 'pointer',
                                        fontWeight: 'bold',
                                        opacity: isAnalyzing ? 0.7 : 1
                                    }}
                                >
                                    {isAnalyzing ? 'Analyzing Match...' : '🧠 Perform Deep Analysis'}
                                </button>
                            ) : (
                                <div style={{
                                    backgroundColor: '#2e1065',
                                    border: '1px solid #8b5cf6',
                                    borderRadius: '4px',
                                    padding: '10px',
                                    marginBottom: '10px'
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                                        <strong style={{ color: '#a78bfa' }}>Match Analysis</strong>
                                        <button onClick={() => setDeepAnalysis(null)} style={{ background: 'none', border: 'none', color: '#ccc', cursor: 'pointer' }}>×</button>
                                    </div>
                                    <p style={{ color: '#ddd', fontSize: '11px', marginBottom: '10px' }}>{deepAnalysis.summary}</p>

                                    {deepAnalysis.moments?.map((m: any, idx: number) => (
                                        <div key={idx} style={{ marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px dashed #5b21b6' }}>
                                            <div style={{ color: '#c4b5fd', fontWeight: 'bold' }}>R{m.round} T{m.trick}: {m.action}</div>
                                            <div style={{ color: '#fff', fontSize: '11px' }}>{m.critique}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <h4 style={{ color: '#888', marginBottom: '10px', textTransform: 'uppercase', fontSize: '10px', letterSpacing: '1px' }}>Current State Reasoning</h4>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            {players?.filter(p => true).map(player => { // Show ALL players (even me for training/advice)
                                const thought = getThoughtForPlayer(player.index);
                                if (!player.isBot && !thought) return null; // Skip human if no AI thought

                                return (
                                    <div key={player.index} style={{
                                        backgroundColor: 'rgba(255,255,255,0.05)',
                                        padding: '10px',
                                        borderLeft: `3px solid ${player.isBot ? '#f59e0b' : '#3b82f6'}`,
                                        borderRadius: '0 4px 4px 0'
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                            <span style={{ color: player.isBot ? '#f59e0b' : '#3b82f6', fontWeight: 'bold', fontSize: '13px' }}>
                                                {player.name} {player.isBot ? '(BOT)' : '(YOU)'}
                                            </span>
                                            <span style={{ color: '#666', fontSize: '10px' }}>Index: {player.index}</span>
                                        </div>

                                        {/* 1. Official Reasoning (Sent by Server) */}
                                        {player.lastReasoning && (
                                            <div style={{ marginBottom: '8px' }}>
                                                <strong style={{ color: '#888', fontSize: '10px' }}>LAST ACTION:</strong>
                                                <p style={{ color: '#ddd', margin: 0, lineHeight: '1.4' }}>
                                                    "{player.lastReasoning}"
                                                </p>
                                            </div>
                                        )}

                                        {/* 2. Shadow Thought (Live from Brain) */}
                                        {thought ? (
                                            <div style={{ marginTop: '8px', borderTop: '1px dashed #444', paddingTop: '8px' }}>
                                                <strong style={{ color: '#a855f7', fontSize: '10px' }}>BRAIN THINKING:</strong>
                                                <p style={{ color: '#d8b4fe', margin: 0, lineHeight: '1.4' }}>
                                                    {thought}
                                                </p>
                                            </div>
                                        ) : (
                                            player.isActive && player.isBot && (
                                                <span style={{ color: '#555', fontStyle: 'italic' }}>Thinking...</span>
                                            )
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

