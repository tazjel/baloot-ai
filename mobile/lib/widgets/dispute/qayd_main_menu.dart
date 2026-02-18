/// qayd_main_menu.dart — Main menu for Qayd dispute type selection.
///
/// Port of frontend/src/components/dispute/QaydMainMenu.tsx
///
/// Shows 3 accusation type buttons when the local player is the reporter,
/// or a "checking..." message when another player initiated the dispute.
library;
import 'package:flutter/material.dart';

import 'qayd_types.dart';

class QaydMainMenu extends StatelessWidget {
  final bool isReporter;
  final String reporterName;
  final void Function(MainMenuOption) onMenuSelect;

  const QaydMainMenu({
    super.key,
    required this.isReporter,
    required this.reporterName,
    required this.onMenuSelect,
  });

  @override
  Widget build(BuildContext context) {
    if (!isReporter) {
      return _buildWaiting();
    }
    return _buildMenu();
  }

  Widget _buildWaiting() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.shield, size: 56, color: Color(0xFFFBBF24)),
          const SizedBox(height: 16),
          const Text(
            'جاري التحقق...',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          RichText(
            text: TextSpan(
              style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 14),
              children: [
                const TextSpan(text: 'يقوم '),
                TextSpan(
                  text: reporterName,
                  style: const TextStyle(
                    color: Color(0xFFFBBF24),
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const TextSpan(text: ' بمراجعة اللعب'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMenu() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'ماذا تريد أن تفعل؟',
            style: TextStyle(color: Color(0xFFD1D5DB), fontSize: 18),
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 16,
            runSpacing: 12,
            alignment: WrapAlignment.center,
            children: mainMenuOptions
                .map((opt) => _MenuButton(
                      option: opt,
                      onTap: () => onMenuSelect(opt.key),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _MenuButton extends StatelessWidget {
  final MenuOptionData option;
  final VoidCallback onTap;

  const _MenuButton({required this.option, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          constraints: const BoxConstraints(minWidth: 120),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.1)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(option.icon, style: const TextStyle(fontSize: 28)),
              const SizedBox(height: 10),
              Text(
                option.ar,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
