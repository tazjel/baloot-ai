import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle, ChevronRight } from 'lucide-react';
import CardVector from '../CardVector';
import { CardSelection } from './types';

interface VerdictData {
  isCorrect: boolean;
  message: string;
  reason: string;
  penalty: number;
  loserTeam: string | null | undefined;
}

interface QaydVerdictPanelProps {
  verdictData: VerdictData | null;
  crimeCard: CardSelection | null;
  proofCard: CardSelection | null;
}

export default function QaydVerdictPanel({ verdictData, crimeCard, proofCard }: QaydVerdictPanelProps) {
  if (!verdictData) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const { isCorrect, message, reason, penalty } = verdictData;
  const bannerBg = isCorrect ? '#4CAF50' : '#F44336';

  return (
    <div className="flex flex-col items-center gap-6 py-8 px-6 flex-1">
      <motion.div
        initial={{ scaleX: 0, opacity: 0 }}
        animate={{ scaleX: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.1 }}
        className="w-full py-5 px-6 rounded-2xl flex items-center justify-between shadow-xl"
        style={{ background: bannerBg }}
      >
        <div className="bg-white/20 p-3 rounded-full">
          {isCorrect ? <CheckCircle className="text-white" size={36} /> : <XCircle className="text-white" size={36} />}
        </div>
        <div className="text-right flex-1 mr-4">
          <span className="text-white font-black font-tajawal text-2xl block">{message}</span>
          {penalty > 0 && (
            <span className="text-white/80 font-tajawal text-sm">
              {isCorrect ? `خسارة ${penalty} نقطة` : `عقوبة القيد الخاطئ: ${penalty}`}
            </span>
          )}
        </div>
      </motion.div>

      {crimeCard && (
        <div className="flex items-center gap-8">
          <div className="flex flex-col items-center gap-2">
            <div className="relative ring-4 ring-pink-500 rounded-lg p-1">
              <div className="w-16 h-24">
                <CardVector card={crimeCard.card} className="w-full h-full rounded shadow-lg" />
              </div>
            </div>
            <span className="text-xs text-pink-400 font-bold font-tajawal">الجريمة</span>
          </div>

          {proofCard && (
            <>
              <ChevronRight className="text-gray-500" size={24} />
              <div className="flex flex-col items-center gap-2">
                <div className="relative ring-4 ring-green-500 rounded-lg p-1">
                  <div className="w-16 h-24">
                    <CardVector card={proofCard.card} className="w-full h-full rounded shadow-lg" />
                  </div>
                </div>
                <span className="text-xs text-green-400 font-bold font-tajawal">الدليل</span>
              </div>
            </>
          )}
        </div>
      )}

      {reason && <p className="text-gray-400 font-tajawal text-sm text-center max-w-md">{reason}</p>}
    </div>
  );
}
