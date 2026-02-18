/// card_animations.dart — Card deal, play, and sweep animations.
///
/// Port of frontend CSS keyframes and animationUtils.ts trajectory calculations.
///
/// ## Animations
/// - **Deal**: 8 cards stagger from deck center to hand fan positions
/// - **Play**: Card flies from hand position to table center (curved path)
/// - **Sweep**: 4 table cards slide toward winner's position
/// - **Thump**: Scale bump on card landing (1.1 → 1.0)
/// - **FloorReveal**: Floor card appears with scale + rotation
///
/// ## Usage
/// Wrap a [CardWidget] with [AnimatedCardDeal] or [AnimatedCardPlay]
/// to apply the animation. The parent widget controls when to trigger.
library;
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../models/enums.dart';
import 'spring_curves.dart';

// =============================================================================
// Deal Animation — Cards fly from deck to hand
// =============================================================================

/// Animates a card dealing from center deck position into the hand.
///
/// Each card has a [staggerIndex] (0–7) that delays its entrance,
/// creating a cascading deal effect.
class AnimatedCardDeal extends StatefulWidget {
  final Widget child;
  final int staggerIndex;
  final VoidCallback? onComplete;

  const AnimatedCardDeal({
    super.key,
    required this.child,
    this.staggerIndex = 0,
    this.onComplete,
  });

  @override
  State<AnimatedCardDeal> createState() => _AnimatedCardDealState();
}

class _AnimatedCardDealState extends State<AnimatedCardDeal>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _slideY;
  late Animation<double> _opacity;
  late Animation<double> _scale;
  late Animation<double> _rotation;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: dealDuration,
    );

    // Apply smooth ease curve
    final curved = CurvedAnimation(parent: _controller, curve: smoothEase);

    // Cards fly in from above (translateY: -45vh equivalent)
    _slideY = Tween<double>(begin: -300, end: 0).animate(curved);

    // Fade in
    _opacity = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0, 0.6, curve: Curves.easeOut),
      ),
    );

    // Scale from small to full
    _scale = Tween<double>(begin: 0.2, end: 1).animate(curved);

    // Rotate from 180° to 0° (card flip effect)
    _rotation = Tween<double>(begin: math.pi, end: 0).animate(curved);

    // Start with stagger delay
    Future.delayed(
      Duration(milliseconds: widget.staggerIndex * dealStaggerDelay.inMilliseconds),
      () {
        if (mounted) {
          _controller.forward().then((_) {
            widget.onComplete?.call();
          });
        }
      },
    );
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
        return Transform.translate(
          offset: Offset(0, _slideY.value),
          child: Transform.scale(
            scale: _scale.value,
            child: Transform.rotate(
              angle: _rotation.value,
              child: Opacity(
                opacity: _opacity.value,
                child: child,
              ),
            ),
          ),
        );
      },
      child: widget.child,
    );
  }
}

// =============================================================================
// Card Play Animation — Hand to table center
// =============================================================================

/// Animates a card playing from a hand position to the table center.
///
/// The [fromPosition] determines the starting position and trajectory
/// (Bottom → up, Right → left, Top → down, Left → right).
class AnimatedCardPlay extends StatefulWidget {
  final Widget child;
  final PlayerPosition fromPosition;
  final VoidCallback? onComplete;

  const AnimatedCardPlay({
    super.key,
    required this.child,
    required this.fromPosition,
    this.onComplete,
  });

  @override
  State<AnimatedCardPlay> createState() => _AnimatedCardPlayState();
}

class _AnimatedCardPlayState extends State<AnimatedCardPlay>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _position;
  late Animation<double> _scale;
  late Animation<double> _opacity;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: playDuration,
    );

    // Spring-like curve (matches Framer stiffness: 350, damping: 25)
    final curved = CurvedAnimation(parent: _controller, curve: fastDecelerate);

    // Calculate initial offset based on which player played
    final initialOffset = _getInitialOffset(widget.fromPosition);

    _position = Tween<Offset>(
      begin: initialOffset,
      end: Offset.zero,
    ).animate(curved);

    _scale = Tween<double>(begin: 0.8, end: 1.0).animate(curved);

    _opacity = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0, 0.4, curve: Curves.easeOut),
      ),
    );

    _controller.forward().then((_) {
      widget.onComplete?.call();
    });
  }

  Offset _getInitialOffset(PlayerPosition position) {
    const range = 300.0;
    switch (position) {
      case PlayerPosition.bottom:
        return const Offset(0, range); // From below
      case PlayerPosition.top:
        return const Offset(0, -range); // From above
      case PlayerPosition.left:
        return const Offset(-range, 0); // From left
      case PlayerPosition.right:
        return const Offset(range, 0); // From right
    }
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
        return Transform.translate(
          offset: _position.value,
          child: Transform.scale(
            scale: _scale.value,
            child: Opacity(
              opacity: _opacity.value,
              child: child,
            ),
          ),
        );
      },
      child: widget.child,
    );
  }
}

