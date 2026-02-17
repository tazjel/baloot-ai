/// MultiplayerScreen — Room creation and joining.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/theme/colors.dart';

class MultiplayerScreen extends StatelessWidget {
  const MultiplayerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('لعب جماعي'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/lobby'),
        ),
      ),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.people_rounded, size: 64, color: AppColors.goldPrimary),
            SizedBox(height: 16),
            Text('قريباً...', style: TextStyle(fontSize: 24, color: AppColors.textMuted)),
            Text('Multiplayer coming soon', style: TextStyle(fontSize: 16, color: AppColors.textMuted)),
          ],
        ),
      ),
    );
  }
}
