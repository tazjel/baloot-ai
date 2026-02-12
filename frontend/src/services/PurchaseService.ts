import { UserProfile } from '../types';

export class PurchaseService {
    /**
     * Validates if a purchase is possible.
     */
    static canAfford(userProfile: UserProfile, cost: number): boolean {
        return userProfile.coins >= cost;
    }

    /**
     * Processes the transaction logic (calculating new balance).
     * Does not update state directly, returns new balance.
     */
    static processTransaction(currentCoins: number, cost: number): number {
        if (currentCoins < cost) {
            throw new Error("Insufficient funds");
        }
        return currentCoins - cost;
    }
    
    // Receipt generation mentioned in prompt
    static generateReceipt(itemId: string, cost: number, remainingCoins: number): string {
        return `Purchased ${itemId} for ${cost}. Remaining balance: ${remainingCoins}`;
    }
}
