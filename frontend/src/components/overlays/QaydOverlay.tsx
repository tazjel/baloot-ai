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
          onAccusation(
            acc.violation_type || 'REVOKE',
            acc.crime_card,
            0,
            acc.crime_card?.played_by || 'Unknown',
            acc.proof_card
          );
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
