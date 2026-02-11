import React from 'react';
import { DeclaredProject, CardModel, Suit, Rank } from '../../types';
import { Spade, Heart, Club, Diamond } from '../SuitIcons';
import { Trophy } from 'lucide-react';

/**
 * ProjectReveal — Displays declared project cards near a player's avatar.
 *
 * 3-Phase display mechanic:
 * - Trick 1 (trickCount=0): Text label (سرا/50/100/400) — handled by parent
 * - Trick 2 (trickCount=1): Face-up mini cards fanned out
 * - Trick 3+ (trickCount>=2): Hidden (cards disappear)
 */

interface ProjectRevealProps {
    projects: DeclaredProject[];
    trickCount: number;
    position: 'top' | 'left' | 'right' | 'bottom';
}

// --- Mini Card Component (simplified inline rendering) ---
const MiniCard: React.FC<{ card: CardModel; rotation: number; offsetX: number }> = ({ card, rotation, offsetX }) => {
    if (!card) return null;

    const isRed = card.suit === Suit.Hearts || card.suit === Suit.Diamonds;
    const color = isRed ? '#d32f2f' : '#111';

    const rankText = card.rank === Rank.Ten ? '10' :
        card.rank === Rank.Ace ? 'A' :
            card.rank === Rank.King ? 'K' :
                card.rank === Rank.Queen ? 'Q' :
                    card.rank === Rank.Jack ? 'J' : card.rank;

    const SuitIcon = ({ size }: { size: number }) => {
        const props = { size, color };
        switch (card.suit) {
            case Suit.Spades: return <Spade {...props} />;
            case Suit.Hearts: return <Heart {...props} />;
            case Suit.Clubs: return <Club {...props} />;
            case Suit.Diamonds: return <Diamond {...props} />;
            default: return null;
        }
    };

    return (
        <div
            className="absolute bg-white rounded-md border border-gray-300 shadow-lg select-none"
            style={{
                width: '2.2rem',
                height: '3.1rem',
                transform: `translateX(${offsetX}px) rotate(${rotation}deg)`,
                transformOrigin: 'bottom center',
                zIndex: 10 + Math.abs(offsetX),
            }}
        >
            {/* Top-left index */}
            <div className="absolute top-0.5 left-0.5 flex flex-col items-center leading-none">
                <span className="font-bold text-[9px] tracking-tighter" style={{ color }}>{rankText}</span>
                <SuitIcon size={8} />
            </div>
            {/* Center suit icon */}
            <div className="absolute inset-0 flex items-center justify-center">
                <SuitIcon size={16} />
            </div>
        </div>
    );
};

// --- Project Label (Trick 1 display) ---
const ProjectLabel: React.FC<{ project: DeclaredProject }> = ({ project }) => {
    let label = '';
    switch (project.type) {
        case 'SIRA': label = 'سرا'; break;
        case 'FIFTY': label = '50'; break;
        case 'HUNDRED': label = '100'; break;
        case 'FOUR_HUNDRED': label = '400'; break;
        case 'BALOOT': label = 'بلوت'; break;
    }
    return (
        <div className="bg-gradient-to-r from-amber-300 to-yellow-500 text-black font-black text-xs sm:text-sm px-3 py-1 rounded-full shadow-lg border border-white flex items-center gap-1 animate-bounce-in">
            <Trophy size={14} className="text-amber-800" />
            <span>{label}</span>
        </div>
    );
};

// --- Cards Fan (Trick 2 display) ---
const CardsFan: React.FC<{ projects: DeclaredProject[]; position: string }> = ({ projects, position }) => {
    // Collect all cards from all projects
    const allCards: CardModel[] = [];
    projects.forEach(p => {
        if (p.cards) {
            allCards.push(...p.cards);
        }
    });

    if (allCards.length === 0) {
        // Fallback to labels if no card data
        return (
            <div className="flex flex-col gap-1">
                {projects.map((p, i) => <ProjectLabel key={i} project={p} />)}
            </div>
        );
    }

    // Fan layout: spread cards with slight rotation
    const totalCards = allCards.length;
    const spreadAngle = Math.min(8, 30 / totalCards); // degrees between cards
    const spreadX = Math.min(18, 50 / totalCards); // px between cards

    // Position offset based on player position
    const positionStyle: React.CSSProperties = {};
    if (position === 'top') {
        positionStyle.top = '3.5rem';
        positionStyle.left = '50%';
        positionStyle.transform = 'translateX(-50%)';
    } else if (position === 'bottom') {
        positionStyle.bottom = '4.5rem';
        positionStyle.left = '50%';
        positionStyle.transform = 'translateX(-50%)';
    } else if (position === 'left') {
        positionStyle.top = '50%';
        positionStyle.left = '3.5rem';
        positionStyle.transform = 'translateY(-50%)';
    } else if (position === 'right') {
        positionStyle.top = '50%';
        positionStyle.right = '3.5rem';
        positionStyle.transform = 'translateY(-50%)';
    }

    return (
        <div
            className="absolute z-50 flex items-center justify-center animate-in fade-in zoom-in duration-500"
            style={{
                ...positionStyle,
                width: `${totalCards * spreadX + 40}px`,
                height: '3.5rem',
            }}
        >
            {allCards.map((card, i) => {
                const centerIdx = (totalCards - 1) / 2;
                const offset = i - centerIdx;
                return (
                    <MiniCard
                        key={`${card.rank}${card.suit}-${i}`}
                        card={card}
                        rotation={offset * spreadAngle}
                        offsetX={offset * spreadX}
                    />
                );
            })}
        </div>
    );
};

// --- Main Component ---
const ProjectReveal: React.FC<ProjectRevealProps> = ({ projects, trickCount, position }) => {
    if (!projects || projects.length === 0) return null;

    // DEBUG: trace what we receive
    console.log('[ProjectReveal]', { position, trickCount, projects: projects.map(p => ({ type: p.type, cardsLen: p.cards?.length })) });

    // Phase 1: Trick 1 (trickCount=0) — Show text labels
    if (trickCount === 0) {
        return (
            <div className="absolute top-10 left-1/2 -translate-x-1/2 w-max flex flex-col items-center gap-1 z-50">
                {projects.map((proj, idx) => (
                    <ProjectLabel key={idx} project={proj} />
                ))}
            </div>
        );
    }

    // Phase 2: Trick 2 (trickCount=1) — Show face-up cards
    if (trickCount === 1) {
        return <CardsFan projects={projects} position={position} />;
    }

    // Phase 3: Trick 3+ (trickCount>=2) — Hidden
    return null;
};

export default ProjectReveal;
