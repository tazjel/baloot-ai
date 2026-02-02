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
      <div className="flex items-center justify-between px-4 py-3 bg-gray-800/90 rounded-t-2xl">
        <div className="flex items-center gap-3">
          {/* Timer */}
          <div className="flex items-center gap-1 bg-yellow-500/20 px-3 py-1 rounded-full">
            <Clock size={16} className="text-yellow-400" />
            <span className="text-yellow-400 font-bold font-mono">{timeLeft}</span>
          </div>
        </div>

        {/* Title */}
        <div className="flex items-center gap-2 text-right">
          {step === 'SELECT_CARD' && (
            <span className={`text-sm ${instructionColor}`}>
              أختر الورقة التي <span className="font-bold">{instructionAr}</span>
            </span>
          )}
          <span className="text-gray-300 font-bold font-tajawal">{titleAr}</span>
        </div>
      </div>
    );
  };

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
            className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-4 rounded-xl font-bold transition-colors min-w-[140px]"
          >
            <span className="block text-sm text-gray-400">{opt.label}</span>
            <span className="block text-lg font-tajawal">{opt.labelAr}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );

  const renderViolationButtons = () => (
    <div className="px-4 py-3 bg-gray-800/50 flex flex-wrap justify-center gap-2">
      {filteredViolations.map((v) => (
        <motion.button
          key={v.type}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => handleViolationSelect(v.type as ViolationType)}
          className={`px-4 py-2 rounded-lg font-bold transition-all ${
            selectedViolation === v.type
              ? 'bg-amber-500 text-black shadow-lg'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <span className="block text-xs text-gray-400">{v.label}</span>
          <span className="block font-tajawal">{v.labelAr}</span>
        </motion.button>
      ))}
    </div>
  );

  const renderTrickHistory = () => (
    <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
      {tricks.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <Gavel size={48} className="mx-auto mb-2 opacity-50" />
          <p className="font-tajawal">لا توجد أكلات للمراجعة</p>
          <p className="text-sm">No tricks to review</p>
        </div>
      ) : (
        tricks.map((trick) => (
          <motion.div
            key={trick.trickNumber}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gray-800/60 rounded-xl p-3 border border-gray-700"
          >
            {/* Trick Header */}
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-gray-500">Trick {trick.trickNumber}</span>
              <span className="text-sm font-tajawal text-gray-400">
                الأكلة {trick.trickNumber}
              </span>
            </div>

            {/* Cards */}
            <div className="flex justify-center gap-2 flex-wrap">
              {trick.cards.map((play, idx) => {
                const isSelected =
                  selectedCard?.card.id === play.card.id &&
                  selectedCard?.trickNumber === trick.trickNumber;

                return (
                  <motion.div
                    key={`${trick.trickNumber}-${idx}`}
                    whileHover={{ scale: 1.1, y: -5 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() =>
                      step === 'SELECT_CARD' &&
                      handleCardSelect(play.card, trick.trickNumber, play.playedBy)
                    }
                    className={`relative cursor-pointer transition-all ${
                      isSelected ? 'ring-4 ring-pink-500 ring-offset-2 ring-offset-gray-900 rounded-lg' : ''
                    }`}
                  >
                    {/* Card */}
                    <div className="w-16 h-24">
                      <CardVector card={play.card} className="w-full h-full rounded-lg shadow-md" />
                    </div>

                    {/* Player Label */}
                    <div className="absolute -bottom-5 left-0 right-0 text-center">
                      <span className="text-[10px] text-gray-500 truncate block">
                        {play.playedBy}
                      </span>
                    </div>

                    {/* Selection Highlight */}
                    {isSelected && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="absolute inset-0 bg-pink-500/30 rounded-lg pointer-events-none"
                      />
                    )}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        ))
      )}
    </div>
  );

  const renderResult = () => {
    if (!result) return null;

    const isSuccess = result.success;

    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="p-6 flex flex-col items-center gap-4"
      >
        {/* Result Banner */}
        <div
          className={`w-full py-4 px-6 rounded-xl flex items-center justify-center gap-3 ${
            isSuccess ? 'bg-green-500' : 'bg-red-500'
          }`}
        >
          {isSuccess ? (
            <CheckCircle size={32} className="text-white" />
          ) : (
            <XCircle size={32} className="text-white" />
          )}
          <div className="text-center">
            <span className="text-white font-bold text-lg block">
              نتيجة القيد: {isSuccess ? 'صحيح' : 'خطأ'}
            </span>
            <span className="text-white/80 text-sm">
              Result: {isSuccess ? 'CORRECT' : 'INCORRECT'}
            </span>
          </div>
        </div>

        {/* Violation Type */}
        <div className="bg-gray-700 px-4 py-2 rounded-lg">
          <span className="text-gray-400 text-sm">نوع القيد: </span>
          <span className="text-white font-bold">{result.violationType}</span>
        </div>

        {/* Accused Player */}
        <div className="text-gray-400">
          <span>المتهم: </span>
          <span className="text-yellow-400 font-bold">{result.accusedPlayer}</span>
        </div>

        {/* Close Button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onCancel}
          className="mt-4 bg-gray-600 hover:bg-gray-500 text-white px-8 py-3 rounded-xl font-bold"
        >
          إغلاق
        </motion.button>
      </motion.div>
    );
  };

  const renderFooter = () => {
    if (step === 'RESULT') return null;

    return (
      <div className="px-4 py-3 bg-gray-800/90 rounded-b-2xl flex justify-between items-center">
        {/* Left: Accuser Info */}
        <div className="flex items-center gap-2">
          <span className="text-gray-500 text-sm">المقيد:</span>
          <span className="text-yellow-400 font-bold font-tajawal">
            {gameState.players[0]?.name || 'أنت'}
          </span>
        </div>

        {/* Right: Action Buttons */}
        <div className="flex gap-2">
          {step !== 'MAIN_MENU' && (
            <button
              onClick={handleBack}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
            >
              رجوع
            </button>
          )}

          {step === 'SELECT_CARD' && selectedCard && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleConfirm}
              className="px-6 py-2 bg-amber-500 hover:bg-amber-400 text-black font-bold rounded-lg transition-colors"
            >
              قيدها
            </motion.button>
          )}

          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
          >
            إغلاق
          </button>
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
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className="bg-gray-900 w-full max-w-2xl max-h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-700"
        >
          {/* Header */}
          {renderHeader()}

          {/* Violation Type Buttons (shown in SELECT_VIOLATION and SELECT_CARD steps) */}
          {(step === 'SELECT_VIOLATION' || step === 'SELECT_CARD') && renderViolationButtons()}

          {/* Content Area */}
          <div className="flex-1 overflow-hidden flex flex-col">
            {step === 'MAIN_MENU' && renderMainMenu()}
            {step === 'SELECT_VIOLATION' && (
              <div className="p-6 text-center text-gray-400">
                <p className="font-tajawal">اختر نوع المخالفة من الأعلى</p>
                <p className="text-sm">Select violation type above</p>
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
