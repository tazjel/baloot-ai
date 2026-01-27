
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TensionLevel } from '../../hooks/useGameTension';

interface HeartbeatLayerProps {
    tension: TensionLevel;
    bpm: number;
}

export const HeartbeatLayer: React.FC<HeartbeatLayerProps> = ({ tension, bpm }) => {
    if (tension === 'low' || bpm === 0) return null;

    // Pulse duration in seconds (60 / bpm)
    const duration = 60 / bpm;

    // Determine intensity (opacity/color) based on tension
    let opacity = 0;
    let color = 'rgba(255, 0, 0, 0)'; // Transparent

    switch (tension) {
        case 'medium':
            opacity = 0.1;
            color = 'radial-gradient(circle, transparent 60%, rgba(200, 50, 50, 0.2) 100%)';
            break;
        case 'high':
            opacity = 0.2;
            color = 'radial-gradient(circle, transparent 50%, rgba(220, 0, 0, 0.4) 100%)';
            break;
        case 'critical':
            opacity = 0.3;
            color = 'radial-gradient(circle, transparent 40%, rgba(255, 0, 0, 0.6) 100%)';
            break;
    }

    return (
        <AnimatePresence>
            <motion.div
                className="pointer-events-none fixed inset-0 z-0"
                initial={{ opacity: 0 }}
                animate={{
                    opacity: [0, opacity, 0], // Pulse
                }}
                transition={{
                    duration: duration,
                    repeat: Infinity,
                    ease: "easeInOut"
                }}
                style={{
                    background: color,
                    mixBlendMode: 'multiply'
                }}
            />
        </AnimatePresence>
    );
};
