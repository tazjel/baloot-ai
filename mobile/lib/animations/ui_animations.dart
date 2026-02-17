/// ui_animations.dart — Toast, speech bubble, hint pulse, and turn indicator.
///
/// Port of frontend CSS keyframes for UI overlays.
///
/// ## Animations
/// - **ToastSlideIn**: Toast slides down from top with fade
/// - **SpeechBubbleFade**: Speech bubble fades in, holds, fades out
/// - **HintPulse**: Repeating glow pulse on hinted card
/// - **TurnIndicatorPulse**: Repeating scale pulse on active player
/// - **TrumpShimmer**: Repeating gold glow on trump-suit cards
/// - **ScoreFlash**: Brief scale + color flash on score change
/// - **KabootBurst**: Celebration scale burst
import 'package:flutter/material.dart';

import '../core/theme/colors.dart';
import 'spring_curves.dart';

// =============================================================================
// Toast Slide-In Animation
// =============================================================================

/// Slides a toast notification in from the top with spring physics.
class AnimatedToastEntry extends StatefulWidget {
  final Widget child;
  final Duration autoHideDuration;
  final VoidCallback? onDismiss;

  const AnimatedToastEntry({
    super.key,
    required this.child,
    this.autoHideDuration = const Duration(seconds: 3),
    this.onDismiss,
  });

  @override
  State<AnimatedToastEntry> createState() => _AnimatedToastEntryState();
}

class _AnimatedToastEntryState extends State<AnimatedToastEntry>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideOffset;
  late Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: toastDuration,
    );

    _slideOffset = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: fastDecelerate));

    _opacity = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );

    _controller.forward();

    // Auto-hide after delay
    Future.delayed(widget.autoHideDuration, () {
      if (mounted) {
        _controller.reverse().then((_) {
          widget.onDismiss?.call();
        });
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideOffset,
      child: FadeTransition(
        opacity: _opacity,
        child: widget.child,
      ),
    );
  }
}

// =============================================================================
// Speech Bubble Fade (show, hold 5s, fade out)
// =============================================================================

/// Fades a speech bubble in, holds for [holdDuration], then fades out.
class AnimatedSpeechBubble extends StatefulWidget {
  final Widget child;
  final Duration holdDuration;
  final VoidCallback? onComplete;

  const AnimatedSpeechBubble({
    super.key,
    required this.child,
    this.holdDuration = const Duration(seconds: 5),
    this.onComplete,
  });

  @override
  State<AnimatedSpeechBubble> createState() => _AnimatedSpeechBubbleState();
}

class _AnimatedSpeechBubbleState extends State<AnimatedSpeechBubble>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: speechFadeDuration,
    );

    // Fade in
    _controller.forward();

    // Hold, then fade out
    Future.delayed(widget.holdDuration, () {
      if (mounted) {
        _controller.reverse().then((_) {
          widget.onComplete?.call();
        });
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _controller,
      child: widget.child,
    );
  }
}

// =============================================================================
// Hint Card Pulse — Repeating glow
// =============================================================================

/// Repeating pulsing glow effect for AI-hinted cards.
///
/// Port of CSS `hintPulse` keyframes:
/// box-shadow oscillates between 8px and 20px amber glow.
class HintPulseEffect extends StatefulWidget {
  final Widget child;

  const HintPulseEffect({super.key, required this.child});

  @override
  State<HintPulseEffect> createState() => _HintPulseEffectState();
}

class _HintPulseEffectState extends State<HintPulseEffect>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: hintPulseDuration,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, child) {
        final t = _controller.value;
        return Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: AppColors.warning.withOpacity(0.5 + t * 0.4),
              width: 2,
            ),
            boxShadow: [
              BoxShadow(
                color: AppColors.warning.withOpacity(0.4 + t * 0.4),
                blurRadius: 8 + t * 12,
                spreadRadius: t * 4,
              ),
            ],
          ),
          child: child,
        );
      },
      child: widget.child,
    );
  }
}

