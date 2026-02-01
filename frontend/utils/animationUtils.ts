import { Player } from '../types';

interface AnimationParams {
    playerIndex: number;
    isLatest: boolean;
    myIndex: number;
    players: Player[];
    tableCards: any[]; // Using any because table structure might be complex
}

/**
 * Calculates the animation trajectory for a played card.
 * Moves card from player's position (Bottom/Right/Top/Left) to the table center.
 */
export const getPlayedCardAnimation = ({
    playerIndex,
    isLatest,
    myIndex,
    players,
    tableCards
}: AnimationParams) => {
    const relativeIndex = (playerIndex - myIndex + 4) % 4; // 0=Me, 1=Right, 2=Partner, 3=Left

    const cardWidth = window.innerWidth < 640 ? 60 : 85;
    const cardHeight = window.innerWidth < 640 ? 84 : 118;
    const offsetDistance = window.innerWidth < 640 ? 25 : 40; // Tighter

    // 1. Determine Final Position (Target)
    let targetX = 0;
    let targetY = 0;
    let rotation = 0;
    let initialX = 0;
    let initialY = 0;

    const range = 500; // Throw distance

    switch (relativeIndex) {
        case 0: // Me (Bottom)
            targetX = 0;
            targetY = offsetDistance;
            initialX = 0;
            initialY = range; // Come from bottom
            rotation = -2 + ((playerIndex * 7) % 5);
            break;
        case 1: // Right
            targetX = offsetDistance * 1.5;
            targetY = 0;
            initialX = range; // Come from right
            initialY = 0;
            rotation = 85 + ((playerIndex * 7) % 5);
            break;
        case 2: // Partner (Top)
            targetX = 0;
            targetY = -offsetDistance;
            initialX = 0;
            initialY = -range; // Come from top
            rotation = 180 + ((playerIndex * 7) % 5);
            break;
        case 3: // Left
            targetX = -offsetDistance * 1.5;
            targetY = 0;
            initialX = -range; // Come from left
            initialY = 0;
            rotation = -85 + ((playerIndex * 7) % 5);
            break;
    }

    // Z-Index Logic
    // We try to find the player's card in the tableCards to see play order
    const playOrder = tableCards.findIndex(c => (c as any).playedBy === players[playerIndex].position);
    const zIndex = 40 + (playOrder >= 0 ? playOrder : 0);

    // Telemetry for Verification
    if (isLatest) {
        // We use a dynamic import for logger if needed, or just console in dev
        // Keeping it side-effect free for now, moving logging out or keeping purely calculation
        // If logging is strictly required here, we'd need to inject the logger or handle it in the component.
        // For "Clean Code", we prefer pure functions. We'll leave the logging in the component or remove it if excessive.
    }

    return {
        initial: { opacity: 0, x: initialX, y: initialY, scale: 0.8, rotate: rotation },
        animate: { opacity: 1, x: targetX, y: targetY, scale: 1, rotate: rotation },
        exit: { opacity: 0, scale: 0.5 },
        style: {
            position: 'absolute' as 'absolute',
            top: '50%',
            left: '50%',
            width: `${cardWidth}px`,
            height: `${cardHeight}px`,
            marginTop: `-${cardHeight / 2}px`, // Center anchor
            marginLeft: `-${cardWidth / 2}px`, // Center anchor
            zIndex: zIndex,
            boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
        },
        animClass: isLatest ? 'animate-thump' : '' // Custom tailwind class for thump impact
    };
};
