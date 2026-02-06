import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GameState, CardModel, PlayerPosition } from '../types';
import CardVector from './CardVector';
import { ShieldAlert, X, CheckCircle, XCircle, ChevronRight } from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
//  TYPES — Matches QaydEngine state machine
// ═══════════════════════════════════════════════════════════════════════════════

type QaydStep =
  | 'IDLE'
  | 'MAIN_MENU'
  | 'VIOLATION_SELECT'
  | 'SELECT_CARD_1'
  | 'SELECT_CARD_2'
  | 'ADJUDICATION'
  | 'RESULT';

type MainMenuOption = 'REVEAL_CARDS' | 'WRONG_SAWA' | 'WRONG_AKKA';

type ViolationType =
  | 'REVOKE'
  | 'TRUMP_IN_DOUBLE'
  | 'NO_OVERTRUMP'
  | 'NO_TRUMP';

interface CardSelection {
  card: CardModel;
  trick_idx: number;
  card_idx: number;
  played_by: PlayerPosition;
}

interface TrickRecord {
  cards: any[];
  playedBy?: string[];
  winner?: PlayerPosition;
  metadata?: any[];
}

// ═══════════════════════════════════════════════════════════════════════════════
//  PROPS
// ═══════════════════════════════════════════════════════════════════════════════

interface DisputeModalProps {
  gameState: GameState;
  onAction: (action: string, payload?: any) => void;
  onClose: () => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const MAIN_MENU_OPTIONS: { key: MainMenuOption; ar: string; icon: string }[] = [
  { key: 'REVEAL_CARDS', ar: 'كشف الأوراق', icon: '🃏' },
  { key: 'WRONG_SAWA',   ar: 'سوا خاطئ',    icon: '🤝' },
  { key: 'WRONG_AKKA',   ar: 'أكة خاطئة',   icon: '👑' },
];

const VIOLATION_TYPES_HOKUM: { key: ViolationType; ar: string }[] = [
  { key: 'REVOKE',          ar: 'قاطع' },
  { key: 'TRUMP_IN_DOUBLE', ar: 'ربع في الدبل' },
  { key: 'NO_OVERTRUMP',    ar: 'ما كبر بحكم' },
  { key: 'NO_TRUMP',        ar: 'ما دق بحكم' },
];

const VIOLATION_TYPES_SUN: { key: ViolationType; ar: string }[] = [
  { key: 'REVOKE', ar: 'قاطع' },
];

const BG_DARK   = '#404040';
const BG_DARKER = '#333333';
const BORDER    = '#555555';

// ═══════════════════════════════════════════════════════════════════════════════
//  COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const DisputeModal: React.FC<DisputeModalProps> = ({ gameState, onAction, onClose }) => {
  // ─── Derived from server state ─────────────────────────────────────────────
  const qaydState   = gameState.qaydState;
  const serverStep  = (qaydState as any)?.step as QaydStep | undefined;
  const isActive    = !!qaydState?.active;
  const reporterPos = qaydState?.reporter;
  const isReporter  = reporterPos === gameState.players[0]?.position;
  const isBot       = (qaydState as any)?.reporter_is_bot ?? false;
  const isHokum     = gameState.gameMode === 'HOKUM';
  const isDoubled   = (gameState.doublingLevel ?? 1) >= 2;

  // ─── Local UI state ────────────────────────────────────────────────────────
  const [step, setStep]                   = useState<QaydStep>(serverStep || 'MAIN_MENU');
  const [menuOption, setMenuOption]       = useState<MainMenuOption | null>(null);
  const [violation, setViolation]         = useState<ViolationType | null>(null);
  const [crimeCard, setCrimeCard]         = useState<CardSelection | null>(null);
  const [proofCard, setProofCard]         = useState<CardSelection | null>(null);
  const [timeLeft, setTimeLeft]           = useState(isBot ? 2 : 60);

  // ─── Verdict data (defined early so useEffect can reference it) ────────────
  const verdictData = useMemo(() => {
    const qs = qaydState as any;
    if (!qs) return null;
    const v = qs.verdict;
    if (!v) return null;
    const isCorrect = v === 'CORRECT';
    return {
      isCorrect,
      message: qs.verdict_message ?? (isCorrect ? 'قيد صحيح' : 'قيد خاطئ'),
      reason: qs.reason ?? '',
      penalty: qs.penalty_points ?? 0,
      loserTeam: qs.loser_team,
    };
  }, [qaydState]);

  // Ref for stable access in useEffect
  const verdictRef = useRef(verdictData);
  verdictRef.current = verdictData;

  // ─── Sync with server step ─────────────────────────────────────────────────
  useEffect(() => {
    if (serverStep === 'RESULT' || serverStep === 'ADJUDICATION') {
      setStep('RESULT');
    }
  }, [serverStep]);

