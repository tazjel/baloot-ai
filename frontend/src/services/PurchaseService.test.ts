import { describe, it, expect } from 'vitest';
import { PurchaseService } from './PurchaseService';
import { UserProfile } from '../types';

describe('PurchaseService', () => {
    // canAfford
    it('canAfford should return true if user has enough coins', () => {
        const user: UserProfile = { coins: 100 } as any;
        expect(PurchaseService.canAfford(user, 50)).toBe(true);
        expect(PurchaseService.canAfford(user, 100)).toBe(true);
    });

    it('canAfford should return false if user has insufficient coins', () => {
        const user: UserProfile = { coins: 40 } as any;
        expect(PurchaseService.canAfford(user, 50)).toBe(false);
    });

    // processTransaction
    it('processTransaction should deduct cost', () => {
        const balance = PurchaseService.processTransaction(100, 40);
        expect(balance).toBe(60);
    });

    it('processTransaction should throw error on insufficient funds', () => {
        expect(() => PurchaseService.processTransaction(30, 40)).toThrow("Insufficient funds");
    });

    // generateReceipt
    it('generateReceipt should format string correctly', () => {
        const receipt = PurchaseService.generateReceipt('skin_123', 50, 20);
        expect(receipt).toBe("Purchased skin_123 for 50. Remaining balance: 20");
    });
});
