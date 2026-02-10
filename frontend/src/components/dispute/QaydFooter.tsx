import React from 'react';
import { QaydStep, BG_DARK, BORDER } from './types';

interface QaydFooterProps {
  step: QaydStep;
  timeLeft: number;
  timerDuration: number;
  reporterName: string;
  onBack: () => void;
}

export default function QaydFooter({ step, timeLeft, timerDuration, reporterName, onBack }: QaydFooterProps) {
  if (step === 'RESULT') return null;

  const progress = timerDuration > 0 ? (timeLeft / timerDuration) * 100 : 0;
  const dashOffset = 100 - progress;

  return (
    <div className="flex items-center justify-between px-5 py-3"
         style={{ background: BG_DARK, borderTop: `1px solid ${BORDER}` }}>
      <div className="flex items-center gap-3">
        {(step === 'SELECT_CARD_1' || step === 'SELECT_CARD_2' || step === 'VIOLATION_SELECT') && (
          <button onClick={onBack}
            className="px-4 py-2 rounded-lg text-sm font-tajawal text-gray-300 hover:text-white bg-[#555] hover:bg-[#666] transition-all">
            ← رجوع
          </button>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 bg-[#333] px-4 py-2 rounded-lg">
          <span className="text-gray-400 text-sm font-tajawal">:المقيد</span>
          <span className="text-[10px]">👑</span>
          <span className="text-white font-bold font-tajawal">{reporterName}</span>
        </div>

        <div className="relative w-10 h-10 flex items-center justify-center">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="16" fill="none" stroke="#333" strokeWidth="3" />
            <circle cx="18" cy="18" r="16" fill="none"
              stroke={timeLeft <= 10 ? '#F44336' : '#FBBF24'}
              strokeWidth="3" strokeDasharray="100" strokeDashoffset={dashOffset}
              className="transition-all duration-1000 ease-linear" />
          </svg>
          <span className={`absolute font-bold font-mono text-xs ${timeLeft <= 10 ? 'text-red-400' : 'text-white'}`}>
            {timeLeft}
          </span>
        </div>
      </div>
    </div>
  );
}
