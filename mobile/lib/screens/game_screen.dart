/// GameScreen — Main game board.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/theme/colors.dart';

class GameScreen extends StatelessWidget {
  const GameScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(color: AppColors.tableGreen),
        child: SafeArea(
          child: Stack(
            children: [
              // Table felt gradient
              const Positioned.fill(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: Alignment.center,
                      radius: 1.2,
                      colors: [
                        AppColors.tableGreenLight,
                        AppColors.tableGreen,
                        AppColors.tableGreenDark,
                      ],
                    ),
                  ),
                ),
              ),
              // Center placeholder
              Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.style_rounded, size: 64, color: AppColors.goldPrimary),
                    const SizedBox(height: 16),
                    Text(
                      'طاولة البلوت',
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.white),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Game Board — Coming in M-F4',
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.white70),
                    ),
                  ],
                ),
              ),
              // Back button
              Positioned(
                top: 8,
                left: 8,
                child: IconButton(
                  icon: const Icon(Icons.arrow_back, color: Colors.white),
                  onPressed: () => context.go('/lobby'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
