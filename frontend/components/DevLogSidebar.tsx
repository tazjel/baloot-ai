
import React, { useEffect, useState, useRef } from 'react';
import { devLogger, LogEntry } from '../utils/devLogger';

export const DevLogSidebar: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false); // Default closed
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Load initial history
        setLogs(devLogger.getHistory());

        // Subscribe to new logs
        const unsubscribe = devLogger.subscribe((log) => {
            setLogs(prev => [...prev, log]);
        });

        return () => unsubscribe();
    }, []);

    useEffect(() => {
        // Auto scroll
        if (isOpen && endRef.current) {
            endRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs, isOpen]);

    const toggle = () => setIsOpen(!isOpen);
    const clear = () => {
        devLogger.clear();
        setLogs([]);
    };

    if (!isOpen) {
        return (
            <div style={{
                position: 'fixed',
                right: 0,
                top: '50%',
                transform: 'translateY(-50%)',
                zIndex: 9999,
            }}>
                <button
                    onClick={toggle}
                    style={{
                        writingMode: 'vertical-rl',
                        padding: '10px 5px',
                        backgroundColor: '#333',
                        color: '#0f0',
                        border: '1px solid #0f0',
                        borderRight: 'none',
                        cursor: 'pointer',
                        fontFamily: 'monospace',
                        fontWeight: 'bold',
                        borderTopLeftRadius: '5px',
                        borderBottomLeftRadius: '5px'
                    }}
                >
                    DEV LOGS
                </button>
            </div>
        );
    }

    return (
        <div style={{
            position: 'fixed',
            right: 0,
            top: 0,
            bottom: 0,
            width: '400px',
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            color: '#fff',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            borderLeft: '2px solid #0f0',
            fontFamily: 'monospace',
            fontSize: '12px',
            boxShadow: '-5px 0 15px rgba(0,0,0,0.5)'
        }}>
            {/* Header */}
            <div style={{
                padding: '10px',
                borderBottom: '1px solid #333',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: '#111'
            }}>
                <span style={{ color: '#0f0', fontWeight: 'bold' }}>INTELLIGENT BOT PROTOCOL</span>
                <div>
                    <button onClick={clear} style={{ marginRight: '10px', background: 'transparent', border: '1px solid #666', color: '#aaa', cursor: 'pointer' }}>CLR</button>
                    <button onClick={toggle} style={{ background: 'transparent', border: '1px solid #666', color: '#aaa', cursor: 'pointer' }}>X</button>
                </div>
            </div>

            {/* Logs Area */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '10px',
                wordBreak: 'break-word',
                userSelect: 'text', // Allow copying
                cursor: 'text'
            }}>
                {logs.length === 0 && <div style={{ color: '#666', textAlign: 'center', marginTop: '20px' }}>Waiting for data stream...</div>}

                {logs.map((log) => (
                    <div key={log.id} style={{ marginBottom: '8px', borderBottom: '1px solid #222', paddingBottom: '4px' }}>
                        <div style={{ display: 'flex', marginBottom: '2px' }}>
                            <span style={{ color: '#666', marginRight: '8px' }}>[{log.timestamp}]</span>
                            <span style={{
                                fontWeight: 'bold',
                                color: log.level === 'ERROR' ? '#ff4444' :
                                    log.level === 'WARN' ? '#ffbb33' :
                                        log.level === 'SUCCESS' ? '#00C851' : '#33b5e5',
                                marginRight: '8px'
                            }}>{log.level}</span>
                            <span style={{ color: '#ccc' }}>[{log.category}]</span>
                        </div>
                        <div style={{ color: '#fff', paddingLeft: '15px' }}>
                            {log.message}
                        </div>
                        {log.data && (
                            <pre style={{
                                marginTop: '4px',
                                background: '#111',
                                padding: '5px',
                                borderRadius: '3px',
                                color: '#aaa',
                                overflowX: 'auto',
                                fontSize: '10px'
                            }}>
                                {JSON.stringify(log.data, null, 2)}
                            </pre>
                        )}
                    </div>
                ))}
                <div ref={endRef} />
            </div>
        </div>
    );
};
