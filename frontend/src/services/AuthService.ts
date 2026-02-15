import { UserProfile, LeagueTier } from '../types';

export class AuthService {
    private static TOKEN_KEY = 'baloot_auth_token';

    static getToken(): string | null {
        return localStorage.getItem(this.TOKEN_KEY);
    }

    static setToken(token: string) {
        localStorage.setItem(this.TOKEN_KEY, token);
    }

    static logout() {
        localStorage.removeItem(this.TOKEN_KEY);
    }

    static async signup(data: { firstName: string, lastName: string, email: string, password: string }): Promise<any> {
        const response = await fetch('/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const resData = await response.json();
        if (!response.ok) {
            throw new Error(resData.error || 'Signup failed');
        }
        return resData;
    }

    static async signin(data: { email: string, password: string }): Promise<UserProfile> {
        const response = await fetch('/signin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const resData = await response.json();
        if (!response.ok) {
            throw new Error(resData.error || 'Signin failed');
        }

        this.setToken(resData.token);

        // Map response to UserProfile
        const profile: UserProfile = {
            id: resData.email, // Use email as temporary ID
            name: `${resData.firstName} ${resData.lastName}`,
            firstName: resData.firstName,
            lastName: resData.lastName,
            email: resData.email,
            leaguePoints: resData.leaguePoints || 1000,
            tier: this.calculateTier(resData.leaguePoints || 1000),
            coins: resData.coins || 1000,
            ownedItems: resData.ownedItems || [],
            equippedItems: resData.equippedItems || { card: 'card_default', table: 'table_default' },
            level: 1,
            xp: 0,
            xpToNextLevel: 1000
        };

        return profile;
    }

    static async getUser(): Promise<UserProfile> {
        const token = this.getToken();
        if (!token) throw new Error("No token");

        const response = await fetch('/user', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const resData = await response.json();
        if (!response.ok) throw new Error(resData.error || "Failed to fetch user");

        // resData structure: { user: {user_id, first_name, ...}, leaguePoints, tier, coins, ... }
        const u = resData.user;

        const profile: UserProfile = {
            id: u.user_id ? String(u.user_id) : u.email,
            name: `${u.first_name} ${u.last_name}`,
            firstName: u.first_name,
            lastName: u.last_name,
            email: u.email,
            leaguePoints: resData.leaguePoints,
            tier: resData.tier as LeagueTier,
            coins: resData.coins,
            ownedItems: resData.ownedItems,
            equippedItems: resData.equippedItems,
            level: 1,
            xp: 0,
            xpToNextLevel: 1000
        };

        return profile;
    }

    static async purchaseItem(itemId: string, cost: number): Promise<{success: boolean, coins: number, ownedItems: string[]}> {
        const token = this.getToken();
        if (!token) throw new Error("No token");

        const response = await fetch('/shop/purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ itemId, cost })
        });

        const resData = await response.json();
        if (!response.ok) {
             throw new Error(resData.error || resData.message || "Purchase failed");
        }

        return resData;
    }

    static async equipItem(itemId: string, type: 'card' | 'table'): Promise<{success: boolean, equippedItems: {card: string, table: string}}> {
        const token = this.getToken();
        if (!token) throw new Error("No token");

        const response = await fetch('/shop/equip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ itemId, type })
        });

        const resData = await response.json();
        if (!response.ok) {
             throw new Error(resData.error || resData.message || "Equip failed");
        }

        return resData;
    }

    private static calculateTier(points: number): LeagueTier {
        if (points >= 2000) return LeagueTier.grandmaster;
        if (points >= 1800) return LeagueTier.DIAMOND;
        if (points >= 1600) return LeagueTier.PLATINUM;
        if (points >= 1400) return LeagueTier.GOLD;
        if (points >= 1200) return LeagueTier.SILVER;
        return LeagueTier.BRONZE;
    }
}
