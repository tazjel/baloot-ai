import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert } from 'lucide-react';
import { MainMenuOption, MAIN_MENU_OPTIONS } from './types';

interface QaydMainMenuProps {
  isReporter: boolean;
  reporterName: string;
  onMenuSelect: (opt: MainMenuOption) => void;
}

export default function QaydMainMenu({ isReporter, reporterName, onMenuSelect }: QaydMainMenuProps) {
  if (!isReporter) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-6">
        <motion.div animate={{ rotate: [0, 10, -10, 0] }} transition={{ repeat: Infinity, duration: 2 }}>
          <ShieldAlert size={56} className="text-amber-400" />
        </motion.div>
        <p className="text-xl text-white font-tajawal font-bold">جاري التحقق...</p>
        <p className="text-sm text-gray-400 font-tajawal">
          يقوم <span className="text-amber-400 font-bold">{reporterName}</span> بمراجعة اللعب
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-6 py-8 px-4">
      <p className="text-gray-300 font-tajawal text-lg">ماذا تريد أن تفعل؟</p>
      <div className="flex flex-row-reverse gap-4 flex-wrap justify-center">
        {MAIN_MENU_OPTIONS.map(opt => (
          <motion.button
            key={opt.key}
            whileHover={{ scale: 1.06, y: -2 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onMenuSelect(opt.key)}
            className="relative flex flex-col items-center gap-3 bg-white/5 hover:bg-white/10
                       border border-white/10 hover:border-amber-500/50
                       rounded-2xl px-8 py-6 min-w-[130px] transition-all group"
          >
            <span className="text-3xl">{opt.icon}</span>
            <span className="text-lg font-bold font-tajawal text-white group-hover:text-amber-400 transition-colors">
              {opt.ar}
            </span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