// =============================================================================
// Trump Shimmer — Repeating gold glow on trump cards
// =============================================================================

/// Repeating gold shimmer effect for trump-suit cards.
///
/// Port of CSS `trumpShimmer` keyframes:
/// gold border + box-shadow oscillates every 2s.
class TrumpShimmerEffect extends StatefulWidget {
  final Widget child;

  const TrumpShimmerEffect({super.key, required this.child});

  @override
  State<TrumpShimmerEffect> createState() => _TrumpShimmerEffectState();
}

class _TrumpShimmerEffectState extends State<TrumpShimmerEffect>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: trumpShimmerDuration,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, child) {
        final t = _controller.value;
        return Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: AppColors.goldPrimary.withOpacity(0.5 + t * 0.3),
              width: 2,
            ),
            boxShadow: [
              BoxShadow(
                color: AppColors.goldPrimary.withOpacity(0.4 + t * 0.3),
                blurRadius: 8 + t * 8,
                spreadRadius: t * 2,
              ),
            ],
          ),
          child: child,
        );
      },
      child: widget.child,
    );
  }
}

// =============================================================================
// Turn Indicator Pulse — Repeating scale on active player
// =============================================================================

/// Repeating scale pulse on the active player's avatar.
class TurnIndicatorPulse extends StatefulWidget {
  final Widget child;

  const TurnIndicatorPulse({super.key, required this.child});

  @override
  State<TurnIndicatorPulse> createState() => _TurnIndicatorPulseState();
}

class _TurnIndicatorPulseState extends State<TurnIndicatorPulse>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    _scale = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: _scale,
      child: widget.child,
    );
  }
}

// =============================================================================
// Score Flash — Brief scale + color flash
// =============================================================================

/// Brief flash animation when score changes.
/// Scale: 1 → 1.4 → 1, color flash to gold.
class AnimatedScoreFlash extends StatefulWidget {
  final Widget child;
  final int score;

  const AnimatedScoreFlash({
    super.key,
    required this.child,
    required this.score,
  });

  @override
  State<AnimatedScoreFlash> createState() => _AnimatedScoreFlashState();
}

class _AnimatedScoreFlashState extends State<AnimatedScoreFlash>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scale;
  int _lastScore = 0;

  @override
  void initState() {
    super.initState();
    _lastScore = widget.score;
    _controller = AnimationController(
      vsync: this,
      duration: scoreFlashDuration,
    );

    _scale = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: 1.0, end: 1.4).chain(CurveTween(curve: Curves.easeOut)),
        weight: 30,
      ),
      TweenSequenceItem(
        tween: Tween(begin: 1.4, end: 1.0).chain(CurveTween(curve: Curves.easeIn)),
        weight: 70,
      ),
    ]).animate(_controller);
  }

  @override
  void didUpdateWidget(AnimatedScoreFlash oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.score != _lastScore) {
      _lastScore = widget.score;
      _controller.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: _scale,
      child: widget.child,
    );
  }
}

// =============================================================================
// Kaboot Burst — Celebration scale explosion
// =============================================================================

/// Scale burst effect for kaboot (sweep) celebrations.
/// Scale: 0 → 1.3 → 1.0 with bounce overshoot.
class AnimatedKabootBurst extends StatefulWidget {
  final Widget child;
  final VoidCallback? onComplete;

  const AnimatedKabootBurst({
    super.key,
    required this.child,
    this.onComplete,
  });

  @override
  State<AnimatedKabootBurst> createState() => _AnimatedKabootBurstState();
}

class _AnimatedKabootBurstState extends State<AnimatedKabootBurst>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scale;
  late Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: kabootBurstDuration,
    );

    _scale = Tween<double>(begin: 0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: bounceOvershoot),
    );

    _opacity = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0, 0.5, curve: Curves.easeOut),
      ),
    );

    _controller.forward().then((_) {
      widget.onComplete?.call();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: _scale,
      child: FadeTransition(
        opacity: _opacity,
        child: widget.child,
      ),
    );
  }
}
