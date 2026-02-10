import { describe, it, expect } from 'vitest';
import { AccountingEngine } from './AccountingEngine';
import { DoublingLevel, ProjectType } from '../types';

describe('AccountingEngine', () => {

    // ═══════════════════════════════════════════════════════════
    // SUN Scoring
    // ═══════════════════════════════════════════════════════════
    describe('SUN scoring', () => {
        it('should convert abnat to game points using (abnat × 2) / 10', () => {
            // 65 abnat → (65*2)/10 = 13 game points each
            const result = AccountingEngine.calculateRoundResult(
                65, 65, 0, 0, 'SUN', 1 as DoublingLevel, null
            );
            expect(result.us.gamePoints).toBe(13);
            expect(result.them.gamePoints).toBe(13);
        });

        it('should handle normal SUN round with bidder winning', () => {
            // Us bid SUN, scored 80 abnat (80*2/10=16 > 13 → win)
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 0, 'SUN', 1 as DoublingLevel, 'us'
            );
            expect(result.us.gamePoints).toBe(16);
            expect(result.them.gamePoints).toBe(10);
            expect(result.winner).toBe('us');
        });

        it('should handle odd abnat creating .X in SUN', () => {
            // 43 abnat → (43*2)/10 = 8.6
            const result = AccountingEngine.calculateRoundResult(
                43, 87, 0, 0, 'SUN', 1 as DoublingLevel, 'us'
            );
            // 43*2/10 = 8.6, 87*2/10 = 17.4
            // bidder(us) scored 8.6 ≤ 13 → Khasara
            expect(result.us.gamePoints).toBe(0);
            expect(result.them.gamePoints).toBe(26);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // HOKUM Scoring
    // ═══════════════════════════════════════════════════════════
    describe('HOKUM scoring', () => {
        it('should round 0.5 DOWN in HOKUM conversion', () => {
            // 85 abnat → 85/10 = 8.5 → floors to 8
            // 77 abnat → 77/10 = 7.7 → ceil to 8
            // Sum = 16 = maxPoints → exact fit
            const result = AccountingEngine.calculateRoundResult(
                85, 77, 0, 0, 'HOKUM', 1 as DoublingLevel, null
            );
            expect(result.us.gamePoints).toBe(8);
            expect(result.them.gamePoints).toBe(8);
        });

        it('should handle sum > maxPoints by capping loser', () => {
            // 86/10=8.6→9, 76/10=7.6→8. Sum=17>16. Winner(us, 9>8) keeps 9, them=16-9=7
            const result = AccountingEngine.calculateRoundResult(
                86, 76, 0, 0, 'HOKUM', 1 as DoublingLevel, null
            );
            expect(result.us.gamePoints).toBe(9);
            expect(result.them.gamePoints).toBe(7);
        });

        it('should handle sum < maxPoints by adding remainder to winner', () => {
            // 84/10=8.4→8, 75/10=7.5→7. Sum=15<16. Remainder=1 to winner(us)→9
            const result = AccountingEngine.calculateRoundResult(
                84, 75, 0, 0, 'HOKUM', 1 as DoublingLevel, null
            );
            expect(result.us.gamePoints).toBe(9);
            expect(result.them.gamePoints).toBe(7);
        });

        it('should handle HOKUM max raw (162 abnat → 16 pts)', () => {
            // 162/10=16.2→16. themRaw=0 → Kaboot
            const result = AccountingEngine.calculateRoundResult(
                162, 0, 0, 0, 'HOKUM', 1 as DoublingLevel, 'us'
            );
            expect(result.us.isKaboot).toBe(true);
            expect(result.us.gamePoints).toBe(25);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // Kaboot (Capot - All Tricks Won)
    // ═══════════════════════════════════════════════════════════
    describe('Kaboot', () => {
        it('should award 44 points for SUN Kaboot', () => {
            const result = AccountingEngine.calculateRoundResult(
                130, 0, 0, 0, 'SUN', 1 as DoublingLevel, 'us'
            );
            expect(result.us.isKaboot).toBe(true);
            expect(result.us.gamePoints).toBe(44);
            expect(result.them.gamePoints).toBe(0);
        });

        it('should award 25 points for HOKUM Kaboot', () => {
            const result = AccountingEngine.calculateRoundResult(
                162, 0, 0, 0, 'HOKUM', 1 as DoublingLevel, 'us'
            );
            expect(result.us.isKaboot).toBe(true);
            expect(result.us.gamePoints).toBe(25);
            expect(result.them.gamePoints).toBe(0);
        });

        it('should detect Kaboot for opponent team', () => {
            const result = AccountingEngine.calculateRoundResult(
                0, 162, 0, 0, 'HOKUM', 1 as DoublingLevel, 'them'
            );
            expect(result.them.isKaboot).toBe(true);
            expect(result.them.gamePoints).toBe(25);
            expect(result.us.gamePoints).toBe(0);
        });

        it('should NOT detect Kaboot if both are 0', () => {
            const result = AccountingEngine.calculateRoundResult(
                0, 0, 0, 0, 'SUN', 1 as DoublingLevel, null
            );
            expect(result.us.isKaboot).toBe(false);
            expect(result.them.isKaboot).toBe(false);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // Khasara (Buyer Loss)
    // ═══════════════════════════════════════════════════════════
    describe('Khasara', () => {
        it('should give opponent ALL 26 points in SUN if bidder scores ≤ 13', () => {
            // Bidder (us) scored exactly 65 abnat → 13 pts → ≤ 13 → KHASARA
            const result = AccountingEngine.calculateRoundResult(
                65, 65, 0, 0, 'SUN', 1 as DoublingLevel, 'us'
            );
            expect(result.us.gamePoints).toBe(0);
            expect(result.them.gamePoints).toBe(26);
        });

        it('should give opponent ALL 16 points in HOKUM if bidder scores ≤ 8', () => {
            // Bidder (us) scored 80 abnat → 80/10=8 → ≤ 8 → KHASARA
            const result = AccountingEngine.calculateRoundResult(
                80, 82, 0, 0, 'HOKUM', 1 as DoublingLevel, 'us'
            );
            expect(result.us.gamePoints).toBe(0);
            expect(result.them.gamePoints).toBe(16);
        });

        it('should NOT trigger Khasara if bidder scores > threshold', () => {
            // Bidder (us) scored 70 abnat → 70*2/10=14 pts in SUN → > 13 → WIN
            const result = AccountingEngine.calculateRoundResult(
                70, 60, 0, 0, 'SUN', 1 as DoublingLevel, 'us'
            );
            expect(result.us.gamePoints).toBe(14);
            expect(result.them.gamePoints).toBe(12);
        });

        it('should handle Khasara when opponent is bidder', () => {
            // Them bid SUN, them scored 60 abnat → 12 pts → ≤ 13 → KHASARA
            const result = AccountingEngine.calculateRoundResult(
                70, 60, 0, 0, 'SUN', 1 as DoublingLevel, 'them'
            );
            expect(result.them.gamePoints).toBe(0);
            expect(result.us.gamePoints).toBe(26);
        });

        it('should NOT trigger Khasara if bidderTeam is null', () => {
            // No bidder specified → no Khasara check
            const result = AccountingEngine.calculateRoundResult(
                65, 65, 0, 0, 'SUN', 1 as DoublingLevel, null
            );
            expect(result.us.gamePoints).toBe(13);
            expect(result.them.gamePoints).toBe(13);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // Doubling
    // ═══════════════════════════════════════════════════════════
    describe('Doubling', () => {
        it('should multiply total and give all to winner when doubled', () => {
            // SUN: Us=80(16pts), Them=50(10pts). Total=26. Winner(us): 26×2=52
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 0, 'SUN', 2 as DoublingLevel, 'us'
            );
            expect(result.us.gamePoints).toBe(52);
            expect(result.them.gamePoints).toBe(0);
        });

        it('should handle tripling (×3)', () => {
            // SUN: Us=80(16pts), Them=50(10pts). Total=26. Winner(us): 26×3=78
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 0, 'SUN', 3 as DoublingLevel, 'us'
            );
            expect(result.us.gamePoints).toBe(78);
            expect(result.them.gamePoints).toBe(0);
        });

        it('should not multiply if level is 1', () => {
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 0, 'SUN', 1 as DoublingLevel, 'us'
            );
            expect(result.us.gamePoints).toBe(16);
            expect(result.them.gamePoints).toBe(10);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // Baloot Bonus
    // ═══════════════════════════════════════════════════════════
    describe('Baloot bonus', () => {
        it('should add flat 2 points for Baloot (never multiplied)', () => {
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 0, 'SUN', 1 as DoublingLevel, 'us', true, false
            );
            expect(result.us.gamePoints).toBe(18); // 16 + 2
            expect(result.them.gamePoints).toBe(10);
        });

        it('should add Baloot for both teams independently', () => {
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 0, 'SUN', 1 as DoublingLevel, 'us', true, true
            );
            expect(result.us.gamePoints).toBe(18);  // 16 + 2
            expect(result.them.gamePoints).toBe(12); // 10 + 2
        });

        it('should NOT multiply Baloot bonus even when doubled', () => {
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 0, 'SUN', 2 as DoublingLevel, 'us', true, false
            );
            // Winner (us): 26 × 2 = 52 + 2 Baloot = 54
            expect(result.us.gamePoints).toBe(54);
            expect(result.them.gamePoints).toBe(0);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // Project Abnat Values
    // ═══════════════════════════════════════════════════════════
    describe('getProjectAbnatValue', () => {
        it('should return correct values for FOUR_HUNDRED', () => {
            expect(AccountingEngine.getProjectAbnatValue(ProjectType.FOUR_HUNDRED, 'SUN')).toBeGreaterThan(0);
            expect(AccountingEngine.getProjectAbnatValue(ProjectType.FOUR_HUNDRED, 'HOKUM')).toBe(0);
        });

        it('should return values for HUNDRED in SUN and HOKUM', () => {
            const sunVal = AccountingEngine.getProjectAbnatValue(ProjectType.HUNDRED, 'SUN');
            const hokumVal = AccountingEngine.getProjectAbnatValue(ProjectType.HUNDRED, 'HOKUM');
            expect(sunVal).toBeGreaterThan(hokumVal);
            expect(hokumVal).toBeGreaterThan(0);
        });

        it('should return values for FIFTY', () => {
            const sunVal = AccountingEngine.getProjectAbnatValue(ProjectType.FIFTY, 'SUN');
            const hokumVal = AccountingEngine.getProjectAbnatValue(ProjectType.FIFTY, 'HOKUM');
            expect(sunVal).toBeGreaterThan(0);
            expect(hokumVal).toBeGreaterThan(0);
        });

        it('should return values for SIRA', () => {
            const sunVal = AccountingEngine.getProjectAbnatValue(ProjectType.SIRA, 'SUN');
            const hokumVal = AccountingEngine.getProjectAbnatValue(ProjectType.SIRA, 'HOKUM');
            expect(sunVal).toBeGreaterThan(0);
            expect(hokumVal).toBeGreaterThan(0);
        });

        it('should return 0 for BALOOT (handled as flat game points)', () => {
            expect(AccountingEngine.getProjectAbnatValue(ProjectType.BALOOT, 'SUN')).toBe(0);
            expect(AccountingEngine.getProjectAbnatValue(ProjectType.BALOOT, 'HOKUM')).toBe(0);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // Projects in Scoring
    // ═══════════════════════════════════════════════════════════
    describe('Projects in scoring', () => {
        it('should include project abnat in totalRaw', () => {
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 20, 0, 'SUN', 1 as DoublingLevel, 'us'
            );
            expect(result.us.totalRaw).toBe(100); // 80 + 20
            // Game points: 100 * 2 / 10 = 20
            expect(result.us.gamePoints).toBe(20);
        });

        it('should include opponent projects in their totalRaw', () => {
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 10, 'SUN', 1 as DoublingLevel, 'us'
            );
            expect(result.them.totalRaw).toBe(60); // 50 + 10
            expect(result.them.gamePoints).toBe(12); // 60*2/10
        });
    });

    // ═══════════════════════════════════════════════════════════
    // ScoreBreakdown Structure
    // ═══════════════════════════════════════════════════════════
    describe('ScoreBreakdown structure', () => {
        it('should populate all breakdown fields', () => {
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 10, 5, 'SUN', 1 as DoublingLevel, 'us'
            );

            expect(result.us.rawCardPoints).toBe(80);
            expect(result.us.projectPoints).toBe(10);
            expect(result.us.totalRaw).toBe(90);
            expect(result.us.isKaboot).toBe(false);
            expect(result.us.multiplierApplied).toBe(1);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // Edge Cases
    // ═══════════════════════════════════════════════════════════
    describe('Edge cases', () => {
        it('should handle tie correctly (no bidder)', () => {
            const result = AccountingEngine.calculateRoundResult(
                65, 65, 0, 0, 'SUN', 1 as DoublingLevel, null
            );
            expect(result.winner).toBe('tie');
        });

        it('should handle zero-sum game', () => {
            const result = AccountingEngine.calculateRoundResult(
                0, 0, 0, 0, 'SUN', 1 as DoublingLevel, null
            );
            expect(result.us.gamePoints).toBe(0);
            expect(result.them.gamePoints).toBe(0);
        });

        it('should return baida as false (placeholder)', () => {
            const result = AccountingEngine.calculateRoundResult(
                80, 50, 0, 0, 'SUN', 1 as DoublingLevel, 'us'
            );
            expect(result.baida).toBe(false);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // explainCalculation
    // ═══════════════════════════════════════════════════════════
    describe('explainCalculation', () => {
        it('should return non-empty array of explanation steps', () => {
            const steps = AccountingEngine.explainCalculation(80, 50, 'SUN', 'us');
            expect(steps.length).toBeGreaterThan(0);
        });

        it('should include bid type in first step', () => {
            const steps = AccountingEngine.explainCalculation(80, 50, 'SUN', 'us');
            expect(steps[0]).toContain('SUN');
        });

        it('should work for HOKUM as well', () => {
            const steps = AccountingEngine.explainCalculation(90, 72, 'HOKUM', 'them');
            expect(steps.length).toBeGreaterThan(0);
            expect(steps[0]).toContain('HOKUM');
        });
    });
});
