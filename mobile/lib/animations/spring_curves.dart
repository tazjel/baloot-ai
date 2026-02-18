/// spring_curves.dart — Framer Motion spring equivalents for Flutter.
///
/// Port of frontend CSS cubic-bezier curves and Framer Motion spring configs.
///
/// ## Spring Configs (from TypeScript)
/// - Card Play: stiffness 350, damping 25, mass 0.8
/// - Hand Fan: stiffness 200, damping 20
/// - Action Dock: stiffness 300, damping 30
/// - Toast: stiffness 400, damping 28
/// - Hint Overlay: stiffness 300, damping 25
/// - Dispute Modal: stiffness 400, damping 30
///
/// ## CSS Cubic-Bezier Curves
/// - Bounce overshoot: (0.34, 1.56, 0.64, 1)
/// - Ease-out fast: (0.25, 1, 0.5, 1)
/// - Smooth ease: (0.19, 1, 0.22, 1)
/// - Extreme bounce: (0.175, 0.885, 0.32, 1.275)
library;
import 'package:flutter/physics.dart';
import 'package:flutter/animation.dart';

// =============================================================================
// Spring Simulations (port of Framer Motion spring configs)
// =============================================================================

/// Create a SpringSimulation matching Framer Motion's spring physics.
///
/// Framer Motion uses stiffness + damping + mass (underdamped spring).
/// Flutter's [SpringDescription] also uses stiffness + damping + mass.
SpringSimulation createSpring({
  required double stiffness,
  required double damping,
  double mass = 1.0,
  double from = 0.0,
  double to = 1.0,
  double velocity = 0.0,
}) {
  final spring = SpringDescription(
    mass: mass,
    stiffness: stiffness,
    damping: damping,
  );
  return SpringSimulation(spring, from, to, velocity);
}

/// Card play trajectory spring (snappy, minimal bounce).
/// Framer: { stiffness: 350, damping: 25, mass: 0.8 }
SpringDescription get cardPlaySpring => const SpringDescription(
      mass: 0.8,
      stiffness: 350,
      damping: 25,
    );

/// Hand fan card entry spring (softer, staggered).
/// Framer: { stiffness: 200, damping: 20 }
SpringDescription get handFanSpring => const SpringDescription(
      mass: 1.0,
      stiffness: 200,
      damping: 20,
    );

/// Action dock entry spring (balanced).
/// Framer: { stiffness: 300, damping: 30 }
SpringDescription get dockSpring => const SpringDescription(
      mass: 1.0,
      stiffness: 300,
      damping: 30,
    );

/// Toast notification spring (stiff, quick settle).
/// Framer: { stiffness: 400, damping: 28 }
SpringDescription get toastSpring => const SpringDescription(
      mass: 1.0,
      stiffness: 400,
      damping: 28,
    );

/// Hint overlay spring (moderate).
/// Framer: { stiffness: 300, damping: 25 }
SpringDescription get hintSpring => const SpringDescription(
      mass: 1.0,
      stiffness: 300,
      damping: 25,
    );

/// Dispute modal spring (urgent, stiff).
/// Framer: { stiffness: 400, damping: 30 }
SpringDescription get disputeSpring => const SpringDescription(
      mass: 1.0,
      stiffness: 400,
      damping: 30,
    );

// =============================================================================
// CSS Cubic-Bezier Curves (as Flutter Curves)
// =============================================================================

/// Bouncy overshoot curve: cubic-bezier(0.34, 1.56, 0.64, 1)
/// Used for: throw-pop, floor-reveal, kaboot-burst
const Curve bounceOvershoot = Cubic(0.34, 1.56, 0.64, 1);

/// Fast deceleration curve: cubic-bezier(0.25, 1, 0.5, 1)
/// Used for: deal-fly, thump, throw-curve
const Curve fastDecelerate = Cubic(0.25, 1, 0.5, 1);

/// Smooth ease-in-out: cubic-bezier(0.19, 1, 0.22, 1)
/// Used for: card-deal, played-card-enter
const Curve smoothEase = Cubic(0.19, 1, 0.22, 1);

/// Extreme elastic bounce: cubic-bezier(0.175, 0.885, 0.32, 1.275)
/// Used for: bounce-in effects
const Curve extremeBounce = Cubic(0.175, 0.885, 0.32, 1.275);

// =============================================================================
// Animation Durations (matching CSS)
// =============================================================================

/// Card deal: deck to hand (0.5-0.6s)
const Duration dealDuration = Duration(milliseconds: 500);

/// Stagger delay per card in deal (50ms)
const Duration dealStaggerDelay = Duration(milliseconds: 50);

/// Card play: hand to table (~0.35-0.4s equivalent of spring)
const Duration playDuration = Duration(milliseconds: 350);

/// Trick sweep: table to winner (0.5s)
const Duration sweepDuration = Duration(milliseconds: 500);

/// Thump impact: scale 1.1 → 1.0 (0.2s)
const Duration thumpDuration = Duration(milliseconds: 200);

/// Floor card reveal (0.8s)
const Duration floorRevealDuration = Duration(milliseconds: 800);

/// Kaboot burst celebration (0.6s)
const Duration kabootBurstDuration = Duration(milliseconds: 600);

/// Score flash (0.4s)
const Duration scoreFlashDuration = Duration(milliseconds: 400);

/// Toast notification entry/exit (0.3s)
const Duration toastDuration = Duration(milliseconds: 300);

/// Speech bubble fade (0.3s)
const Duration speechFadeDuration = Duration(milliseconds: 300);

/// Hint pulse cycle (1.5s)
const Duration hintPulseDuration = Duration(milliseconds: 1500);

/// Trump shimmer cycle (2s)
const Duration trumpShimmerDuration = Duration(milliseconds: 2000);
