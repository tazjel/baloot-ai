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
                padding: '6px 8px',
                borderRadius: '8px',
                maxWidth: '120px',
                fontSize: '10px',
                fontWeight: 'bold',
                boxShadow: '0 2px 4px -1px rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.06)',
                zIndex: 50,
                pointerEvents: 'none',
                whiteSpace: 'normal',
                textAlign: 'center',
                border: '1px solid #e5e7eb',
                animation: 'popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
            }}
        >
            <div
                style={{
                    content: '""',
                    position: 'absolute',
                    width: '6px',
                    height: '6px',
                    backgroundColor: '#ffffff',
                    transform: 'rotate(45deg)',
                    borderBottom: '1px solid #e5e7eb',
                    borderRight: '1px solid #e5e7eb',
                    ...(position === 'top' ? { bottom: '-4px', left: '50%', marginLeft: '-3px' } : {}),
                    ...(position === 'bottom' ? { top: '-4px', left: '50%', marginLeft: '-3px', borderBottom: 'none', borderRight: 'none', borderTop: '1px solid #e5e7eb', borderLeft: '1px solid #e5e7eb' } : {}),
                    ...(position === 'left' ? { right: '-4px', top: '50%', marginTop: '-3px', transform: 'rotate(-45deg)', borderBottom: '1px solid #e5e7eb', borderRight: '1px solid #e5e7eb' } : {}),
                    ...(position === 'right' ? { left: '-4px', top: '50%', marginTop: '-3px', transform: 'rotate(135deg)', borderBottom: '1px solid #e5e7eb', borderRight: '1px solid #e5e7eb' } : {})
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
