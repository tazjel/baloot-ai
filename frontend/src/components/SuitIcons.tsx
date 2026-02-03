import React from 'react';

export const Spade: React.FC<{ size?: number; color?: string; className?: string }> = ({ size = 24, color = "currentColor", className = "" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C9 2 7 4.5 7 7C7 9.5 9.5 12 12 14.5C14.5 12 17 9.5 17 7C17 4.5 15 2 12 2ZM12 14.5C9 14.5 4 17 4 21H20C20 17 15 14.5 12 14.5Z" />
        <path d="M11 15V21H13V15H11Z" fill={color} />
    </svg>
);

export const Heart: React.FC<{ size?: number; color?: string; className?: string }> = ({ size = 24, color = "currentColor", className = "" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M12 21.35L10.55 20.03C5.4 15.36 2 12.27 2 8.5C2 5.41 4.42 3 7.5 3C9.24 3 10.91 3.81 12 5.08C13.09 3.81 14.76 3 16.5 3C19.58 3 22 5.41 22 8.5C22 12.27 18.6 15.36 13.45 20.03L12 21.35Z" />
    </svg>
);

export const Club: React.FC<{ size?: number; color?: string; className?: string }> = ({ size = 24, color = "currentColor", className = "" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} className={className} xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="7" r="4.5" />
        <circle cx="7" cy="15" r="4.5" />
        <circle cx="17" cy="15" r="4.5" />
        <polygon points="12,12 10,21 14,21" />
    </svg>
);

export const Diamond: React.FC<{ size?: number; color?: string; className?: string }> = ({ size = 24, color = "currentColor", className = "" }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} className={className} xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L2 12L12 22L22 12L12 2Z" />
    </svg>
);
