import { CardModel, PlayerPosition, QaydStep } from '../../types';
export type { QaydStep };

export type MainMenuOption = 'REVEAL_CARDS' | 'WRONG_SAWA' | 'WRONG_AKKA';

export type ViolationType =
  | 'REVOKE'
  | 'TRUMP_IN_DOUBLE'
  | 'NO_OVERTRUMP'
  | 'NO_TRUMP';

export interface CardSelection {
  card: CardModel;
  trick_idx: number;
  card_idx: number;
  played_by: PlayerPosition;
}

export interface TrickRecord {
  cards: any[];
  playedBy?: string[];
  winner?: PlayerPosition;
  metadata?: any[];
}

// ═══════════════════════════════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

export const MAIN_MENU_OPTIONS: { key: MainMenuOption; ar: string; icon: string }[] = [
  { key: 'REVEAL_CARDS', ar: 'كشف الأوراق', icon: '🃏' },
  { key: 'WRONG_SAWA',   ar: 'سوا خاطئ',    icon: '🤝' },
  { key: 'WRONG_AKKA',   ar: 'أكة خاطئة',   icon: '👑' },
];

export const VIOLATION_TYPES_HOKUM: { key: ViolationType; ar: string }[] = [
  { key: 'REVOKE',          ar: 'قاطع' },
  { key: 'TRUMP_IN_DOUBLE', ar: 'ربع في الدبل' },
  { key: 'NO_OVERTRUMP',    ar: 'ما كبر بحكم' },
  { key: 'NO_TRUMP',        ar: 'ما دق بحكم' },
];

export const VIOLATION_TYPES_SUN: { key: ViolationType; ar: string }[] = [
  { key: 'REVOKE', ar: 'قاطع' },
];

export const BG_DARK   = '#404040';
export const BG_DARKER = '#333333';
export const BORDER    = '#555555';
