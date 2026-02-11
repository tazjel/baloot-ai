import { useState, useCallback, useRef } from 'react';

export type ToastType = 'turn' | 'akka' | 'sawa' | 'project' | 'trick' | 'error' | 'info';

export interface Toast {
    id: string;
    message: string;
    type: ToastType;
    icon: string;
    timestamp: number;
}

const TOAST_DURATION = 3000;
const MAX_TOASTS = 3;
const DEDUP_WINDOW = 1500; // Prevent duplicate toasts within this window

export function useGameToast() {
    const [toasts, setToasts] = useState<Toast[]>([]);
    const lastToastRef = useRef<{ message: string; time: number } | null>(null);

    const addToast = useCallback((message: string, type: ToastType, icon: string = '📢') => {
        const now = Date.now();

        // Deduplication: skip if same message within window
        if (lastToastRef.current &&
            lastToastRef.current.message === message &&
            now - lastToastRef.current.time < DEDUP_WINDOW) {
            return;
        }

        lastToastRef.current = { message, time: now };

        const id = `toast-${now}-${Math.random().toString(36).slice(2, 6)}`;
        const toast: Toast = { id, message, type, icon, timestamp: now };

        setToasts(prev => {
            const next = [toast, ...prev];
            return next.slice(0, MAX_TOASTS);
        });

        // Auto-remove after duration
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, TOAST_DURATION);
    }, []);

    const dismissToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    return { toasts, addToast, dismissToast };
}
