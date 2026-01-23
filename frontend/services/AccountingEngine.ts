import { CardModel, DeclaredProject, ProjectType, Suit, PlayerPosition, ScoreBreakdown, Rank, DoublingLevel } from '../types';
import { POINT_VALUES } from '../utils/gameLogic';

/**
 * ACCOUNTING ENGINE
 * 
 * Based on comprehensive research of the standard scoring system.
 * 
 * KEY CONSTANTS:
 * - SUN Total: 130 Abnat (120 cards + 10 last trick) → 26 Game Points
 * - HOKUM Total: 162 Abnat (152 cards + 10 last trick) → 16 Game Points
 * 
 * FORMULAS:
 * - SUN: Points = (Abnat × 2) / 10  (no rounding needed - always whole number)
 * - HOKUM: Points = Round(Abnat / 10) with 0.5 rounding DOWN
 * 
 * WIN CONDITIONS:
 * - SUN: Buyer must score > 13 points (> 65 Abnat)
 * - HOKUM: Buyer must score > 8 points
 * 
 * KHASARA (Buyer Loss):
 * - SUN: Opponent takes ALL 26 points
 * - HOKUM: Opponent takes ALL 16 points
 * 
 * KABOOT (Capot - All Tricks):
 * - SUN: 44 points (includes 10-point last trick bonus doubled: 120*2/10 + 2*2 = 26 + 8... actually just fixed 44)
 * - HOKUM: 25 points
 */
export class AccountingEngine {

