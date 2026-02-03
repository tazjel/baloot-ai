import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GameState, CardModel, PlayerPosition} from '../../types';
import CardVector from '../CardVector';
import { Gavel, X, CheckCircle, XCircle, Clock } from 'lucide-react';

// =============================================================================
// TYPES
// =============================================================================

type QaydStep = 'MAIN_MENU' | 'SELECT_VIOLATION' | 'SELECT_CARD' | 'RESULT';

type QaydMainOption = 'REVEAL_CARDS' | 'WRONG_SAWA' | 'WRONG_AKKA';

// Hokum violation types
type HokumViolation = 'REVOKE' | 'TRUMP_IN_CLOSED' | 'NO_OVERTRUMP' | 'NO_TRUMP';

// Sun violation types
type SunViolation = 'REVOKE' | 'NO_HIGHER_CARD';

type ViolationType = HokumViolation | SunViolation;

interface TrickPlay {
  card: CardModel;
  playedBy: PlayerPosition;
}

interface TrickRecord {
  cards: TrickPlay[];
  winner?: PlayerPosition;
  trickNumber: number;
}

interface QaydResult {
  success: boolean;
  violationType: string;
  accusedPlayer: string;
  penaltyPoints?: number;
  isGuilty?: boolean;
}

// =============================================================================
// PROPS
// =============================================================================

interface QaydOverlayProps {
  gameState: GameState;
  isHokum: boolean; // true = Hokum, false = Sun
  isClosedDouble?: boolean; // For "Trump in Closed Double" option
  onAccusation: (
    violationType: ViolationType,
    accusedCard: CardModel,
    trickNumber: number,
    accusedPlayer: PlayerPosition
  ) => void;
  onCancel: () => void;
  result?: QaydResult | null; // When result comes back from server
}

// =============================================================================
// CONSTANTS
// =============================================================================

const HOKUM_VIOLATIONS: { type: HokumViolation; label: string; labelAr: string }[] = [
  { type: 'REVOKE', label: 'Revoke', labelAr: 'قاطع' },
  { type: 'TRUMP_IN_CLOSED', label: 'Trump in Double', labelAr: 'ربع في الدبل' },
  { type: 'NO_OVERTRUMP', label: "Didn't Overtrump", labelAr: 'ما كبر بحكم' },
  { type: 'NO_TRUMP', label: "Didn't Trump", labelAr: 'ما دق بحكم' },
];

const SUN_VIOLATIONS: { type: SunViolation; label: string; labelAr: string }[] = [
  { type: 'REVOKE', label: 'Revoke', labelAr: 'قاطع' },
  { type: 'NO_HIGHER_CARD', label: "Didn't Play Higher", labelAr: 'ما كبر' },
];

const MAIN_MENU_OPTIONS: { type: QaydMainOption; label: string; labelAr: string }[] = [
  { type: 'REVEAL_CARDS', label: 'Reveal Cards', labelAr: 'اكشف الورق' },
  { type: 'WRONG_SAWA', label: 'Wrong Sawa', labelAr: 'سوا خطأ' },
  { type: 'WRONG_AKKA', label: 'Wrong Akka', labelAr: 'أكة خاطئة' },
];

const TIMER_SECONDS = 60;

// =============================================================================
// COMPONENT
// =============================================================================