// =============================================================================
// Trick Sweep Animation — Table cards slide to winner
// =============================================================================

/// Animates a played card sweeping off the table toward the winning player.
///
/// The [toPosition] determines the exit direction
/// (the winning player's position on screen).
class AnimatedTrickSweep extends StatefulWidget {
  final Widget child;
  final PlayerPosition toPosition;
  final VoidCallback? onComplete;

  const AnimatedTrickSweep({
    super.key,
    required this.child,
    required this.toPosition,
    this.onComplete,
  });

  @override
  State<AnimatedTrickSweep> createState() => _AnimatedTrickSweepState();
}

class _AnimatedTrickSweepState extends State<AnimatedTrickSweep>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _position;
  late Animation<double> _scale;
  late Animation<double> _opacity;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: sweepDuration,
    );

    final curved = CurvedAnimation(parent: _controller, curve: Curves.easeIn);

    final targetOffset = _getSweepTarget(widget.toPosition);

    _position = Tween<Offset>(
      begin: Offset.zero,
      end: targetOffset,
    ).animate(curved);

    _scale = Tween<double>(begin: 1.0, end: 0.0).animate(curved);

    _opacity = Tween<double>(begin: 1, end: 0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.5, 1.0, curve: Curves.easeIn),
      ),
    );

    _controller.forward().then((_) {
      widget.onComplete?.call();
    });
  }

  Offset _getSweepTarget(PlayerPosition position) {
    // Matches CSS: sweepToTop translateY(-40vh), etc.
    const range = 400.0;
    switch (position) {
      case PlayerPosition.bottom:
        return const Offset(0, range);
      case PlayerPosition.top:
        return const Offset(0, -range);
      case PlayerPosition.left:
        return const Offset(-range, 0);
      case PlayerPosition.right:
        return const Offset(range, 0);
    }
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
        return Transform.translate(
          offset: _position.value,
          child: Transform.scale(
            scale: _scale.value,
            child: Opacity(
              opacity: _opacity.value,
              child: child,
            ),
          ),
        );
      },
      child: widget.child,
    );
  }
}

// =============================================================================
// Thump Animation — Card landing impact
// =============================================================================

/// Brief scale bump when a card lands on the table (1.1 → 1.0).
class AnimatedThump extends StatefulWidget {
  final Widget child;

  const AnimatedThump({super.key, required this.child});

  @override
  State<AnimatedThump> createState() => _AnimatedThumpState();
}

class _AnimatedThumpState extends State<AnimatedThump>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: thumpDuration,
    );

    _scale = Tween<double>(begin: 1.1, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: fastDecelerate),
    );

    _controller.forward();
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
// Floor Card Reveal — Scale + rotation + glow
// =============================================================================

/// Animates the floor card appearing with scale-up, rotation, and gold glow.
class AnimatedFloorReveal extends StatefulWidget {
  final Widget child;

  const AnimatedFloorReveal({super.key, required this.child});

  @override
  State<AnimatedFloorReveal> createState() => _AnimatedFloorRevealState();
}

class _AnimatedFloorRevealState extends State<AnimatedFloorReveal>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scale;
  late Animation<double> _rotation;
  late Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: floorRevealDuration,
    );

    final curved = CurvedAnimation(parent: _controller, curve: bounceOvershoot);

    // Scale: 0.5 → 1.2 → 1.0 (overshoot curve handles the peak)
    _scale = Tween<double>(begin: 0.5, end: 1.0).animate(curved);

    // Rotation: 180° → 0° (flip reveal)
    _rotation = Tween<double>(begin: math.pi, end: 0).animate(
      CurvedAnimation(parent: _controller, curve: smoothEase),
    );

    // Fade in
    _opacity = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0, 0.5, curve: Curves.easeOut),
      ),
    );

    _controller.forward();
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
        return Transform.scale(
          scale: _scale.value,
          child: Transform(
            alignment: Alignment.center,
            transform: Matrix4.identity()
              ..setEntry(3, 2, 0.001) // perspective
              ..rotateY(_rotation.value), // 3D Y-axis flip
            child: Opacity(
              opacity: _opacity.value,
              child: child,
            ),
          ),
        );
      },
      child: widget.child,
    );
  }
}
