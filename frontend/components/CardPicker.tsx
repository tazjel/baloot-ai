import React from 'react';


const SUIT_ICONS: Record<string, string> = { 'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣' };
const RANK_ORDER = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A'];

interface CardPickerProps {
  onSelect: (rank: string, suit: string) => void;
  takenCards?: string[]; // Cards taken by OTHER players (Disabled)
  myCards?: string[];    // Cards in MY hand (Highlighted)
  multiSelect?: boolean;
}

const CardPicker: React.FC<CardPickerProps> = ({ onSelect, takenCards = [], myCards = [] }) => {

  const isTaken = (rank: string, suit: string) => takenCards.includes(`${rank}${suit}`);
  const isMine = (rank: string, suit: string) => myCards.includes(`${rank}${suit}`);

  return (
    <div className="bg-slate-800 p-4 rounded-xl border border-slate-600 shadow-2xl max-w-md">
      <h3 className="text-white font-bold mb-4 text-center">Select Card</h3>
      <div className="grid grid-cols-4 gap-2">
        {['S', 'H', 'D', 'C'].map(suit => (
          <div key={suit} className="flex flex-col gap-2">
            {/* Header Icon */}
            <div className={`text-center font-bold text-xl ${suit === 'H' || suit === 'D' ? 'text-red-500' : 'text-white'}`}>
              {SUIT_ICONS[suit]}
            </div>

            {RANK_ORDER.map(rank => {
              const cardId = `${rank}${suit}`;
              const taken = isTaken(rank, suit);
              const mine = isMine(rank, suit);

              return (
                <button
                  key={cardId}
                  onClick={() => onSelect(rank, suit)}
                  disabled={taken}
                  className={`
                            relative h-12 rounded flex items-center justify-center font-bold text-lg
                            transition-all border
                            ${taken
                      ? 'bg-slate-900 text-slate-600 border-slate-800 cursor-not-allowed'
                      : mine
                        ? 'bg-green-600 text-white border-green-400 shadow-md ring-2 ring-green-300'
                        : 'bg-white hover:bg-yellow-100 border-slate-300 shadow-sm hover:-translate-y-1 text-black'
                    }
                            ${!taken && !mine && (suit === 'H' || suit === 'D') ? 'text-red-600' : ''}
                        `}
                >
                  {rank}
                  <span className="text-xs absolute top-0.5 right-1 opacity-50">{SUIT_ICONS[suit]}</span>
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

export default CardPicker;
