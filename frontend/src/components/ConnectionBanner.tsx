import React from 'react';
import { useConnectionStatus } from '../hooks/useConnectionStatus';

/**
 * ConnectionBanner - Shows a non-intrusive banner when connection is lost.
 * Appears at the top of the screen during disconnect/reconnection.
 */
const ConnectionBanner: React.FC = () => {
    const { status, reconnectAttempt } = useConnectionStatus();

    if (status === 'connected') return null;

    return (
        <div
            className="fixed top-0 left-0 right-0 z-[10000] flex items-center justify-center py-2 px-4 text-sm font-medium transition-all duration-300"
            style={{
                background: status === 'disconnected'
                    ? 'linear-gradient(90deg, #991b1b, #7f1d1d)'
                    : 'linear-gradient(90deg, #92400e, #78350f)',
                color: '#fef3c7',
            }}
        >
            {status === 'reconnecting' ? (
                <span>⏳ جاري إعادة الاتصال... (محاولة {reconnectAttempt})</span>
            ) : (
                <span>🔌 انقطع الاتصال بالسيرفر</span>
            )}
        </div>
    );
};

export default ConnectionBanner;