    /**
     * Calculates the final Game Points for a round given the raw inputs.
     * This is the "Truth" source for scoring - matches standard rules exactly.
     */
    public static calculateRoundResult(
        usRaw: number,           // Raw Abnat for "Us" team (includes last trick bonus if won)
        themRaw: number,         // Raw Abnat for "Them" team
        usProjects: number,      // Sum of project Abnat values (NOT game points yet)
        themProjects: number,
        bidType: 'SUN' | 'HOKUM',
        doublingLevel: DoublingLevel,
        bidderTeam: 'us' | 'them' | null,
        hasBalootUs: boolean = false,    // NEW: Track Baloot separately (2 pts, never multiplied)
        hasBalootThem: boolean = false
    ): { us: ScoreBreakdown, them: ScoreBreakdown, winner: 'us' | 'them' | 'tie', baida: boolean } {

        // ═══════════════════════════════════════════════════════════
        // 1. INITIAL STRUCTURES
        // ═══════════════════════════════════════════════════════════
        const us: ScoreBreakdown = {
            rawCardPoints: usRaw,
            projectPoints: usProjects,
            totalRaw: usRaw + usProjects,
            gamePoints: 0,
            isKaboot: false,
            multiplierApplied: doublingLevel
        };

        const them: ScoreBreakdown = {
            rawCardPoints: themRaw,
            projectPoints: themProjects,
            totalRaw: themRaw + themProjects,
            gamePoints: 0,
            isKaboot: false,
            multiplierApplied: doublingLevel
        };

        // ═══════════════════════════════════════════════════════════
        // 2. KABOOT DETECTION (All Tricks Won)
        // ═══════════════════════════════════════════════════════════
        // If opponent scored 0 raw Abnat, it's a Kaboot (they got no tricks)
        const isUsKaboot = themRaw === 0 && usRaw > 0;
        const isThemKaboot = usRaw === 0 && themRaw > 0;

        // ═══════════════════════════════════════════════════════════
        // 3. CONVERSION FUNCTIONS (Abnat → Game Points)
        // ═══════════════════════════════════════════════════════════

        /**
         * SUN CONVERSION: Points = (Abnat × 2) / 10
         * - This formula naturally handles .5 cases (65 × 2 = 130, 130/10 = 13)
         * - Total pool: 130 Abnat → 26 Game Points
         */
        const convertSunAbnat = (abnat: number): number => {
            return (abnat * 2) / 10;
        };

        /**
         * HOKUM CONVERSION: Points = Round(Abnat / 10) with 0.5 rounding DOWN
         * - 15.5 → 15 (round half down per ExternalApp)
         * - 15.6 → 16
         * - Total pool: 162 Abnat → 16 Game Points
         */
        const convertHokumAbnat = (abnat: number): number => {
            const divided = abnat / 10;
            const decimal = divided - Math.floor(divided);

            // Round half DOWN (Standard rule: 15.5 → 15)
            if (decimal <= 0.5) {
                return Math.floor(divided);
            } else {
                return Math.ceil(divided);
            }
        };

        // ═══════════════════════════════════════════════════════════
        // 4. BASE CALCULATION
        // ═══════════════════════════════════════════════════════════
        let usBase = 0;
        let themBase = 0;
        const maxPoints = bidType === 'SUN' ? 26 : 16;

        if (isUsKaboot) {
            // US won all tricks
            us.isKaboot = true;
            usBase = bidType === 'SUN' ? 44 : 25;
            themBase = 0;
        } else if (isThemKaboot) {
            // THEM won all tricks
            them.isKaboot = true;
            themBase = bidType === 'SUN' ? 44 : 25;
            usBase = 0;
        } else {
            // Normal calculation
            if (bidType === 'SUN') {
                usBase = convertSunAbnat(us.totalRaw);
                themBase = convertSunAbnat(them.totalRaw);
            } else {
                // HOKUM: Calculate winner first, loser gets remainder
                const usRounded = convertHokumAbnat(us.totalRaw);
                const themRounded = convertHokumAbnat(them.totalRaw);

                // Check if sum exceeds max (rounding can cause this)
                const sum = usRounded + themRounded;

                if (sum > maxPoints) {
                    // Winner takes calculated, loser gets remainder
                    if (usRounded >= themRounded) {
                        usBase = usRounded;
                        themBase = maxPoints - usRounded;
                    } else {
                        themBase = themRounded;
                        usBase = maxPoints - themRounded;
                    }
                } else if (sum < maxPoints) {
                    // Add remainder to winner
                    if (usRounded >= themRounded) {
                        usBase = usRounded + (maxPoints - sum);
                        themBase = themRounded;
                    } else {
                        themBase = themRounded + (maxPoints - sum);
                        usBase = usRounded;
                    }
                } else {
                    usBase = usRounded;
                    themBase = themRounded;
                }
            }
        }

        // ═══════════════════════════════════════════════════════════
        // 5. KHASARA CHECK (Buyer Win/Loss Condition)
        // ═══════════════════════════════════════════════════════════
        // The Buyer must score MORE than the threshold, otherwise they LOSE
        // and opponent takes ALL points.

        if (!isUsKaboot && !isThemKaboot && bidderTeam) {
            const bidderScore = bidderTeam === 'us' ? usBase : themBase;

            // WIN THRESHOLDS (Buyer must score MORE than this):
            // - SUN: > 13 points (meaning 14+ to win)
            // - HOKUM: > 8 points (meaning 9+ to win)
            const winThreshold = bidType === 'SUN' ? 13 : 8;

            if (bidderScore <= winThreshold) {
                // ══════════════════════════════════════
                // KHASARA! Buyer Lost!
                // Opponent takes ALL points from the pool
                // ══════════════════════════════════════
                if (bidderTeam === 'us') {
                    usBase = 0;
                    themBase = maxPoints; // 26 for SUN, 16 for HOKUM
                } else {
                    themBase = 0;
                    usBase = maxPoints;
                }
            }
        }

        // ═══════════════════════════════════════════════════════════
        // 6. APPLY BASE POINTS
        // ═══════════════════════════════════════════════════════════
        us.gamePoints = usBase;
        them.gamePoints = themBase;

        // ═══════════════════════════════════════════════════════════
        // 7. DOUBLING MULTIPLIER
        // ═══════════════════════════════════════════════════════════
        // When doubled: Winner takes (Total Points + Project Points) × Multiplier
        // Loser gets 0
        // IMPORTANT: Baloot 2 pts is NEVER multiplied - added as flat scalar at end

        if (doublingLevel > 1) {
            const totalGamePoints = us.gamePoints + them.gamePoints;

            if (us.gamePoints > them.gamePoints) {
                // US wins - takes all × multiplier
                us.gamePoints = totalGamePoints * doublingLevel;
                them.gamePoints = 0;
            } else if (them.gamePoints > us.gamePoints) {
                // THEM wins - takes all × multiplier
                them.gamePoints = totalGamePoints * doublingLevel;
                us.gamePoints = 0;
            }
            // Tie: Both keep their multiplied scores (rare)
        }

        // ═══════════════════════════════════════════════════════════
        // 8. BALOOT BONUS (Flat 2 points, NEVER multiplied)
        // ═══════════════════════════════════════════════════════════
        if (hasBalootUs) {
            us.gamePoints += 2;
        }
        if (hasBalootThem) {
            them.gamePoints += 2;
        }

        // ═══════════════════════════════════════════════════════════
        // 9. DETERMINE WINNER & RETURN
        // ═══════════════════════════════════════════════════════════
        const winner = us.gamePoints > them.gamePoints ? 'us'
            : them.gamePoints > us.gamePoints ? 'them'
                : 'tie';

        return {
            us,
            them,
            winner,
            baida: false // Baida (shutout) tracking if needed
        };
    }

