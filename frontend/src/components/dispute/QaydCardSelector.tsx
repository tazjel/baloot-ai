import React from 'react';
import { motion } from 'framer-motion';
import { CardModel, GameState } from '../../types';
import CardVector from '../CardVector';
import { CardSelection, TrickRecord, ViolationType, BG_DARK, BG_DARKER, BORDER } from './types';

interface QaydCardSelectorProps {
  step: 'SELECT_CARD_1' | 'SELECT_CARD_2';
  tricks: TrickRecord[];
  crimeCard: CardSelection | null;
  proofCard: CardSelection | null;
  violations: { key: ViolationType; ar: string }[];
  violation: ViolationType | null;
  players: GameState['players'];
  onCardClick: (card: CardModel, trickIdx: number, cardIdx: number, playedBy: string) => void;
  onViolationSelect: (v: ViolationType) => void;
}

export default function QaydCardSelector({
  step,
  tricks,
  crimeCard,
  proofCard,
  violations,
  violation,
  players,
  onCardClick,
  onViolationSelect,
}: QaydCardSelectorProps) {
  const isCrimeStep = step === 'SELECT_CARD_1';
  const instructionAr = isCrimeStep
    ? 'اختر الورقة التي تم الغش بها'
    : 'ابحث عن الورقة التي كشفت الغش';
  const instructionColor = isCrimeStep ? 'text-pink-400' : 'text-green-400';

  return (
    <>
      {/* Violation Bar */}
      <div className="flex flex-row-reverse flex-wrap justify-center gap-2 px-4 py-3"
           style={{ background: BG_DARK, borderBottom: `1px solid ${BORDER}` }}>
        {violations.map(v => (
          <motion.button
            key={v.key}
            whileTap={{ scale: 0.95 }}
            onClick={() => onViolationSelect(v.key)}
            className={`px-5 py-2 rounded-xl font-bold font-tajawal text-sm transition-all shadow-sm ${
              violation === v.key
                ? 'bg-[#E0E0E0] text-black shadow-inner'
                : 'bg-[#555] text-gray-300 hover:bg-[#666]'
            }`}
          >
            {v.ar}
          </motion.button>
        ))}
      </div>

      {/* Card Selection Area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <div className="text-center py-3 px-4" style={{ background: BG_DARKER }}>
          <p className={`font-tajawal text-base ${instructionColor}`}>{instructionAr}</p>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
          {tricks.length === 0 ? (
            <div className="text-center text-gray-500 py-12 font-tajawal">لا توجد أكلات للمراجعة</div>
          ) : (
            tricks.map((trick, trickIdx) => (
              <div key={trickIdx} className="rounded-xl p-3 shadow-sm border"
                   style={{ background: BG_DARK, borderColor: BORDER }}>
                <div className="flex justify-between items-center mb-2 px-1 pb-2"
                     style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <span className="text-xs text-gray-500">
                    {trick.winner ? `Winner: ${trick.winner}` : 'In Progress'}
                  </span>
                  <span className="text-sm font-bold font-tajawal text-white">
                    الأكلة {trickIdx + 1}
                  </span>
                </div>

                <div className="flex justify-center gap-3">
                  {trick.cards.map((cardOrPlay: any, cardIdx: number) => {
                    const card: CardModel = cardOrPlay?.card ?? cardOrPlay;
                    const playedBy: string = cardOrPlay?.playedBy ?? trick.playedBy?.[cardIdx] ?? '';
                    if (!card) return null;

                    const isCrime = crimeCard?.trick_idx === trickIdx && crimeCard?.card_idx === cardIdx;
                    const isProof = proofCard?.trick_idx === trickIdx && proofCard?.card_idx === cardIdx;

                    let ringStyle = '';
                    if (isCrime) ringStyle = 'ring-4 ring-pink-500 scale-105';
                    if (isProof) ringStyle = 'ring-4 ring-green-500 scale-105';

                    return (
                      <motion.div
                        key={`${trickIdx}-${cardIdx}`}
                        whileHover={{ y: -4 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => onCardClick(card, trickIdx, cardIdx, playedBy)}
                        className={`relative cursor-pointer transition-all rounded-lg ${ringStyle}`}
                      >
                        <div className="w-[52px] h-[76px]">
                          <CardVector card={card} className="w-full h-full rounded shadow-md" />
                        </div>

                        {isCrime && (
                          <div className="absolute -top-2 -right-2 bg-pink-600 text-white text-[7px] px-1.5 py-0.5 rounded-full font-bold font-tajawal shadow-lg">
                            الجريمة
                          </div>
                        )}
                        {isProof && (
                          <div className="absolute -top-2 -right-2 bg-green-600 text-white text-[7px] px-1.5 py-0.5 rounded-full font-bold font-tajawal shadow-lg">
                            الدليل
                          </div>
                        )}

                        <div className="text-center mt-1">
                          <span className="text-[9px] text-gray-500 font-tajawal">
                            {players.find(p => p.position === playedBy)?.name ?? playedBy}
                          </span>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
