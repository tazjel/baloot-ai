import React, { useState, useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GameState, CardModel, PlayerPosition, QaydStep } from '../types';
import { ShieldAlert, X } from 'lucide-react';

// Sub-components
import QaydMainMenu from './dispute/QaydMainMenu';
import QaydCardSelector from './dispute/QaydCardSelector';
import QaydVerdictPanel from './dispute/QaydVerdictPanel';
import QaydFooter from './dispute/QaydFooter';
import {
  MainMenuOption,
  ViolationType,
  CardSelection,
  TrickRecord,
  VIOLATION_TYPES_HOKUM,
  VIOLATION_TYPES_SUN,
  BG_DARK,
  BG_DARKER,
  BORDER,
} from './dispute/types';

// ═══════════════════════════════════════════════════════════════════════════════
//  PROPS
// ═══════════════════════════════════════════════════════════════════════════════

interface DisputeModalProps {
  gameState: GameState;
  onAction: (action: string, payload?: any) => void;
  onClose: () => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  COMPONENT — Orchestrator
// ═══════════════════════════════════════════════════════════════════════════════

const DisputeModal: React.FC<DisputeModalProps> = ({ gameState, onAction, onClose }) => {
  // ─── Derived from server state ─────────────────────────────────────────────
  const qaydState   = gameState.qaydState;
  const serverStep  = qaydState?.step;
  const isActive    = !!qaydState?.active;
  const reporterPos = qaydState?.reporter;
  const isReporter  = reporterPos === gameState.players[0]?.position;
  const isBot       = qaydState?.reporter_is_bot ?? false;
  const isHokum     = gameState.gameMode === 'HOKUM';
  const isDoubled   = (gameState.doublingLevel ?? 1) >= 2;

  // ─── Local UI state ────────────────────────────────────────────────────────
  const [step, setStep]                   = useState<QaydStep>(serverStep || 'MAIN_MENU');
  const [menuOption, setMenuOption]       = useState<MainMenuOption | null>(null);
  const [violation, setViolation]         = useState<ViolationType | null>(null);
  const [crimeCard, setCrimeCard]         = useState<CardSelection | null>(null);
  const [proofCard, setProofCard]         = useState<CardSelection | null>(null);
  const [timeLeft, setTimeLeft]           = useState(isBot ? 2 : 60);

  // ─── Verdict data ──────────────────────────────────────────────────────────
  const verdictData = useMemo(() => {
    if (!qaydState) return null;
    const v = qaydState.verdict;
    if (!v) return null;
    const isCorrect = v === 'CORRECT';
    return {
      isCorrect,
      message: qaydState.verdict_message ?? (isCorrect ? 'قيد صحيح' : 'قيد خاطئ'),
      reason: qaydState.reason ?? '',
      penalty: qaydState.penalty_points ?? 0,
      loserTeam: qaydState.loser_team,
    };
  }, [qaydState]);

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
    if (!isReporter) return;

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
  }, [step, verdictData]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Timeout fallback: if RESULT step has no verdict after 10s, auto-cancel ─
  useEffect(() => {
    if (step === 'RESULT' && !verdictData) {
      const t = setTimeout(() => {
        onAction('QAYD_CANCEL');
      }, 10000);
      return () => clearTimeout(t);
    }
  }, [step, verdictData]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Derived data ──────────────────────────────────────────────────────────
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

  const violations = useMemo(() => {
    const list = isHokum ? VIOLATION_TYPES_HOKUM : VIOLATION_TYPES_SUN;
    return list.filter(v => v.key !== 'TRUMP_IN_DOUBLE' || isDoubled);
  }, [isHokum, isDoubled]);

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
    } else if (step === 'SELECT_CARD_1') {
      setCrimeCard(null);
      setStep('VIOLATION_SELECT');
    } else if (step === 'VIOLATION_SELECT') {
      setViolation(null);
      setStep('MAIN_MENU');
      onAction('QAYD_CANCEL');
    }
  };

  // ═══════════════════════════════════════════════════════════════════════════
  //  RENDER — Compose sub-components
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[9999] flex items-center justify-center p-3"
        role="alertdialog"
        aria-modal="true"
        aria-label="Dispute review"
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
                className="text-gray-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10"
                aria-label="Cancel dispute">
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

          {/* CONTENT */}
          <div className="flex-1 overflow-hidden flex flex-col" style={{ background: BG_DARKER }}>
            {step === 'MAIN_MENU' && (
              <QaydMainMenu
                isReporter={isReporter}
                reporterName={reporterName}
                onMenuSelect={handleMenuSelect}
              />
            )}
            {step === 'VIOLATION_SELECT' && (
              <div className="flex flex-col items-center gap-4 py-6 px-4">
                <p className="text-gray-300 font-tajawal text-base mb-2">اختر نوع المخالفة</p>
                <div className="flex flex-row-reverse flex-wrap justify-center gap-3">
                  {violations.map(v => (
                    <motion.button
                      key={v.key}
                      whileHover={{ scale: 1.05, y: -2 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => handleViolationSelect(v.key)}
                      className="px-6 py-3 rounded-xl font-bold font-tajawal text-sm
                                 bg-white/5 border border-white/10 text-gray-300
                                 hover:bg-amber-500/20 hover:border-amber-500/50 hover:text-amber-400
                                 transition-all shadow-sm"
                    >
                      {v.ar}
                    </motion.button>
                  ))}
                </div>
              </div>
            )}
            {(step === 'SELECT_CARD_1' || step === 'SELECT_CARD_2') && (
              <QaydCardSelector
                step={step}
                tricks={tricks}
                crimeCard={crimeCard}
                proofCard={proofCard}
                violations={violations}
                violation={violation}
                players={gameState.players}
                onCardClick={handleCardClick}
                onViolationSelect={handleViolationSelect}
              />
            )}
            {step === 'RESULT' && (
              <QaydVerdictPanel
                verdictData={verdictData}
                crimeCard={crimeCard}
                proofCard={proofCard}
              />
            )}
          </div>

          {/* FOOTER */}
          <QaydFooter
            step={step}
            timeLeft={timeLeft}
            timerDuration={timerDuration}
            reporterName={reporterName}
            onBack={handleBack}
          />
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default DisputeModal;
