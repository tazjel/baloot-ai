import React, { useEffect, useState } from 'react';

interface SpeechBubbleProps {
    text: string | null;
    isVisible: boolean;
    onComplete?: () => void;
    position: 'top' | 'bottom' | 'left' | 'right';
}

export const SpeechBubble: React.FC<SpeechBubbleProps> = ({ text, isVisible, onComplete, position }) => {
    const [show, setShow] = useState(isVisible);

    useEffect(() => {
        setShow(isVisible);
        if (isVisible) {
            const timer = setTimeout(() => {
                setShow(false);
                if (onComplete) onComplete();
            }, 5000); // 5 seconds display
            return () => clearTimeout(timer);
        }
    }, [isVisible, text, onComplete]);

    if (!show || !text) return null;

    // Positioning styles
    const positionStyles: Record<string, React.CSSProperties> = {
        top: { bottom: '110%', left: '50%', transform: 'translateX(-50%)' },
        bottom: { top: '110%', left: '50%', transform: 'translateX(-50%)' },
        left: { right: '110%', top: '50%', transform: 'translateY(-50%)' },
        right: { left: '110%', top: '50%', transform: 'translateY(-50%)' }
    };

    return (
        <div
            style={{
                position: 'absolute',
                ...positionStyles[position],
                backgroundColor: '#ffffff',
                color: '#1f2937',
                padding: '12px 16px',
                borderRadius: '16px',
                maxWidth: '220px',
                fontSize: '14px',
                fontWeight: 'bold',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                zIndex: 50,
                pointerEvents: 'none',
                whiteSpace: 'normal',
                textAlign: 'center',
                border: '2px solid #e5e7eb',
                animation: 'popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
            }}
        >
            <div
                style={{
                    content: '""',
                    position: 'absolute',
                    width: '10px',
                    height: '10px',
                    backgroundColor: '#ffffff',
                    transform: 'rotate(45deg)',
                    borderBottom: '2px solid #e5e7eb',
                    borderRight: '2px solid #e5e7eb',
                    ...(position === 'top' ? { bottom: '-7px', left: '50%', marginLeft: '-5px' } : {}),
                    ...(position === 'bottom' ? { top: '-7px', left: '50%', marginLeft: '-5px', borderBottom: 'none', borderRight: 'none', borderTop: '2px solid #e5e7eb', borderLeft: '2px solid #e5e7eb' } : {}),
                    ...(position === 'left' ? { right: '-7px', top: '50%', marginTop: '-5px', transform: 'rotate(-45deg)', borderBottom: '2px solid #e5e7eb', borderRight: '2px solid #e5e7eb' } : {}),
                    ...(position === 'right' ? { left: '-7px', top: '50%', marginTop: '-5px', transform: 'rotate(135deg)', borderBottom: '2px solid #e5e7eb', borderRight: '2px solid #e5e7eb' } : {})
                }}
            />
            "{text}"
            <style>{`
        @keyframes popIn {
          from { opacity: 0; transform: scale(0.5) ${position === 'top' || position === 'bottom' ? 'translateX(-50%)' : 'translateY(-50%)'}; }
          to { opacity: 1; transform: scale(1) ${position === 'top' || position === 'bottom' ? 'translateX(-50%)' : 'translateY(-50%)'}; }
        }
      `}</style>
        </div>
    );
};
