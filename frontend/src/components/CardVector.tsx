import React, { useMemo } from 'react';
import { CardModel, Suit, Rank } from '../types';
import { VISUAL_ASSETS } from '../constants';
import { Spade, Heart, Club, Diamond } from './SuitIcons';

interface CardVectorProps {
    card: CardModel;
    isHidden?: boolean;
    className?: string;
    selected?: boolean;
    onClick?: () => void;
    isPlayable?: boolean;
    isAkka?: boolean;
    skin?: string;
}

const CardVector: React.FC<CardVectorProps> = ({
    card,
    isHidden = false,
    className = '',
    selected = false,
    onClick,
    isPlayable = true,
    isAkka = false,
    skin = 'card_default'
}) => {
    if (!card) return null;

    const isRed = card.suit === Suit.Hearts || card.suit === Suit.Diamonds;
    const color = isRed ? '#d32f2f' : '#111';

    // --- Suit Icon Component ---
    const SuitIcon = ({ size, className, rotate }: { size: number, className?: string, rotate?: boolean }) => {
        const props = { size, color, className: `${className} ${rotate ? 'rotate-180' : ''}` };
        switch (card.suit) {
            case Suit.Spades: return <Spade {...props} />;
            case Suit.Hearts: return <Heart {...props} />;
            case Suit.Clubs: return <Club {...props} />;
            case Suit.Diamonds: return <Diamond {...props} />;
        }
    };

    // --- Pip Layout Logic ---
    const getPips = () => {
        // 100% width/height of the PILLARED area
        const pips = [];
        const r = card.rank;

        // Standard Pip Positions (percentages)
        // Cols: 30%, 70% | Row Center: 50%
        // Rows: 20, 35, 50, 65, 80

        // Column Definitions
        const left = '30%';
        const right = '70%';
        const mid = '50%';

        // Row Definitions
        const top = '20%';
        const topMid = '35%'; // for 7,8
        const center = '50%';
        const botMid = '65%'; // for 8
        const bot = '80%';

        interface StandardPipProps {
            top: string;
            left: string;
            invert?: boolean;
        }

        const StandardPip: React.FC<StandardPipProps> = ({ top, left, invert }) => (
            <div className={`absolute -translate-x-1/2 -translate-y-1/2 ${invert ? 'rotate-180' : ''}`} style={{ top, left }}>
                <SuitIcon size={20} />
            </div>
        );

        // Logic
        if (['2', '3'].includes(r as string)) {
            pips.push(<StandardPip top={top} left={mid} key="t" />);
            pips.push(<StandardPip top={bot} left={mid} key="b" invert />);
            if ((r as string) === '3') pips.push(<StandardPip top={center} left={mid} key="c" />);
        }
        else if (['4', '5', '6', '7', '8', '9', '10'].includes(r as string) || r === Rank.Ten) {
            // Corners
            pips.push(<StandardPip top={top} left={left} key="tl" />);
            pips.push(<StandardPip top={top} left={right} key="tr" />);
            pips.push(<StandardPip top={bot} left={left} key="bl" invert />);
            pips.push(<StandardPip top={bot} left={right} key="br" invert />);

            if (['6', '7', '8', '9', '10', Rank.Ten].includes(r as string)) {
                // Mids
                pips.push(<StandardPip top={center} left={left} key="ml" />);
                pips.push(<StandardPip top={center} left={right} key="mr" />);
            }

            // Center Column
            if (['5', '9'].includes(r as string)) {
                pips.push(<StandardPip top={center} left={mid} key="c" />);
            }
            if (['7', '8', '10', Rank.Ten].includes(r as string)) {
                pips.push(<StandardPip top={topMid} left={mid} key="tm" />);
            }
            if (['8', '10', Rank.Ten].includes(r as string)) {
                pips.push(<StandardPip top={botMid} left={mid} key="bm" invert />);
            }
        }

        return pips;
    };

    const isFace = ['J', 'Q', 'K'].includes(card.rank as string) || [Rank.Jack, Rank.Queen, Rank.King].includes(card.rank);
    const isAce = card.rank === Rank.Ace || (card.rank as string) === 'A';

    // Rank Text
    const rankText = card.rank === Rank.Ten ? '10' :
        card.rank === Rank.Ace ? 'A' :
            card.rank === Rank.King ? 'K' :
                card.rank === Rank.Queen ? 'Q' :
                    card.rank === Rank.Jack ? 'J' : card.rank;

    const playStyle = (!isHidden && isPlayable) ? 'cursor-pointer hover:-translate-y-2 hover:shadow-2xl' : '';

    return (
        <div
            role={onClick ? "button" : undefined}
            tabIndex={onClick ? 0 : undefined}
            aria-label={onClick && card ? `${card.rank} of ${card.suit}` : undefined}
            className={`
        relative aspect-[2.5/3.5] bg-white rounded-lg border border-gray-300 shadow-md select-none transition-transform duration-300
        font-serif overflow-hidden
        ${selected ? 'ring-4 ring-yellow-400 -translate-y-6 z-50' : ''}
        ${playStyle}
        ${className}
      `}
            onClick={onClick}
            onKeyDown={(e) => {
                if (onClick && (e.key === 'Enter' || e.key === ' ')) {
                    onClick();
                }
            }}
            style={{
                boxShadow: '2px 2px 5px rgba(0,0,0,0.1)'
            }}
        >
            {isHidden ? (
                <div
                    className="w-full h-full flex items-center justify-center border-4 border-white bg-cover bg-center"
                    style={{
                        backgroundImage: skin === 'card_default' ? `url('/assets/royal_card_back.png')` : 'none',
                        background: skin !== 'card_default' ? (VISUAL_ASSETS.CARDS.find(c => c.id === skin)?.value || '#1e3a8a') : undefined
                    }}
                ></div>
            ) : (
                <>
                    {/* Top Index */}
                    <div className="absolute top-1 left-1 flex flex-col items-center leading-none">
                        <span className="font-bold text-xl tracking-tighter" style={{ color }}>{rankText}</span>
                        <SuitIcon size={14} />
                    </div>

                    {/* Bottom Index */}
                    <div className="absolute bottom-1 right-1 flex flex-col items-center leading-none rotate-180">
                        <span className="font-bold text-xl tracking-tighter" style={{ color }}>{rankText}</span>
                        <SuitIcon size={14} />
                    </div>

                    {/* Center Content */}
                    <div className="absolute inset-[15%] flex items-center justify-center">
                        {isAce ? (
                            <SuitIcon size={64} />
                        ) : isFace ? (
                            <div className="w-full h-full flex items-center justify-center relative opacity-80">
                                {/* Improved Court Placeholder: No Box */}
                                <div className="absolute inset-0 flex items-center justify-center opacity-10">
                                    <span className="text-6xl font-black" style={{ color }}>{rankText}</span>
                                </div>
                                <SuitIcon size={40} />
                            </div>
                        ) : (
                            <div className="relative w-full h-full pointer-events-none">
                                {getPips()}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
};

export default CardVector;
