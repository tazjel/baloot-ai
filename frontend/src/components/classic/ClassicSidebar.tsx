import React from 'react';
import { GameState, GamePhase } from '../../types';
import './classic.css';

interface ClassicSidebarProps {
    gameState: GameState;
    matchScores: { us: number; them: number };
}

export default function ClassicSidebar({ gameState, matchScores }: ClassicSidebarProps) {
    const { settings, roundHistory, bid } = gameState;
    const roundNum = (roundHistory?.length || 0) + 1;

    return (
        <div className="classic-sidebar">
            {/* Session Header */}
            <div className="km-glass-strong">
                <div className="km-session-header">
                    <span style={{ fontSize: 20 }}>🎴</span>
                    <span>جلسة {1000 + Math.floor(Math.random() * 900)}</span>
                </div>
                <div className="km-session-props">
                    <div className="km-session-prop">
                        <span>⏱</span>
                        <span>{settings?.turnDuration || 10}s</span>
                    </div>
                    <div className="km-session-prop">
                        <span>🎯</span>
                        <span>152 نقطة</span>
                    </div>
                    <div className="km-session-prop">
                        <span>🔄</span>
                        <span>جولة {roundNum}</span>
                    </div>
                    <div className="km-session-prop">
                        <span>📋</span>
                        <span>{bid?.type || 'لم يبدأ'}</span>
                    </div>
                </div>
            </div>

            {/* Score Panel */}
            <div className="km-glass-strong">
                <div className="km-score-panel">
                    <div className="km-score-team">
                        <span className="km-score-label">لنا</span>
                        <span className="km-score-value">{matchScores.us}</span>
                    </div>
                    <div className="km-score-divider" />
                    <div className="km-score-team">
                        <span className="km-score-label">لهم</span>
                        <span className="km-score-value">{matchScores.them}</span>
                    </div>
                </div>
            </div>

            {/* Round History */}
            <div className="km-glass" style={{ padding: '10px 14px' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--km-text-secondary)', marginBottom: 6 }}>
                    سجل الجولات
                </div>
                {roundHistory && roundHistory.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {roundHistory.slice(-5).map((r, i) => (
                            <div key={i} style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                fontSize: 12,
                                padding: '4px 8px',
                                borderRadius: 8,
                                background: r.winner === 'us' ? 'rgba(39, 174, 96, 0.15)' : 'rgba(192, 57, 43, 0.15)',
                                color: r.winner === 'us' ? 'var(--km-accent-green)' : 'var(--km-accent-red)'
                            }}>
                                <span>ج{(r.roundNumber || i + 1)}</span>
                                <span>{r.us?.result || 0} - {r.them?.result || 0}</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div style={{ fontSize: 12, color: 'var(--km-text-muted)', textAlign: 'center', padding: 12 }}>
                        لا توجد جولات بعد
                    </div>
                )}
            </div>

            {/* Chat Panel */}
            <div className="km-glass km-chat-panel" style={{ flex: 1, minHeight: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--km-text-secondary)', padding: '10px 14px 6px' }}>
                    💬 المحادثة
                </div>
                <div className="km-chat-messages">
                    {/* Static placeholder messages */}
                    <div className="km-chat-bubble">
                        <div style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--km-gold-dim)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>🤖</div>
                        <span>مرحباً بكم في البلوت! 🎴</span>
                    </div>
                    {gameState.phase === GamePhase.Playing && (
                        <div className="km-chat-bubble">
                            <div style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--km-accent-blue)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>⚡</div>
                            <span>الجولة بدأت — بالتوفيق!</span>
                        </div>
                    )}
                </div>
                <div className="km-chat-input">
                    <input type="text" placeholder="اكتب رسالة..." readOnly />
                    <button style={{
                        background: 'var(--km-gold-dim)',
                        border: 'none',
                        borderRadius: '50%',
                        width: 32,
                        height: 32,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        fontSize: 14
                    }}>📤</button>
                </div>
            </div>
        </div>
    );
}
