import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baloot_ai/state/providers.dart';
import 'package:baloot_ai/models/enums.dart';
import 'package:baloot_ai/models/card_model.dart';
import 'package:baloot_ai/utils/akka_utils.dart';

void main() {
  CardModel card(Rank rank, Suit suit) => CardModel(id: '${rank.symbol}${suit.symbol}', rank: rank, suit: suit);

  test('KAWESH action returns same state (unchanged phase) but adds message', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Initial state: Bidding phase
    container.read(gameStateProvider.notifier).updateGameState((prev) {
      return prev.copyWith(
        phase: GamePhase.bidding,
        currentTurnIndex: 0,
        players: prev.players.map((p) => p.copyWith(isActive: true)).toList(),
      );
    });

    final initialPhase = container.read(gameStateProvider).gameState.phase;
    
    // Execute KAWESH
    container.read(biddingLogicProvider.notifier).handleBiddingAction(0, 'KAWESH');

    final newState = container.read(gameStateProvider).gameState;
    
    // Phase should not change (it waits for timer to redeal)
    expect(newState.phase, initialPhase);
    
    // Check system message
    final messages = container.read(gameStateProvider).messages;
    expect(messages.any((m) => m.text.contains('أعلن كوش! توزيع جديد...')), true);
  });

  test('KAWESH preserves dealerIndex (same dealer on kawesh)', () async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Set dealer index explicitly
    container.read(gameStateProvider.notifier).updateGameState((prev) {
      return prev.copyWith(
        phase: GamePhase.bidding,
        dealerIndex: 2,
        currentTurnIndex: 0,
        players: prev.players.map((p) => p.copyWith(isActive: true)).toList(),
      );
    });

    // Execute KAWESH
    container.read(biddingLogicProvider.notifier).handleBiddingAction(0, 'KAWESH');

    final state = container.read(gameStateProvider).gameState;
    expect(state.dealerIndex, 2);
  });

  test('canDeclareKawesh integration — hand with no court cards triggers kawesh eligibility', () {
     // Verify canDeclareKawesh logic as "integration" check
     final kaweshHand = [
        card(Rank.seven, Suit.spades),
        card(Rank.eight, Suit.hearts),
        card(Rank.nine, Suit.diamonds),
        card(Rank.seven, Suit.clubs),
        card(Rank.eight, Suit.spades),
      ];
      
      expect(canDeclareKawesh(kaweshHand), true);

      final normalHand = [
        card(Rank.ace, Suit.spades),
        card(Rank.eight, Suit.hearts),
      ];
      expect(canDeclareKawesh(normalHand), false);
  });
}
