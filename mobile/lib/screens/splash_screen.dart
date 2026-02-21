/// splash_screen.dart — Animated splash screen on app launch.
///
/// Shows the Baloot AI logo with a gold shimmer animation,
/// then auto-navigates to the lobby after a brief delay.
/// Also pre-loads settings so the lobby opens instantly.
library;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/colors.dart';
import '../state/providers.dart';

/// Animated splash screen shown on app launch.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeIn;
  late final Animation<double> _scale;
  late final Animation<double> _shimmer;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    );

    _fadeIn = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
    );

    _scale = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.0, 0.6, curve: Curves.easeOutBack),
      ),
    );

    _shimmer = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.4, 1.0, curve: Curves.easeInOut),
    );

    _controller.forward();

    // Defer auth init to avoid modifying providers during build
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initAndNavigate();
    });
  }

  Future<void> _initAndNavigate() async {
    // Start auth initialization in parallel with animation
    final authInit = ref.read(authProvider.notifier).initialize();

    // Wait for both animation delay and auth init
    await Future.wait([
      authInit,
      Future.delayed(const Duration(milliseconds: 2400)),
    ]);

    if (!mounted) return;

    final auth = ref.read(authProvider);
    if (auth.isAuthenticated) {
      context.go('/lobby');
    } else {
      context.go('/login');
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.center,
            radius: 1.2,
            colors: [
              Color(0xFF1C1917), // darkSurface
              Color(0xFF0D0907), // darkBg
              Color(0xFF000000),
            ],
          ),
        ),
        child: Center(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              return FadeTransition(
                opacity: _fadeIn,
                child: ScaleTransition(
                  scale: _scale,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Logo icon with gold glow
                      Container(
                        width: 120,
                        height: 120,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              AppColors.goldLight,
                              AppColors.goldPrimary,
                              AppColors.goldDark,
                            ],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.goldPrimary
                                  .withOpacity(0.3 + _shimmer.value * 0.3),
                              blurRadius: 24 + _shimmer.value * 16,
                              spreadRadius: 4 + _shimmer.value * 8,
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.style_rounded, // Card stack icon
                          size: 60,
                          color: Colors.white,
                        ),
                      ),

                      const SizedBox(height: 32),

                      // Title
                      ShaderMask(
                        shaderCallback: (bounds) {
                          return LinearGradient(
                            colors: const [
                              AppColors.goldDark,
                              AppColors.goldLight,
                              AppColors.goldPrimary,
                            ],
                            stops: [
                              (_shimmer.value - 0.3).clamp(0.0, 1.0),
                              _shimmer.value.clamp(0.0, 1.0),
                              (_shimmer.value + 0.3).clamp(0.0, 1.0),
                            ],
                          ).createShader(bounds);
                        },
                        child: const Text(
                          'بلوت AI',
                          style: TextStyle(
                            fontSize: 42,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),

                      const SizedBox(height: 8),

                      // Subtitle
                      FadeTransition(
                        opacity: _shimmer,
                        child: const Text(
                          'Baloot AI',
                          style: TextStyle(
                            fontSize: 16,
                            color: AppColors.textMuted,
                            letterSpacing: 4,
                          ),
                        ),
                      ),

                      const SizedBox(height: 48),

                      // Loading dots
                      FadeTransition(
                        opacity: _shimmer,
                        child: const SizedBox(
                          width: 32,
                          height: 32,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: AppColors.goldPrimary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
