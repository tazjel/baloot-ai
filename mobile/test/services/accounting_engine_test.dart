import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/services/accounting_engine.dart';
import 'package:baloot_ai/models/enums.dart';

void main() {
  group('AccountingEngine — SUN Conversion', () {
    test('sunCardGP: floor-to-even rounding', () {
      // q odd + remainder > 0 → round up
      expect(AccountingEngine.sunCardGP(67), 14); // 13 r 2, odd → 14
      expect(AccountingEngine.sunCardGP(63), 12); // 12 r 3, even → 12
      // Edge cases
      expect(AccountingEngine.sunCardGP(0), 0);
      expect(AccountingEngine.sunCardGP(5), 1); // 1 r 0, no remainder
      expect(AccountingEngine.sunCardGP(130), 26); // Full pool
    });

    test('sunCardGP: pairs always sum to 26', () {
      // Test several complementary pairs that sum to 130
      final pairs = [
        [65, 65],
        [70, 60],
        [80, 50],
        [90, 40],
        [100, 30],
        [110, 20],
        [120, 10],
        [130, 0],
        [67, 63],
        [73, 57],
      ];
      for (final pair in pairs) {
        final gpA = AccountingEngine.sunCardGP(pair[0]);
        final gpB = AccountingEngine.sunCardGP(pair[1]);
        expect(gpA + gpB, 26,
            reason: 'SUN ${pair[0]}+${pair[1]} should sum to 26, got $gpA+$gpB');
      }
    });
  });

  group('AccountingEngine — HOKUM Conversion', () {
    test('hokumCardGP: individual rounding (r > 5 rounds up)', () {
      expect(AccountingEngine.hokumCardGP(85), 8); // 8 r 5 → 8 (r=5 is NOT > 5)
      expect(AccountingEngine.hokumCardGP(86), 9); // 8 r 6 → 9
      expect(AccountingEngine.hokumCardGP(80), 8); // 8 r 0 → 8
      expect(AccountingEngine.hokumCardGP(0), 0);
      expect(AccountingEngine.hokumCardGP(162), 16); // Full pool
    });

    test('hokumPairGP: pairs always sum to 16', () {
      final pairs = [
        [81, 81],
        [90, 72],
        [100, 62],
        [110, 52],
        [120, 42],
        [130, 32],
        [150, 12],
        [162, 0],
        [85, 77],
        [96, 66],
      ];
      for (final pair in pairs) {
        final result = AccountingEngine.hokumPairGP(pair[0], pair[1]);
        expect(result[0] + result[1], 16,
            reason:
                'HOKUM ${pair[0]}+${pair[1]} should sum to 16, got ${result[0]}+${result[1]}');
      }
    });

    test('hokumPairGP: sum=17 reduces larger remainder side', () {
      // Both individually round up, but sum exceeds 16
      final result = AccountingEngine.hokumPairGP(86, 76);
      expect(result[0] + result[1], 16);
    });

    test('hokumPairGP: sum=15 increases larger remainder side', () {
      // Both individually round down, but sum below 16
      final result = AccountingEngine.hokumPairGP(85, 77);
      expect(result[0] + result[1], 16);
    });
  });

  group('AccountingEngine — Kaboot (Capot)', () {
    test('SUN kaboot: winner gets 44, loser gets 0', () {
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 130,
        themRaw: 0,
        usProjects: 0,
        themProjects: 0,
        bidType: 'SUN',
        doublingLevel: DoublingLevel.normal,
        bidderTeam: 'us',
      );
      expect(result.us.gamePoints, 44);
      expect(result.them.gamePoints, 0);
      expect(result.us.isKaboot, true);
      expect(result.winner, 'us');
    });

    test('HOKUM kaboot: winner gets 25, loser gets 0', () {
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 0,
        themRaw: 162,
        usProjects: 0,
        themProjects: 0,
        bidType: 'HOKUM',
        doublingLevel: DoublingLevel.normal,
        bidderTeam: 'them',
      );
      expect(result.them.gamePoints, 25);
      expect(result.us.gamePoints, 0);
      expect(result.them.isKaboot, true);
      expect(result.winner, 'them');
    });
  });

  group('AccountingEngine — Khasara (Buyer Loss)', () {
    test('bidder GP < opponent GP → khasara', () {
      // Us bid SUN, scored less
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 40,
        themRaw: 90,
        usProjects: 0,
        themProjects: 0,
        bidType: 'SUN',
        doublingLevel: DoublingLevel.normal,
        bidderTeam: 'us',
      );
      // Us scored 8 GP, Them scored 18 GP → khasara → them get 26
      expect(result.us.gamePoints, 0);
      expect(result.them.gamePoints, 26);
      expect(result.winner, 'them');
    });

    test('GP tie with bidder raw < opp raw → khasara', () {
      // Carefully picked so GP are equal but raw abnat differ
      // SUN: 33 → 6 r 3, even → 6 GP. 97 → 19 r 2, odd → 20. No, sum != 26
      // Let's use HOKUM with projects to create a tie
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 80,
        themRaw: 82,
        usProjects: 0,
        themProjects: 0,
        bidType: 'HOKUM',
        doublingLevel: DoublingLevel.normal,
        bidderTeam: 'us',
      );
      // HOKUM pair: 80→8, 82→8+1=9? No: 80/10=8r0→8, 82/10=8r2→8. Sum=16. OK.
      // Wait: 80+82=162, pair should sum to 16
      // 80: q=8,r=0→8. 82: q=8,r=2→8. Sum=16. ✓
      // Us GP=8, Them GP=8 → tie → compare raw: 80 < 82 → khasara
      expect(result.us.gamePoints, 0);
      expect(result.them.gamePoints, 16);
    });

    test('GP tie, doubled → doubler always loses', () {
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 81,
        themRaw: 81,
        usProjects: 0,
        themProjects: 0,
        bidType: 'HOKUM',
        doublingLevel: DoublingLevel.double_,
        bidderTeam: 'us',
      );
      // 81: q=8,r=1→8 each. Sum=16. ✓
      // Tie + doubled → bidder (us) loses
      // Khasara: them get 16 base. Then doubling: 16*2=32 to them
      expect(result.us.gamePoints, 0);
      expect(result.them.gamePoints, 32);
    });

    test('GP tie, equal raw → split (no khasara)', () {
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 81,
        themRaw: 81,
        usProjects: 0,
        themProjects: 0,
        bidType: 'HOKUM',
        doublingLevel: DoublingLevel.normal,
        bidderTeam: 'us',
      );
      // 81→8 each, sum=16. ✓. Raw equal → no khasara → split
      expect(result.us.gamePoints, 8);
      expect(result.them.gamePoints, 8);
    });
  });

  group('AccountingEngine — Baloot Bonus', () {
    test('baloot adds flat 2 GP, never multiplied', () {
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 90,
        themRaw: 40,
        usProjects: 0,
        themProjects: 0,
        bidType: 'SUN',
        doublingLevel: DoublingLevel.normal,
        bidderTeam: 'us',
        hasBalootUs: true,
      );
      // 90→18, 40→8. Us wins. +2 baloot = 20
      expect(result.us.gamePoints, 20);
      expect(result.them.gamePoints, 8);
    });

    test('baloot survives khasara for winning team', () {
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 40,
        themRaw: 90,
        usProjects: 0,
        themProjects: 0,
        bidType: 'SUN',
        doublingLevel: DoublingLevel.normal,
        bidderTeam: 'us',
        hasBalootThem: true,
      );
      // Us bid, scored 8 GP < 18 GP → khasara → them get 26 + 2 baloot = 28
      expect(result.them.gamePoints, 28);
      expect(result.us.gamePoints, 0);
    });

    test('baloot not multiplied even when doubled', () {
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 100,
        themRaw: 62,
        usProjects: 0,
        themProjects: 0,
        bidType: 'HOKUM',
        doublingLevel: DoublingLevel.double_,
        bidderTeam: 'us',
        hasBalootUs: true,
      );
      // HOKUM pair: 100→10, 62→6. Sum=16. ✓
      // Us wins. Doubled: total=16, us gets 16*2=32. Then +2 baloot = 34.
      expect(result.us.gamePoints, 34);
      expect(result.them.gamePoints, 0);
    });
  });

  group('AccountingEngine — Doubling', () {
    test('double multiplier: winner takes all × 2', () {
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 100,
        themRaw: 62,
        usProjects: 0,
        themProjects: 0,
        bidType: 'HOKUM',
        doublingLevel: DoublingLevel.double_,
        bidderTeam: 'us',
      );
      // HOKUM pair: 100→10, 62→6. Sum=16.
      // Us wins: total=16, doubled=16*2=32
      expect(result.us.gamePoints, 32);
      expect(result.them.gamePoints, 0);
    });
  });

  group('AccountingEngine — Project Abnat Values', () {
    test('SUN project values', () {
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.fourHundred, 'SUN'), 40);
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.hundred, 'SUN'), 20);
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.fifty, 'SUN'), 10);
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.sira, 'SUN'), 4);
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.baloot, 'SUN'), 0);
    });

    test('HOKUM project values', () {
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.fourHundred, 'HOKUM'), 0);
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.hundred, 'HOKUM'), 10);
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.fifty, 'HOKUM'), 5);
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.sira, 'HOKUM'), 2);
      expect(AccountingEngine.getProjectAbnatValue(ProjectType.baloot, 'HOKUM'), 0);
    });
  });

  group('AccountingEngine — Projects in Scoring', () {
    test('projects add to total raw before conversion', () {
      // SUN: usRaw=60 + usProjects=20 = 80 total
      //       themRaw=70 + themProjects=0 = 70 total
      final result = AccountingEngine.calculateRoundResult(
        usRaw: 60,
        themRaw: 70,
        usProjects: 20,
        themProjects: 0,
        bidType: 'SUN',
        doublingLevel: DoublingLevel.normal,
        bidderTeam: 'us',
      );
      // SUN: 80→16, 70 (wait: 60+70=130, projects add on top)
      // Us totalRaw=80, them totalRaw=70. 80+70=150 (not 130, projects add)
      // sunCardGP(80) = 80/5=16 r 0 → 16 (even, no round)
      // sunCardGP(70) = 70/5=14 r 0 → 14
      // Us: 16, them: 14 → us wins
      expect(result.us.gamePoints, 16);
      expect(result.them.gamePoints, 14);
    });
  });

  group('AccountingEngine — Explain Calculation', () {
    test('returns step-by-step explanation for SUN', () {
      final steps = AccountingEngine.explainCalculation(
        usRaw: 70,
        themRaw: 60,
        bidType: 'SUN',
        bidderTeam: 'us',
      );
      expect(steps.length, greaterThan(3));
      expect(steps[0], contains('SUN'));
      expect(steps.any((s) => s.contains('Us:')), true);
    });

    test('returns step-by-step explanation for HOKUM', () {
      final steps = AccountingEngine.explainCalculation(
        usRaw: 100,
        themRaw: 62,
        bidType: 'HOKUM',
        bidderTeam: 'them',
      );
      expect(steps.length, greaterThan(3));
      expect(steps[0], contains('HOKUM'));
    });
  });
}