    // ═══════════════════════════════════════════════════════════════
    // HELPER: Calculate Project Abnat Value
    // ═══════════════════════════════════════════════════════════════
    public static getProjectAbnatValue(type: ProjectType, bidType: 'SUN' | 'HOKUM'): number {
        const isSun = bidType === 'SUN';

        switch (type) {
            case ProjectType.FOUR_HUNDRED:
                // 4 Aces - Only valid in SUN
                return isSun ? 40 : 0;
            case ProjectType.HUNDRED:
                // 5-sequence or 4-of-a-kind (K/Q/J/10)
                return isSun ? 20 : 10;
            case ProjectType.FIFTY:
                // 4-sequence
                return isSun ? 10 : 5;
            case ProjectType.SIRA:
                // 3-sequence
                return isSun ? 4 : 2;
            case ProjectType.BALOOT:
                // K+Q of Trump - handled separately (flat 2 game points)
                return 0; // Don't add to Abnat, add directly to game points
            default:
                return 0;
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // HELPER: Debug - Show calculation step by step
    // ═══════════════════════════════════════════════════════════════
    public static explainCalculation(
        usRaw: number,
        themRaw: number,
        bidType: 'SUN' | 'HOKUM',
        bidderTeam: 'us' | 'them' | null
    ): string[] {
        const steps: string[] = [];

        steps.push(`📊 Round Type: ${bidType}`);
        steps.push(`🎴 Raw Abnat - Us: ${usRaw}, Them: ${themRaw}`);

        if (bidType === 'SUN') {
            const usPoints = (usRaw * 2) / 10;
            const themPoints = (themRaw * 2) / 10;
            steps.push(`📐 SUN Formula: (Abnat × 2) / 10`);
            steps.push(`   Us: (${usRaw} × 2) / 10 = ${usPoints}`);
            steps.push(`   Them: (${themRaw} × 2) / 10 = ${themPoints}`);

            if (bidderTeam) {
                const bidderScore = bidderTeam === 'us' ? usPoints : themPoints;
                steps.push(`👤 Buyer (${bidderTeam}) scored: ${bidderScore}`);
                steps.push(`   Win threshold: > 13 points`);
                if (bidderScore <= 13) {
                    steps.push(`❌ KHASARA! Buyer lost. Opponent gets 26 points.`);
                } else {
                    steps.push(`✅ Buyer wins!`);
                }
            }
        } else {
            const usPoints = Math.floor(usRaw / 10);
            const themPoints = Math.floor(themRaw / 10);
            steps.push(`📐 HOKUM Formula: Round(Abnat / 10), 0.5 rounds DOWN`);
            steps.push(`   Us: ${usRaw} / 10 = ${(usRaw / 10).toFixed(1)} → ${usPoints}`);
            steps.push(`   Them: ${themRaw} / 10 = ${(themRaw / 10).toFixed(1)} → ${themPoints}`);

            if (bidderTeam) {
                const bidderScore = bidderTeam === 'us' ? usPoints : themPoints;
                steps.push(`👤 Buyer (${bidderTeam}) scored: ${bidderScore}`);
                steps.push(`   Win threshold: > 8 points`);
                if (bidderScore <= 8) {
                    steps.push(`❌ KHASARA! Buyer lost. Opponent gets 16 points.`);
                } else {
                    steps.push(`✅ Buyer wins!`);
                }
            }
        }

        return steps;
    }
}
