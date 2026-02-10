/**
 * gameLogic.ts — Barrel re-export file.
 * 
 * This module has been decomposed into focused sub-modules:
 *   - projectUtils.ts  — Project detection, comparison, conflict resolution
 *   - scoringUtils.ts  — Point values, card strength, score calculation
 *   - trickUtils.ts    — Trick winner, move validation, invalid move reasons
 *   - sortUtils.ts     — Hand sorting (suit grouping + color alternation)
 *   - deckUtils.ts     — Deck generation (Fisher-Yates shuffle)
 *   - akkaUtils.ts     — Akka/Kawesh eligibility checks
 * 
 * All existing imports from this file continue to work via re-exports.
 */

// --- Project Logic ---
export { detectProjects, compareProjects, getProjectScoreValue, resolveProjectConflicts, SEQUENCE_ORDER } from './projectUtils';

// --- Scoring Logic ---
export { POINT_VALUES, STRENGTH_ORDER, getCardStrength, calculateFinalScore } from './scoringUtils';

// --- Trick Logic ---
export { getTrickWinner, isValidMove, getInvalidMoveReason } from './trickUtils';

// --- Sorting Logic ---
export { getSortRank, sortHand } from './sortUtils';

// --- Deck Logic ---
export { generateDeck } from './deckUtils';

// --- Akka & Kawesh Logic ---
export { cardKey, buildPlayedCardsSet, canDeclareAkka, scanHandForAkka, canDeclareKawesh } from './akkaUtils';
