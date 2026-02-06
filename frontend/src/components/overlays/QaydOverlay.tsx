/**
 * QaydOverlay — Thin compatibility wrapper.
 * 
 * The canonical Qayd UI is now DisputeModal.tsx (Kammelna 5-step flow).
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
  result?: any;
}

export const QaydOverlay: React.FC<QaydOverlayProps> = ({
  gameState,
  onAccusation,
  onCancel,
  onConfirm,
}) => {
  // Bridge old prop interface → new unified onAction
  const handleAction = (action: string, payload?: any) => {
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
        // For new 5-step actions (QAYD_MENU_SELECT, QAYD_VIOLATION_SELECT, etc),
        // emit directly via the game state socket.
        // Table.tsx's onPlayerAction handles this.
        // But since the old interface doesn't have a generic onAction,
        // we need to use the window-level emit.
        try {
          // Access the socket emit that Table passes as onPlayerAction
          // This is a known limitation of the bridge — ideally Table.tsx
          // should pass onPlayerAction directly.
          const event = new CustomEvent('qayd_action', { detail: { action, payload } });
          window.dispatchEvent(event);
        } catch (e) {
          console.warn('[QaydOverlay Bridge] Cannot forward action:', action, e);
        }
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
