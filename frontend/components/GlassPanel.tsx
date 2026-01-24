import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

interface GlassPanelProps extends HTMLMotionProps<"div"> {
    children: React.ReactNode;
    className?: string;
    intensity?: 'low' | 'medium' | 'high';
    border?: boolean;
    glow?: boolean;
}

const GlassPanel: React.FC<GlassPanelProps> = ({
    children,
    className = '',
    intensity = 'medium',
    border = true,
    glow = false,
    ...props
}) => {
    // Opacity & Blur mapping
    const bgMap = {
        low: 'bg-white/10 backdrop-blur-sm',
        medium: 'bg-white/20 backdrop-blur-md',
        high: 'bg-white/30 backdrop-blur-lg'
    };

    const borderClass = border ? 'border border-white/20' : '';
    const glowClass = glow ? 'shadow-[0_0_20px_rgba(212,175,55,0.3)]' : 'shadow-lg';

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className={`
                rounded-2xl 
                ${bgMap[intensity]} 
                ${borderClass} 
                ${glowClass} 
                ${className}
            `}
            {...props}
        >
            {children}
        </motion.div>
    );
};

export default GlassPanel;