export const QaydOverlay: React.FC<QaydOverlayProps> = ({
  gameState,
  isHokum,
  isClosedDouble = false,
  onAccusation,
  onCancel,
  result,
}) => {
  // State
  const [step, setStep] = useState<QaydStep>(result ? 'RESULT' : 'MAIN_MENU');
  const [mainOption, setMainOption] = useState<QaydMainOption | null>(null);
  const [selectedViolation, setSelectedViolation] = useState<ViolationType | null>(null);
  const [selectedCard, setSelectedCard] = useState<{
    card: CardModel;
    trickNumber: number;
    playedBy: PlayerPosition;
  } | null>(null);
  const [timeLeft, setTimeLeft] = useState(TIMER_SECONDS);

  // Get tricks from game state
  const tricks: TrickRecord[] = (gameState.currentRoundTricks || []).map((t: any, idx: number) => ({
    cards: t.cards || [],
    winner: t.winner,
    trickNumber: idx + 1,
  }));

  // Timer countdown
  useEffect(() => {
    if (step === 'RESULT') return;

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          onCancel();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [step, onCancel]);

  // Update step when result arrives
  useEffect(() => {
    if (result) {
      setStep('RESULT');
    }
  }, [result]);

  // Get violations based on game mode
  const violations = isHokum ? HOKUM_VIOLATIONS : SUN_VIOLATIONS;

  // Filter out "Trump in Closed" if not applicable
  const filteredViolations = violations.filter(v => {
    if (v.type === 'TRUMP_IN_CLOSED' && !isClosedDouble) return false;
    return true;
  });

  // Handlers
  const handleMainOptionSelect = (option: QaydMainOption) => {
    setMainOption(option);
    if (option === 'REVEAL_CARDS') {
      setStep('SELECT_VIOLATION');
    } else {
      // For WRONG_SAWA and WRONG_AKKA, go directly to player selection
      // (simplified for now - can be expanded later)
      setStep('SELECT_VIOLATION');
    }
  };

  const handleViolationSelect = (violation: ViolationType) => {
    setSelectedViolation(violation);
    setStep('SELECT_CARD');
  };

  const handleCardSelect = (card: CardModel, trickNumber: number, playedBy: PlayerPosition) => {
    setSelectedCard({ card, trickNumber, playedBy });
  };

  const handleConfirm = () => {
    if (selectedViolation && selectedCard) {
      onAccusation(
        selectedViolation,
        selectedCard.card,
        selectedCard.trickNumber,
        selectedCard.playedBy
      );
    }
  };

  const handleBack = () => {
    if (step === 'SELECT_CARD') {
      setSelectedCard(null);
      setStep('SELECT_VIOLATION');
    } else if (step === 'SELECT_VIOLATION') {
      setSelectedViolation(null);
      setMainOption(null);
      setStep('MAIN_MENU');
    }
  };

  // =============================================================================
  // RENDER FUNCTIONS
  // =============================================================================

  const renderHeader = () => {
    let titleAr = 'نوع القيد';
    let instructionAr = '';
    let instructionColor = 'text-white';

    if (step === 'SELECT_CARD') {
      if (selectedCard) {
        instructionAr = 'كشفت الغش';
        instructionColor = 'text-green-400';
      } else {
        instructionAr = 'تم الغش بها';
        instructionColor = 'text-red-400';
      }
    }

    return (
      <div className="flex items-center justify-between px-6 py-4 bg-[#404040] border-b border-[#555555]">
        {/* Left: Simple Title or Empty */}
         <div className="text-white/50 text-xs font-tajawal">
            Forensic Challenge
         </div>

        {/* Center: Instruction */}
        <div className="flex-1 text-center">
             {step === 'SELECT_CARD' && (
                <span className={`text-base ${instructionColor} font-tajawal`}>
                اختر الورقة التي <span className="font-bold">{instructionAr}</span>
                </span>
            )}
        </div>

        {/* Right: Main Title - "نوع القيد" or similar */}
        <div className="text-right">
             <span className="text-white font-medium font-tajawal text-lg">{titleAr}</span>
        </div>
      </div>
    );
  };
  
  // NOTE: renderMainMenu also needs styling update to match Stitch (Tabs/Buttons)
  // ...

  const renderMainMenu = () => (
    <div className="p-6 flex flex-col items-center gap-4">
      <h3 className="text-lg text-gray-300 font-tajawal mb-2">اختر نوع المخالفة</h3>
      <div className="flex gap-3 flex-wrap justify-center">
        {MAIN_MENU_OPTIONS.map((opt) => (
          <motion.button
            key={opt.type}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => handleMainOptionSelect(opt.type)}
            className="group relative bg-white/5 hover:bg-white/10 border border-white/10 hover:border-amber-500/50 text-white px-6 py-5 rounded-2xl transition-all min-w-[140px] flex flex-col items-center gap-2"
          >
            <div className="absolute inset-0 bg-amber-500/0 group-hover:bg-amber-500/5 rounded-2xl transition-all" />
            <span className="text-2xl font-black font-tajawal group-hover:text-amber-400 transition-colors">{opt.labelAr}</span>
            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-sans">{opt.label}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );

  const renderViolationButtons = () => (
    <div className="px-6 py-4 bg-[#404040] flex flex-wrap justify-center flex-row-reverse gap-3">
      {filteredViolations.map((v) => (
        <motion.button
          key={v.type}
          whileTap={{ scale: 0.95 }}
          onClick={() => handleViolationSelect(v.type as ViolationType)}
          className={`px-6 py-2 rounded-xl font-bold font-tajawal text-sm transition-all shadow-md ${
            selectedViolation === v.type
              ? 'bg-[#E0E0E0] text-black shadow-inner'
              : 'bg-[#555555] text-gray-300 hover:bg-[#666666]'
          }`}
        >
          {v.labelAr}
        </motion.button>
      ))}
    </div>
  );

  const renderTrickHistory = () => (
    <div className="flex-1 overflow-y-auto px-2 py-2 space-y-2">
      {tricks.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <Gavel size={48} className="mx-auto mb-2 opacity-50" />
          <p className="font-tajawal">لا توجد أكلات للمراجعة</p>
        </div>
      ) : (
        tricks.map((trick) => (
          <div
            key={trick.trickNumber}
            className="bg-[#404040] rounded-xl p-3 shadow-sm border border-[#555555]"
          >
            {/* Trick Header */}
            <div className="flex justify-between items-center mb-3 px-2 border-b border-[#555555] pb-2">
               {/* Left: Empty or Winner */}
               <span></span>
              <span className="text-sm font-bold font-tajawal text-white">
                الأكلة {trick.trickNumber}
              </span>
            </div>

            {/* Cards */}
            <div className="flex justify-center gap-2">
              {trick.cards.map((play, idx) => {
                const isSelected =
                  selectedCard?.card.id === play.card.id &&
                  selectedCard?.trickNumber === trick.trickNumber;

                return (
                  <div
                    key={`${trick.trickNumber}-${idx}`}
                    onClick={() =>
                      step === 'SELECT_CARD' &&
                      handleCardSelect(play.card, trick.trickNumber, play.playedBy)
                    }
                    className={`relative cursor-pointer transition-transform hover:scale-105 ${
                      isSelected ? 'ring-4 ring-yellow-400 rounded-md z-10' : ''
                    }`}
                  >
                    {/* Card */}
                    <div className="w-14 h-20">
                      <CardVector card={play.card} className="w-full h-full rounded shadow-md" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderResult = () => {
    if (!result) return null;

    const isSuccess = result.isGuilty !== undefined ? result.isGuilty : result.success;

    return (
      <div className="flex-1 flex flex-col items-center justify-start p-6 gap-4 overflow-y-auto">
        {/* Result Banner */}
        <div
          className={`w-full py-4 px-6 rounded-xl flex items-center justify-between shadow-md ${
            isSuccess 
              ? 'bg-[#4CAF50]' 
              : 'bg-[#F44336]'
          }`}
        >
          {/* Icon */}
          <div className="bg-white/20 p-2 rounded-full">
              {isSuccess ? <CheckCircle className="text-white" size={32} /> : <XCircle className="text-white" size={32} />}
          </div>

          {/* Text */}
          <div className="text-right">
            <span className="text-white font-bold font-tajawal text-xl block">
              {isSuccess ? 'تم كشف الغش' : 'اتهام خاطئ'}
            </span>
            <span className="text-white/80 font-tajawal text-sm">
              {isSuccess ? 'تم تسجيل القيد بنجاح' : 'لم يتم العثور على مخالفة'}
            </span>
          </div>
        </div>

        {/* Details Block */}
        <div className="w-full bg-[#404040] rounded-xl p-4 border border-[#555555] flex flex-col gap-3">
             {/* Violation Type */}
            <div className="flex justify-between items-center border-b border-[#555555] pb-3">
              <span className="text-gray-400 font-tajawal text-sm">نوع المخالفة</span>
              <span className="text-white font-bold font-tajawal">{result.violationType}</span>
            </div>

            {/* Accused Player */}
            <div className="flex justify-between items-center">
              <span className="text-gray-400 font-tajawal text-sm">المتهم</span>
              <span className="text-yellow-400 font-bold font-tajawal">{result.accusedPlayer}</span>
            </div>
            
            {/* Penalty Info (if applicable) */}
            {result.penaltyPoints && (
                <div className="flex justify-between items-center border-t border-[#555555] pt-3 mt-1">
                  <span className="text-gray-400 font-tajawal text-sm">النقاط</span>
                  <span className="text-red-400 font-bold font-tajawal">-{result.penaltyPoints}</span>
                </div>
            )}
        </div>

        {/* Close Button (Large) */}
        <button
          onClick={onCancel}
          className="w-full mt-auto bg-[#888888] hover:bg-[#999999] text-[#333333] border border-[#666666] px-8 py-3 rounded-lg font-bold font-tajawal text-lg transition-all shadow-lg"
        >
          إغلاق
        </button>
      </div>
    );
  };

  const renderFooter = () => {
    if (step === 'RESULT') return null;

    return (
      <div className="px-6 py-4 bg-[#404040] rounded-b-[20px] flex justify-between items-center">
        {/* Left: Submit Button (If Card Selected) */}
         <div className="flex-1 flex justify-start">
             {/* If MAIN MENU, show nothing or close */}
             {step === 'SELECT_CARD' && selectedCard && (
                <motion.button
                    whileTap={{ scale: 0.95 }}
                    onClick={handleConfirm}
                    className="px-8 py-2 bg-[#888888] hover:bg-[#999999] text-[#333333] font-bold font-tajawal rounded-lg shadow-lg"
                >
                    قيدها
                </motion.button>
             )}
         </div>

        {/* Center/Right: Caller Info + Timer */}
        <div className="flex items-center gap-4">
             {/* Name */}
             <div className="flex items-center gap-4 bg-[#333333] px-4 py-2 rounded-lg">
                <span className="text-white font-bold font-tajawal">{gameState.players[0]?.name || 'أنت'}</span>
                {/* Crown Icon */}
                 <div className="w-4 h-4 rounded-full bg-yellow-500 flex items-center justify-center">
                    <span className="text-black text-[10px]">👑</span>
                 </div>
                <span className="text-gray-400 text-sm font-tajawal">:المقيد</span>
             </div>

             {/* Circular Timer (Small Yellow/Black) */}
             <div className="relative w-10 h-10 flex items-center justify-center">
                 <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                    <circle cx="18" cy="18" r="16" fill="none" className="stroke-[#333333]" strokeWidth="3" />
                    <circle cx="18" cy="18" r="16" fill="none" className="stroke-yellow-400" strokeWidth="3" strokeDasharray="100" strokeDashoffset={100 - (timeLeft/60)*100} />
                 </svg>
                 <span className="absolute text-white font-bold font-mono text-xs">{timeLeft}</span>
             </div>
        </div>
      </div>
    );
  };

  // =============================================================================
  // MAIN RENDER
  // =============================================================================

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.9, y: 20, opacity: 0 }}
          animate={{ scale: 1, y: 0, opacity: 1 }}
          exit={{ scale: 0.9, y: 20, opacity: 0 }}
          className="bg-[#404040] w-full max-w-2xl max-h-[85vh] rounded-[20px] shadow-2xl flex flex-col overflow-hidden text-right"
        >
          {/* Header */}
          {renderHeader()}

          {/* Violation Type Buttons (shown in SELECT_VIOLATION and SELECT_CARD steps) */}
          {(step === 'SELECT_VIOLATION' || step === 'SELECT_CARD') && renderViolationButtons()}

          {/* Content Area */}
          <div className="flex-1 overflow-hidden flex flex-col bg-[#333333] m-2 rounded-xl">
            {step === 'MAIN_MENU' && renderMainMenu()}
            {step === 'SELECT_VIOLATION' && (
              <div className="p-6 text-center text-gray-400">
                <p className="font-tajawal">اختر نوع المخالفة من الأعلى</p>
              </div>
            )}
            {step === 'SELECT_CARD' && renderTrickHistory()}
            {step === 'RESULT' && renderResult()}
          </div>

          {/* Footer */}
          {renderFooter()}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default QaydOverlay;
