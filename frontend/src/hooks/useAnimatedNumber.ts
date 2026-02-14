import { useState, useEffect, useRef } from 'react';

/**
 * Animates a number from its previous value to the target using requestAnimationFrame.
 * Uses ease-out cubic for smooth deceleration.
 */
export function useAnimatedNumber(target: number, duration = 400): number {
    const [display, setDisplay] = useState(target);
    const prevRef = useRef(target);
    const rafRef = useRef<number | null>(null);

    useEffect(() => {
        const from = prevRef.current;
        const to = target;
        prevRef.current = target;

        if (from === to) return;

        const start = performance.now();
        const diff = to - from;

        const tick = (now: number) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            // Ease-out cubic: 1 - (1 - t)^3
            const eased = 1 - Math.pow(1 - progress, 3);
            setDisplay(Math.round(from + diff * eased));

            if (progress < 1) {
                rafRef.current = requestAnimationFrame(tick);
            }
        };

        rafRef.current = requestAnimationFrame(tick);

        return () => {
            if (rafRef.current !== null) {
                cancelAnimationFrame(rafRef.current);
            }
        };
    }, [target, duration]);

    return display;
}
