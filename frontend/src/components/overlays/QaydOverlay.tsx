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
    accusedPlayer: PlayerPosition,
    proofCard?: CardModel  // New: proof card for Kammelna-style two-card accusation
  ) => void;
  onCancel: () => void;
  onConfirm?: () => void; // New: for confirming pre-proposed accusations
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
  onConfirm,
  result,
}) => {
  // State
  const [step, setStep] = useState<QaydStep>(result ? 'RESULT' : 'MAIN_MENU');
  const [mainOption, setMainOption] = useState<QaydMainOption | null>(null);
  const [selectedViolation, setSelectedViolation] = useState<ViolationType | null>(null);
  
  // Two-card selection for proof-based Qayd (Kammelna-style)
  const [selectedCrimeCard, setSelectedCrimeCard] = useState<{
    card: CardModel;
    trickNumber: number;
    playedBy: PlayerPosition;
  } | null>(null);
  const [selectedProofCard, setSelectedProofCard] = useState<{
    card: CardModel;
    trickNumber: number;
    playedBy: PlayerPosition;
  } | null>(null);
  const [selectionMode, setSelectionMode] = useState<'crime' | 'proof'>('crime');
  
  // Legacy compatibility: selectedCard maps to selectedCrimeCard
  const selectedCard = selectedCrimeCard;
  
  const [timeLeft, setTimeLeft] = useState(TIMER_SECONDS);

  // Get tricks from game state
  // FIX: Backend stores 'cards' and 'playedBy' separately in round_history.
  // We must zip them to match the TrickPlay interface.
  const tricks: TrickRecord[] = (gameState.currentRoundTricks || []).map((t: any, idx: number) => {
      // Check if cards are already formatted (legacy safety) or need zipping
      const mappedCards = t.cards.map((c: any, cIdx: number) => {
           // If 'c' has 'card' prop, it's already formatted (like tableCards)
           if (c.card) return c;
           // Otherwise, zip with playedBy
           return {
               card: c,
               playedBy: t.playedBy ? t.playedBy[cIdx] : undefined
           };
      });
      return {
        cards: mappedCards,
        winner: t.winner,
        trickNumber: idx + 1,
      };
  });

  // Add current active trick (Table Cards)
  if (gameState.tableCards && gameState.tableCards.length > 0) {
    tricks.push({
      cards: gameState.tableCards as any, 
      trickNumber: tricks.length + 1,
      winner: undefined
    });
  }

  // Set timer duration: 60s for Human, 5s for AI/Others
  useEffect(() => {
    const reporterPos = gameState.qaydState?.reporter;
    // Check if local player (index 0) is the reporter
    const isLocalUserReporter = reporterPos && gameState.players[0]?.position === reporterPos;
    
    if (isLocalUserReporter) {
        setTimeLeft(60);
    } else {
        setTimeLeft(5);
    }
  }, [gameState.qaydState?.reporter]);

  // Timer countdown
  useEffect(() => {
    if (step === 'RESULT') return;

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          // TIMEOUT LOGIC
          // If status is REVIEW (e.g. Bot proposed), we auto-confirm the verdict.
          const status = gameState.qaydState?.status;
          if (status === 'REVIEW' && onConfirm) {
              console.log('[QaydOverlay] Timeout in REVIEW mode -> Auto-Confirming Verdict.');
              onConfirm();
          } else {
              console.log('[QaydOverlay] Timeout in Selection mode -> Cancelling.');
              onCancel();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [step, onCancel, onConfirm, gameState.qaydState]); // Added dep

  // lifecycle debug
  useEffect(() => {
    console.log('[QaydOverlay] MOUNTED. Active:', gameState.qaydState?.active, 'Result:', !!result);
    return () => console.log('[QaydOverlay] UNMOUNTED');
  }, []);

  // Update step when result arrives
  useEffect(() => {
    if (result) {
      console.log('[QaydOverlay] Result received. Forcing RESULT step.');
      setStep('RESULT');
      
      // Auto-close result after 5 seconds (increased from 3s for readability)
      const timer = setTimeout(() => {
          if (onCancel) onCancel();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [result, onCancel]);

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
    setSelectionMode('crime'); // Start with crime selection
    setStep('SELECT_CARD');
  };

  const handleCardSelect = (card: CardModel, trickNumber: number, playedBy: PlayerPosition) => {
    if (selectionMode === 'crime') {
      // Selecting the crime card (the illegal play)
      setSelectedCrimeCard({ card, trickNumber, playedBy });
      setSelectionMode('proof'); // Now select proof
    } else {
      // Selecting the proof card (the card that proves the crime)
      setSelectedProofCard({ card, trickNumber, playedBy });
    }
  };

  const handleConfirm = () => {
    if (selectedViolation && selectedCrimeCard && selectedProofCard) {
      // Two-card accusation (Kammelna-style)
      onAccusation(
        selectedViolation,
        selectedCrimeCard.card,
        selectedCrimeCard.trickNumber,
        selectedCrimeCard.playedBy,
        selectedProofCard.card // Pass proof card to parent
      );
    } else if (selectedViolation && selectedCrimeCard) {
      // Legacy single-card accusation
      onAccusation(
        selectedViolation,
        selectedCrimeCard.card,
        selectedCrimeCard.trickNumber,
        selectedCrimeCard.playedBy
      );
    }
  };

  const handleBack = () => {
    if (step === 'SELECT_CARD') {
      if (selectionMode === 'proof' && selectedCrimeCard) {
        // Go back from proof to crime selection
        setSelectedProofCard(null);
        setSelectionMode('crime');
      } else {
        // Go back to violation selection
        setSelectedCrimeCard(null);
        setSelectedProofCard(null);
        setSelectionMode('crime');
        setStep('SELECT_VIOLATION');
      }
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
      if (selectionMode === 'crime') {
        // Step 1: Select the crime card
        instructionAr = 'تم الغش بها';
        instructionColor = 'text-pink-400';
        // titleAr remains 'نوع القيد'
      } else if (selectionMode === 'proof') {
        // Step 2: Select the proof card
        instructionAr = 'كشفت الغش';
        instructionColor = 'text-green-400';
        // titleAr remains 'نوع القيد'
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

  // ...
  
  // RATCHET LOGIC: Prevent backwards jumps (flickering)
  const STEP_ORDER: Record<QaydStep, number> = {
    'MAIN_MENU': 0,
    'SELECT_VIOLATION': 1,
    'SELECT_CARD': 2,
    'RESULT': 3
  };

  const advanceTo = (newStep: QaydStep) => {
    setStep(current => {
        if (STEP_ORDER[newStep] > STEP_ORDER[current]) {
            return newStep;
        }
        return current;
    });
  };

  // Reactive State (Forward Only)
  const reporterPos = gameState.qaydState?.reporter;
  const isReporter = reporterPos && gameState.players[0]?.position === reporterPos;
  const isBotReporter = !isReporter && reporterPos; 

  // 1. DATA DRIVEN RATCHET (For live updates)
  useEffect(() => {
    if (result) return; // Handled by Playback below
    
    // DISABLE BOT PLAYBACK FOR NON-REPORTERS
    // We want the accused/watchers to see the "Investigating..." screen until the result is ready.
    // Advancing steps here caused the UI to show interactive controls (Select Card, etc.) 
    // which confused users into thinking they needed to act.
    
    /* 
    if (isBotReporter && gameState.qaydState?.active) {
        if (gameState.qaydState.target_play) {
             advanceTo('SELECT_CARD');
             // Update selection data safely without resetting step
             setSelectionMode('proof'); 
             const play = gameState.qaydState.target_play;
             setSelectedCrimeCard(prev => prev || { // Stick with existing if set
                 card: play.card,
                 trickNumber: 0,
                 playedBy: play.playedBy
             });
        } else if (gameState.qaydState.qayd_type) {
             advanceTo('SELECT_VIOLATION');
             const v = filteredViolations.find(v => v.type === gameState.qaydState?.qayd_type) || filteredViolations[0];
             setSelectedViolation(v.type as ViolationType);
        } else {
             // Do NOT force MAIN_MENU here. 
             // Allow initial state to be MAIN_MENU, but never revert to it automatically.
        }
    }
    */
  }, [result, isBotReporter, gameState.qaydState]);

  // 2. RESULT-DRIVEN PLAYBACK (The "Reveal" Animation)
  // When result arrives, we play a fast sequence THEN show result.
  useEffect(() => {
    if (result && step !== 'RESULT') {
        console.log('[QaydOverlay] Result received. Starting Reveal Sequence.');
        
        // Instant Setup for visualization
        if (gameState.qaydState?.target_play) {
             const play = gameState.qaydState.target_play;
             setSelectedCrimeCard({ card: play.card, trickNumber: 0, playedBy: play.playedBy });
        }
        if (gameState.qaydState?.qayd_type) {
             const v = filteredViolations.find(v => v.type === gameState.qaydState?.qayd_type) || filteredViolations[0];
             setSelectedViolation(v.type as ViolationType);
        }

        // Sequence
        const t1 = setTimeout(() => advanceTo('SELECT_VIOLATION'), 500);
        const t2 = setTimeout(() => {
            advanceTo('SELECT_CARD');
            setSelectionMode('crime');
        }, 1000);
        const t3 = setTimeout(() => {
            setSelectionMode('proof');
        }, 1500);
        const t4 = setTimeout(() => {
            setStep('RESULT'); // Force final step
        }, 2200);

        return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
    }
  }, [result]); // Only run when result changes

  const renderMainMenu = () => {
    // Watcher Mode (Human Reporter is thinking OR Bot is investigating)
    // If not the reporter, always show the "Investigating" screen unless we have a result.
    if (!isReporter) {
      return (
        <div className="flex flex-col items-center justify-center p-12 text-center h-full">
           <div className="animate-pulse bg-amber-500/20 p-4 rounded-full mb-4">
              <Gavel size={48} className="text-amber-500" />
           </div>
           <h3 className="text-xl text-white font-bold font-tajawal mb-2">جاري التحقق...</h3>
           <p className="text-gray-400 font-tajawal">
              يقوم <span className="text-amber-400 font-bold">{gameState.players.find(p => p.position === reporterPos)?.name || 'المحقق'}</span> بمراجعة اللعب
           </p>
        </div>
      );
    }

    // Interactive Mode (Me) OR Bot Playback Mode
    return (
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
  };

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
                if (!play || !play.card) return null; // Safety check
                
                // Two-card selection: Check if this card is crime or proof
                const isCrimeCard =
                  selectedCrimeCard?.card.id === play.card.id &&
                  selectedCrimeCard?.trickNumber === trick.trickNumber;
                const isProofCard =
                  selectedProofCard?.card.id === play.card.id &&
                  selectedProofCard?.trickNumber === trick.trickNumber;
                
                // Determine ring color based on selection type
                let ringClass = '';
                if (isCrimeCard) {
                  ringClass = 'ring-4 ring-pink-500 rounded-md z-10'; // Crime = Pink
                } else if (isProofCard) {
                  ringClass = 'ring-4 ring-green-500 rounded-md z-10'; // Proof = Green
                }

                return (
                  <div
                    key={`${trick.trickNumber}-${idx}`}
                    onClick={() =>
                      step === 'SELECT_CARD' &&
                      handleCardSelect(play.card, trick.trickNumber, play.playedBy)
                    }
                    className={`relative cursor-pointer transition-transform hover:scale-105 ${ringClass}`}
                  >
                    {/* Card */}
                    <div className="w-14 h-20">
                      <CardVector card={play.card} className="w-full h-full rounded shadow-md" />
                    </div>
                    {/* Label badge for selected cards */}
                    {isCrimeCard && (
                      <div className="absolute -top-2 -right-2 bg-pink-600 text-white text-[8px] px-1.5 py-0.5 rounded-full font-bold">
                        الجريمة
                      </div>
                    )}
                    {isProofCard && (
                      <div className="absolute -top-2 -right-2 bg-green-600 text-white text-[8px] px-1.5 py-0.5 rounded-full font-bold">
                        الدليل
                      </div>
                    )}
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

    // "Smoking Gun" Data
    // Assuming 'proofCard' and 'crimeCard' might be passed in result extras or we need to type QaydResult better.
    // For now, let's assume result might carry 'evidence' object. 
    // Types update: interface QaydResult { ..., evidence?: { crimeCard: CardModel, proofCard: CardModel } }
    
    // Fallback if no specific card data (legacy support)
    const evidence = (result as any).evidence;

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
              {isSuccess ? 'نتيجة القيد: صحيح' : 'نتيجة القيد: خطأ'}
            </span>
            <span className="text-white/80 font-tajawal text-sm">
              {isSuccess ? 'تم تسجيل القيد بنجاح' : 'لم يتم العثور على مخالفة'}
            </span>
          </div>
        </div>

        {/* SMOKING GUN: Side-by-Side Comparison */}
        {isSuccess && evidence && (
             <div className="w-full bg-black/40 rounded-xl p-4 border border-[#555555] flex flex-col gap-3">
                 <h4 className="text-center text-amber-500 font-bold font-tajawal mb-2 tracking-widest text-xs uppercase">
                     الأدلة الجنائية (The Smoking Gun)
                 </h4>
                 
                 <div className="flex justify-center items-center gap-8">
                      {/* The Lie */}
                      <div className="flex flex-col items-center gap-2">
                           <div className="relative">
                               <div className="w-16 h-24 rotate-[-5deg] grayscale opacity-70">
                                   <CardVector card={evidence.crimeCard} className="w-full h-full rounded shadow-lg" />
                               </div>
                               <div className="absolute top-0 right-0 -mt-2 -mr-2 bg-pink-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm">
                                   كان معه
                               </div>
                           </div>
                           <span className="text-xs text-pink-300 font-bold font-tajawal mt-1">الجريمة</span>
                      </div>

                      {/* VS */}
                      <span className="text-white/20 font-black text-xl">VS</span>

                      {/* The Truth */}
                      <div className="flex flex-col items-center gap-2">
                           <div className="relative">
                               <div className="w-16 h-24 rotate-[5deg] scale-110 z-10 shadow-[0_0_15px_rgba(255,215,0,0.3)]">
                                   <CardVector card={evidence.proofCard} className="w-full h-full rounded shadow-lg border-2 border-amber-400" />
                               </div>
                               <div className="absolute top-0 right-0 -mt-2 -mr-2 bg-green-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm">
                                   ولعب
                               </div>
                           </div>
                           <span className="text-xs text-green-300 font-bold font-tajawal mt-1">الدليل</span>
                      </div>
                 </div>
             </div>
        )}

        {/* Details Block */}
        <div className="w-full bg-[#404040] rounded-xl p-4 border border-[#555555] flex flex-col gap-3">
             {/* Violation Type */}
            <div className="flex justify-between items-center border-b border-[#555555] pb-3">
              <span className="text-gray-400 font-tajawal text-sm">نوع القيد</span>
              <span className="text-white font-bold font-tajawal">
                  {(() => {
                      const v = violations.find(v => v.type === result.violationType);
                      return v ? v.labelAr : result.violationType;
                  })()}
              </span>
            </div>

            {/* Accused Player (The Cheater) */}
            <div className="flex justify-between items-center border-b border-[#555555] pb-3">
              <span className="text-gray-400 font-tajawal text-sm">المتهم</span>
              <span className="text-yellow-400 font-bold font-tajawal">
                  {(() => {
                      const p = gameState.players.find(p => p.position === result.accusedPlayer);
                      return p ? p.name : result.accusedPlayer;
                  })()}
              </span>
            </div>

            {/* Reporter (The Accuser) */}
            <div className="flex justify-between items-center">
              <span className="text-gray-400 font-tajawal text-sm">المقيد</span>
              <div className="flex items-center gap-2">
                 <span className="text-[10px]">👑</span>
                 <span className="text-amber-400 font-bold font-tajawal">
                  {(() => {
                    // Try to find reporter name from game state if available
                    // For now, if we don't have it in result, we might need to look it up or passed in
                    const reporterPos = gameState.qaydState?.reporter;
                    if (reporterPos) {
                        const reporter = gameState.players.find(p => p.position === reporterPos);
                        return reporter ? reporter.name : reporterPos;
                    }
                    return 'أنت'; // Fallback
                  })()}
                 </span>
              </div>
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

    // Determine if we can confirm (both cards selected)
    const canConfirm = selectedCrimeCard && selectedProofCard;
    
    // Show progress indicator for two-card selection
    const selectionProgress = selectedCrimeCard 
      ? (selectedProofCard ? 'اختر قيدها للتأكيد' : 'اختر الدليل الآن')
      : 'اختر الورقة الخاطئة';

    return (
      <div className="px-6 py-4 bg-[#404040] rounded-b-[20px] flex justify-between items-center">
        {/* Left: Submit Button or Progress */}
         <div className="flex-1 flex justify-start items-center gap-3">
             {/* Back button when in proof selection */}
             {selectionMode === 'proof' && selectedCrimeCard && (
               <motion.button
                   whileTap={{ scale: 0.95 }}
                   onClick={handleBack}
                   className="px-4 py-2 bg-[#555555] hover:bg-[#666666] text-white text-sm font-tajawal rounded-lg"
               >
                   ← رجوع
               </motion.button>
             )}
             
             {/* Confirm button (only when both cards selected) */}
             {step === 'SELECT_CARD' && canConfirm && (
                <motion.button
                    whileTap={{ scale: 0.95 }}
                    onClick={handleConfirm}
                    className="px-8 py-2 bg-amber-500 hover:bg-amber-600 text-black font-bold font-tajawal rounded-lg shadow-lg"
                >
                    قيدها ✓
                </motion.button>
             )}
             
             {/* Progress text */}
             {step === 'SELECT_CARD' && !canConfirm && (
               <span className="text-gray-400 text-sm font-tajawal">{selectionProgress}</span>
             )}
         </div>

        {/* Center/Right: Caller Info + Timer */}
        <div className="flex items-center gap-4">
             {/* Name */}
             <div className="flex items-center gap-4 bg-[#333333] px-4 py-2 rounded-lg">
                <span className="text-white font-bold font-tajawal">
                  {(() => {
                    const reporterPos = gameState.qaydState?.reporter;
                    if (!reporterPos) return 'أنت';
                    const reporter = gameState.players.find(p => p.position === reporterPos);
                    return reporter ? reporter.name : 'أنت';
                  })()}
                </span>
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

  // HIDE OVERLAY FOR NON-REPORTERS UNTIL RESULT IS READY
  // User requested to remove the "Investigating..." waiting screen.
  if (!isReporter && !result) {
      return null;
  }

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
