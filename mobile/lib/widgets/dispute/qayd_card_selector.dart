/// qayd_card_selector.dart — Trick browser with card picker for Qayd disputes.
///
/// Port of frontend/src/components/dispute/QaydCardSelector.tsx
///
/// Displays all tricks from the current round in a scrollable list.
/// Cards can be tapped to select as crime (pink ring) or proof (green ring).
library;
import 'package:flutter/material.dart';

import '../../models/card_model.dart';
import '../../models/enums.dart';
import '../../models/game_state.dart';
import '../../models/player.dart';
import '../card_widget.dart';
import 'qayd_types.dart';

class QaydCardSelector extends StatelessWidget {
  final QaydStep step;
  final List<TrickRecord> tricks;
  final CardSelection? crimeCard;
  final CardSelection? proofCard;
  final List<ViolationData> violations;
  final ViolationType? violation;
  final List<Player> players;
  final void Function(CardModel card, int trickIdx, int cardIdx, String playedBy)
      onCardClick;
  final void Function(ViolationType v) onViolationSelect;

  const QaydCardSelector({
    super.key,
    required this.step,
    required this.tricks,
    required this.crimeCard,
    required this.proofCard,
    required this.violations,
    required this.violation,
    required this.players,
    required this.onCardClick,
    required this.onViolationSelect,
  });

  @override
  Widget build(BuildContext context) {
    final isCrimeStep = step == QaydStep.selectCard1;
    final instructionText = isCrimeStep
        ? 'اختر الورقة التي تم الغش بها'
        : 'ابحث عن الورقة التي كشفت الغش';
    final instructionColor = isCrimeStep ? qaydCrimeColor : qaydProofColor;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Violation filter bar
        _buildViolationBar(),

        // Instruction text
        Container(
          color: qaydBgDarker,
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
          child: Text(
            instructionText,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: instructionColor,
              fontSize: 15,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),

        // Trick list
        Expanded(
          child: tricks.isEmpty
              ? const Center(
                  child: Text(
                    'لا توجد أكلات للمراجعة',
                    style: TextStyle(color: Color(0xFF6B7280), fontSize: 14),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: tricks.length,
                  itemBuilder: (context, trickIdx) =>
                      _buildTrickCard(trickIdx),
                ),
        ),
      ],
    );
  }

  Widget _buildViolationBar() {
    return Container(
      color: qaydBgDark,
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: qaydBorder)),
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 6,
        alignment: WrapAlignment.center,
        children: violations.map((v) {
          final isSelected = violation == v.key;
          return GestureDetector(
            onTap: () => onViolationSelect(v.key),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isSelected
                    ? const Color(0xFFE0E0E0)
                    : const Color(0xFF555555),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                v.ar,
                style: TextStyle(
                  color: isSelected ? Colors.black : const Color(0xFFD1D5DB),
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildTrickCard(int trickIdx) {
    final trick = tricks[trickIdx];
    final cards = trick.cards;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: qaydBgDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: qaydBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Trick header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: qaydBorder)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  trick.winner != null ? 'Winner: ${trick.winner}' : 'In Progress',
                  style: const TextStyle(color: Color(0xFF6B7280), fontSize: 11),
                ),
                Text(
                  'الأكلة ${trickIdx + 1}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),

          // Cards row
          Padding(
            padding: const EdgeInsets.all(12),
            child: Wrap(
              spacing: 12,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: List.generate(cards.length, (cardIdx) {
                final cardData = cards[cardIdx];
                final card = _parseCard(cardData);
                if (card == null) return const SizedBox.shrink();

                final playedBy = _getPlayedBy(trick, cardData, cardIdx);
                final isCrime = crimeCard?.trickIdx == trickIdx &&
                    crimeCard?.cardIdx == cardIdx;
                final isProof = proofCard?.trickIdx == trickIdx &&
                    proofCard?.cardIdx == cardIdx;

                return _buildSelectableCard(
                  card: card,
                  trickIdx: trickIdx,
                  cardIdx: cardIdx,
                  playedBy: playedBy,
                  isCrime: isCrime,
                  isProof: isProof,
                );
              }),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSelectableCard({
    required CardModel card,
    required int trickIdx,
    required int cardIdx,
    required String playedBy,
    required bool isCrime,
    required bool isProof,
  }) {
    Color? ringColor;
    String? badgeText;
    Color? badgeColor;

    if (isCrime) {
      ringColor = qaydCrimeColor;
      badgeText = 'الجريمة';
      badgeColor = const Color(0xFFDB2777); // Pink-600
    } else if (isProof) {
      ringColor = qaydProofColor;
      badgeText = 'الدليل';
      badgeColor = const Color(0xFF16A34A); // Green-600
    }

    final playerName = _findPlayerName(playedBy);

    return GestureDetector(
      onTap: () => onCardClick(card, trickIdx, cardIdx, playedBy),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Stack(
            clipBehavior: Clip.none,
            children: [
              Container(
                padding: EdgeInsets.all(ringColor != null ? 3 : 0),
                decoration: ringColor != null
                    ? BoxDecoration(
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: ringColor, width: 3),
                      )
                    : null,
                child: CardWidget(card: card, width: 56),
              ),
              if (badgeText != null)
                Positioned(
                  top: -8,
                  right: -8,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 5,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: badgeColor,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      badgeText,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 8,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            playerName,
            style: const TextStyle(color: Color(0xFF6B7280), fontSize: 9),
          ),
        ],
      ),
    );
  }

  CardModel? _parseCard(dynamic cardData) {
    if (cardData == null) return null;
    if (cardData is Map<String, dynamic>) {
      if (cardData.containsKey('card') && cardData['card'] is Map<String, dynamic>) {
        return CardModel.fromJson(cardData['card'] as Map<String, dynamic>);
      }
      return CardModel.fromJson(cardData);
    }
    return null;
  }

  String _getPlayedBy(TrickRecord trick, dynamic cardData, int cardIdx) {
    if (cardData is Map<String, dynamic> && cardData.containsKey('playedBy')) {
      return cardData['playedBy'] as String? ?? '';
    }
    if (trick.playedBy != null && cardIdx < trick.playedBy!.length) {
      return trick.playedBy![cardIdx];
    }
    return '';
  }

  String _findPlayerName(String playedBy) {
    if (playedBy.isEmpty) return '';
    for (final p in players) {
      if (p.position.value == playedBy || p.name == playedBy) {
        return p.name;
      }
    }
    return playedBy;
  }
}