  // ─── Timer ─────────────────────────────────────────────────────────────────
  const timerDuration = isBot ? 2 : isReporter ? 60 : 2;

  useEffect(() => {
    setTimeLeft(timerDuration);
  }, [timerDuration]);

  useEffect(() => {
    if (step === 'RESULT') return;
    if (!isReporter) return; // Non-reporters don't have timer control

    const interval = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          onAction('QAYD_CANCEL');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [step, isReporter]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Auto-close result after 5s ────────────────────────────────────────────
  useEffect(() => {
    if (step === 'RESULT' && verdictRef.current) {
      const t = setTimeout(() => {
        onAction('QAYD_CONFIRM');
      }, 5000);
      return () => clearTimeout(t);
    }
  }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Trick history ─────────────────────────────────────────────────────────
  const tricks: TrickRecord[] = useMemo(() => {
    const list: TrickRecord[] = (gameState.currentRoundTricks || []).map((t: any) => ({
      cards: t.cards || [],
      playedBy: t.playedBy,
      winner: t.winner,
      metadata: t.metadata,
    }));

    if (gameState.tableCards?.length > 0) {
      list.push({
        cards: gameState.tableCards.map(tc => tc.card),
        playedBy: gameState.tableCards.map(tc => tc.playedBy as string),
        winner: undefined,
        metadata: gameState.tableCards.map(tc => tc.metadata),
      });
    }

    return list;
  }, [gameState.currentRoundTricks, gameState.tableCards]);

  // ─── Violations list ───────────────────────────────────────────────────────
  const violations = useMemo(() => {
    const list = isHokum ? VIOLATION_TYPES_HOKUM : VIOLATION_TYPES_SUN;
    return list.filter(v => v.key !== 'TRUMP_IN_DOUBLE' || isDoubled);
  }, [isHokum, isDoubled]);

  // ─── Reporter info ─────────────────────────────────────────────────────────
  const reporterName = useMemo(() => {
    const p = gameState.players.find(p => p.position === reporterPos);
    return p?.name ?? 'غير معروف';
  }, [gameState.players, reporterPos]);

  // ─── Handlers ──────────────────────────────────────────────────────────────
  const handleMenuSelect = (opt: MainMenuOption) => {
    setMenuOption(opt);
    onAction('QAYD_MENU_SELECT', { option: opt });
    setStep('VIOLATION_SELECT');
  };

  const handleViolationSelect = (v: ViolationType) => {
    setViolation(v);
    onAction('QAYD_VIOLATION_SELECT', { violation_type: v });
    setStep('SELECT_CARD_1');
  };

  const handleCardClick = (card: CardModel, trickIdx: number, cardIdx: number, playedBy: string) => {
    const sel: CardSelection = {
      card,
      trick_idx: trickIdx,
      card_idx: cardIdx,
      played_by: playedBy as PlayerPosition,
    };

    if (step === 'SELECT_CARD_1') {
      setCrimeCard(sel);
      onAction('QAYD_SELECT_CRIME', {
        suit: card.suit, rank: card.rank,
        trick_idx: trickIdx, card_idx: cardIdx, played_by: playedBy,
      });
      setStep('SELECT_CARD_2');
    } else if (step === 'SELECT_CARD_2') {
      setProofCard(sel);
      onAction('QAYD_SELECT_PROOF', {
        suit: card.suit, rank: card.rank,
        trick_idx: trickIdx, card_idx: cardIdx, played_by: playedBy,
      });
      setStep('RESULT');
    }
  };

  const handleBack = () => {
    if (step === 'SELECT_CARD_2') {
      setProofCard(null);
      setStep('SELECT_CARD_1');
      // Note: Backend stays at SELECT_CARD_2 step, but re-selecting crime card
      // will re-send QAYD_SELECT_CRIME which resets backend to SELECT_CARD_2.
      // This is safe because backend validates step on each action.
    } else if (step === 'SELECT_CARD_1') {
      setCrimeCard(null);
      setStep('VIOLATION_SELECT');
    } else if (step === 'VIOLATION_SELECT') {
      setViolation(null);
      setStep('MAIN_MENU');
      // Cancel and re-trigger to reset backend state
      onAction('QAYD_CANCEL');
    }
  };

  // verdictData is defined above (before useEffects) to avoid forward reference issues

  // ═══════════════════════════════════════════════════════════════════════════
  //  RENDER — MAIN MENU (Step 1)
  // ═══════════════════════════════════════════════════════════════════════════

  const renderMainMenu = () => {
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
              onClick={() => handleMenuSelect(opt.key)}
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
  };

  // ═══════════════════════════════════════════════════════════════════════════
  //  RENDER — VIOLATION SELECT (Step 2)
  // ═══════════════════════════════════════════════════════════════════════════

  const renderViolationBar = () => (
    <div className="flex flex-row-reverse flex-wrap justify-center gap-2 px-4 py-3"
         style={{ background: BG_DARK, borderBottom: `1px solid ${BORDER}` }}>
      {violations.map(v => (
        <motion.button
          key={v.key}
          whileTap={{ scale: 0.95 }}
          onClick={() => {
            if (step === 'VIOLATION_SELECT') handleViolationSelect(v.key);
            else setViolation(v.key);
          }}
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
  );

  // ═══════════════════════════════════════════════════════════════════════════
  //  RENDER — CARD SELECTION (Steps 3 & 4) — Pink Ring / Green Ring
  // ═══════════════════════════════════════════════════════════════════════════

  const renderCardSelection = () => {
    const isCrimeStep = step === 'SELECT_CARD_1';
    const instructionAr = isCrimeStep
      ? 'اختر الورقة التي تم الغش بها'
      : 'ابحث عن الورقة التي كشفت الغش';
    const instructionColor = isCrimeStep ? 'text-pink-400' : 'text-green-400';

    return (
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
                    // Handle both formats: {card: {...}, playedBy} or flat card dict {suit, rank}
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
                        onClick={() => handleCardClick(card, trickIdx, cardIdx, playedBy)}
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
                            {gameState.players.find(p => p.position === playedBy)?.name ?? playedBy}
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
    );
  };

  // ═══════════════════════════════════════════════════════════════════════════
  //  RENDER — RESULT (Step 5)
  // ═══════════════════════════════════════════════════════════════════════════

  const renderResult = () => {
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
  };

  // ═══════════════════════════════════════════════════════════════════════════
  //  RENDER — FOOTER
  // ═══════════════════════════════════════════════════════════════════════════

  const renderFooter = () => {
    if (step === 'RESULT') return null;

    const progress = timerDuration > 0 ? (timeLeft / timerDuration) * 100 : 0;
    const dashOffset = 100 - progress;

    return (
      <div className="flex items-center justify-between px-5 py-3"
           style={{ background: BG_DARK, borderTop: `1px solid ${BORDER}` }}>
        <div className="flex items-center gap-3">
          {(step === 'SELECT_CARD_1' || step === 'SELECT_CARD_2' || step === 'VIOLATION_SELECT') && (
            <button onClick={handleBack}
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
  };

  // ═══════════════════════════════════════════════════════════════════════════
  //  MAIN RENDER
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[9999] flex items-center justify-center p-3"
        style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}
      >
        <motion.div
          initial={{ scale: 0.92, y: 16, opacity: 0 }}
          animate={{ scale: 1, y: 0, opacity: 1 }}
          exit={{ scale: 0.92, y: 16, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          className="w-full max-w-2xl max-h-[88vh] rounded-[20px] shadow-2xl flex flex-col overflow-hidden text-right"
          style={{ background: BG_DARK, fontFamily: "'Tajawal', sans-serif" }}
        >
          {/* HEADER */}
          <div className="flex items-center justify-between px-5 py-3"
               style={{ background: BG_DARK, borderBottom: `1px solid ${BORDER}` }}>
            {step !== 'RESULT' && (
              <button onClick={() => onAction('QAYD_CANCEL')}
                className="text-gray-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10">
                <X size={20} />
              </button>
            )}
            <div className="flex items-center gap-2 text-xs text-gray-500 font-tajawal">
              {step === 'MAIN_MENU' && <span className="text-amber-400">نوع القيد</span>}
              {step === 'VIOLATION_SELECT' && <span className="text-amber-400">المخالفة</span>}
              {step === 'SELECT_CARD_1' && <span className="text-pink-400">الورقة الأولى</span>}
              {step === 'SELECT_CARD_2' && <span className="text-green-400">الورقة الثانية</span>}
              {step === 'RESULT' && <span className="text-white">النتيجة</span>}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-white font-bold font-tajawal text-base">قيد</span>
              <ShieldAlert size={18} className="text-amber-400" />
            </div>
          </div>

          {/* VIOLATION BAR */}
          {(step === 'VIOLATION_SELECT' || step === 'SELECT_CARD_1' || step === 'SELECT_CARD_2') && renderViolationBar()}

          {/* CONTENT */}
          <div className="flex-1 overflow-hidden flex flex-col" style={{ background: BG_DARKER }}>
            {step === 'MAIN_MENU' && renderMainMenu()}
            {step === 'VIOLATION_SELECT' && (
              <div className="flex items-center justify-center py-12 text-gray-500 font-tajawal">
                اختر نوع المخالفة من الأعلى ↑
              </div>
            )}
            {(step === 'SELECT_CARD_1' || step === 'SELECT_CARD_2') && renderCardSelection()}
            {step === 'RESULT' && renderResult()}
          </div>

          {/* FOOTER */}
          {renderFooter()}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default DisputeModal;
