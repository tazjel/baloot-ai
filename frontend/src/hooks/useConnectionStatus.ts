import { useState, useEffect } from 'react';
import socketService from '../services/SocketService';

type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting';

/**
 * useConnectionStatus - Tracks socket connection state for UI feedback.
 *
 * Returns the current status and reconnect attempt count.
 * Use this to show a banner when the connection drops.
 */
export const useConnectionStatus = () => {
    const [status, setStatus] = useState<ConnectionStatus>('connected');
    const [reconnectAttempt, setReconnectAttempt] = useState(0);

    useEffect(() => {
        const cleanup = socketService.onConnectionStatus((newStatus, attempt) => {
            setStatus(newStatus);
            if (attempt !== undefined) setReconnectAttempt(attempt);
            if (newStatus === 'connected') setReconnectAttempt(0);
        });

        return cleanup;
    }, []);

    return { status, reconnectAttempt };
};
