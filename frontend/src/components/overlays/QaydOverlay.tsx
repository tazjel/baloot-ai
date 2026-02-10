/**
 * QaydOverlay — Thin compatibility wrapper.
 * 
 * The canonical Qayd UI is DisputeModal.tsx (Kammelna 5-step flow).
 * This file re-exports it with the old QaydOverlay prop interface so
 * Table.tsx doesn't need import changes.
 */

import React from 'react';
import { GameState, CardModel, PlayerPosition } from '../../types';
import DisputeModal from '../DisputeModal';

interface QaydOverlayProps {
  gameState: GameState;
  isHokum: boolean;
  isClosedDouble?: boolean;
  onAccusation: (
    violationType: string,
    accusedCard: CardModel,
    trickNumber: number,
    accusedPlayer: PlayerPosition,
    proofCard?: CardModel
  ) => void;
  onCancel: () => void;
  onConfirm?: () => void;
  onPlayerAction?: (action: string, payload?: any) => void;
  result?: any;
}

export const QaydOverlay: React.FC<QaydOverlayProps> = ({
  gameState,
  onAccusation,
  onCancel,
  onConfirm,
  onPlayerAction,
}) => {
  const handleAction = (action: string, payload?: any) => {
    // If Table.tsx passes onPlayerAction directly, use it for ALL actions
    if (onPlayerAction) {
      onPlayerAction(action, payload);
      return;
    }

    // Fallback: Map to old prop interface
    switch (action) {
      case 'QAYD_CANCEL':
        onCancel();
        break;
      case 'QAYD_CONFIRM':
        onConfirm?.();
        break;
      case 'QAYD_ACCUSATION':
        if (payload?.accusation) {
          const acc = payload.accusation;
          
          // Helper to normalize card input
          const normalizeCard = (c: any): CardModel | undefined => {
            if (!c) return undefined;
            return c.card || c;
          };

          const crime = normalizeCard(acc.crime_card);
          const proof = normalizeCard(acc.proof_card);
          // played_by might be on the wrapper or passed separately
          const playedBy: PlayerPosition = (acc.crime_card && typeof acc.crime_card === 'object' && 'playedBy' in acc.crime_card) ? (acc.crime_card as { playedBy: PlayerPosition }).playedBy : 'Unknown' as PlayerPosition;

          if (crime) {
            onAccusation(
              acc.violation_type || 'REVOKE',
              crime,
              0, // Trick number unknown here contextually
              playedBy,
              proof
            );
          }
        }
        break;
      default:
        // For 5-step actions (QAYD_MENU_SELECT, QAYD_VIOLATION_SELECT, etc.)
        // Fall back to QAYD_CANCEL if no handler available
        console.warn('[QaydOverlay] No handler for action:', action);
        break;
    }
  };

  return (
    <DisputeModal
      gameState={gameState}
      onAction={handleAction}
      onClose={onCancel}
    />
  );
};

export default QaydOverlay;
