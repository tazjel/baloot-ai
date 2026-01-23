
import { describe, it, expect } from 'vitest';
import { calculateFinalScore, POINT_VALUES } from './gameLogic';
import { Rank, ProjectType } from '../types';

describe('Scoring System', () => {

    describe('Point Values', () => {
        it('should have correct point values for SUN', () => {
            expect(POINT_VALUES.SUN[Rank.Ace]).toBe(11);
            expect(POINT_VALUES.SUN[Rank.Ten]).toBe(10);
            expect(POINT_VALUES.SUN[Rank.King]).toBe(4);
            expect(POINT_VALUES.SUN[Rank.Queen]).toBe(3);
            expect(POINT_VALUES.SUN[Rank.Jack]).toBe(2); // In Sun, Jack is weak
            expect(POINT_VALUES.SUN[Rank.Nine]).toBe(0);
            expect(POINT_VALUES.SUN[Rank.Eight]).toBe(0);
            expect(POINT_VALUES.SUN[Rank.Seven]).toBe(0);
        });

        it('should have correct point values for HOKUM', () => {
            expect(POINT_VALUES.HOKUM[Rank.Jack]).toBe(20); // Top trump usually
            expect(POINT_VALUES.HOKUM[Rank.Nine]).toBe(14);
            expect(POINT_VALUES.HOKUM[Rank.Ace]).toBe(11);
            expect(POINT_VALUES.HOKUM[Rank.Ten]).toBe(10);
            expect(POINT_VALUES.HOKUM[Rank.King]).toBe(4);
            expect(POINT_VALUES.HOKUM[Rank.Queen]).toBe(3);
            expect(POINT_VALUES.HOKUM[Rank.Eight]).toBe(0);
            expect(POINT_VALUES.HOKUM[Rank.Seven]).toBe(0);
        });
    });

    describe('calculateFinalScore - SUN', () => {
        // Formula: Round( (RawPoints + Projects) * 2 / 10 )

        it('should calculate normal score correctly', () => {
            // 15 Points -> 30 -> 3
            expect(calculateFinalScore(15, 0, false, 'SUN', 1, true)).toBe(3);
        });

        it('should calculate max card score correctly', () => {
            // Max Card Points in Sun = 130. 
            // 130 * 2 / 10 = 26.
            expect(calculateFinalScore(130, 0, false, 'SUN', 1, true)).toBe(26);
        });

        it('should include projects in calculation', () => {
            // 15 Cards + 100 Project = 115.
            // 115 * 2 = 230. / 10 = 23.
            expect(calculateFinalScore(15, 100, false, 'SUN', 1, true)).toBe(23);
        });

        it('should handle Kaboot (Capot) in SUN', () => {
            // Kaboot in Sun is fixed at 44 (if established rules usually say 26*2? or 44 fixed?)
            // Our code returns 44.
            expect(calculateFinalScore(130, 0, true, 'SUN', 1, true)).toBe(44);
        });

        it('should return 0 if losing a Kaboot round', () => {
            expect(calculateFinalScore(10, 0, true, 'SUN', 1, false)).toBe(0);
        });
    });

    describe('calculateFinalScore - HOKUM', () => {
        // Formula: Round( (RawPoints + Projects) / 10 )

        it('should calculate normal score correctly', () => {
            // 15 Points -> 1.5 -> 2
            expect(calculateFinalScore(15, 0, false, 'HOKUM', 1, true)).toBe(2);
            // 14 Points -> 1.4 -> 1
            expect(calculateFinalScore(14, 0, false, 'HOKUM', 1, true)).toBe(1);
        });

        it('should calculate max card score correctly', () => {
            // Max Points in Hokum = 152 (162 total including last trick bonus usually? The input is RAW points).
            // Sum of all cards in Hokum = 152.
            // 152 / 10 = 15.2 -> 15.
            expect(calculateFinalScore(152, 0, false, 'HOKUM', 1, true)).toBe(15);
        });

        it('should include projects in calculation', () => {
            // 20 Cards + 100 Project = 120.
            // 120 / 10 = 12.
            expect(calculateFinalScore(20, 100, false, 'HOKUM', 1, true)).toBe(12);
        });

        it('should handle Kaboot in HOKUM', () => {
            // Kaboot in Hokum = 25 + (Projects / 10)?
            // Case 1: No projects. 25.
            expect(calculateFinalScore(152, 0, true, 'HOKUM', 1, true)).toBe(25);

            // Case 2: With Projects (e.g. 100). 
            // 25 + (100 / 10) = 35.
            expect(calculateFinalScore(152, 100, true, 'HOKUM', 1, true)).toBe(35);
        });
    });

    describe('Score Doubling', () => {
        it('should double the score if level is 2', () => {
            // Sun: 15 pts -> 3. Doubled -> 6.
            expect(calculateFinalScore(15, 0, false, 'SUN', 2, true)).toBe(6);
        });

        it('should quadruple the score if level is 4 (if supported)', () => {
            // Hokum: 20 pts -> 2. Quadrupled -> 8.
            expect(calculateFinalScore(20, 0, false, 'HOKUM', 4, true)).toBe(8); // Assuming 4 is valid multiplier
        });
    });

});
