import { API_BASE_URL } from '../config';
import { UserProfile, LeagueTier } from '../types';

export interface AuthResponse {
    token: string;
    email: string;
    firstName: string;
    lastName: string;
}

export interface SignupResponse {
    message: string;
    email: string;
    firstName: string;
    lastName: string;
    user_id: number;
}

export interface InventoryData {
    ownedItems: string[];
    equippedItems: { card: string; table: string };
}

class AuthService {
    private tokenKey = 'baloot_auth_token';

    getToken(): string | null {
        return localStorage.getItem(this.tokenKey);
    }

    setToken(token: string) {
        localStorage.setItem(this.tokenKey, token);
    }

    removeToken() {
        localStorage.removeItem(this.tokenKey);
    }

    isAuthenticated(): boolean {
        return !!this.getToken();
    }

    async login(email: string, password: string): Promise<AuthResponse> {
        const response = await fetch(`${API_BASE_URL}/signin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Login failed');
        }

        const data = await response.json();
        this.setToken(data.token);
        return data;
    }

    async signup(firstName: string, lastName: string, email: string, password: string): Promise<SignupResponse> {
        const response = await fetch(`${API_BASE_URL}/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ firstName, lastName, email, password }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Signup failed');
        }

        return await response.json();
    }

    async getProfile(): Promise<{ profile: UserProfile, inventory: InventoryData }> {
        const token = this.getToken();
        if (!token) throw new Error('No token found');

        const response = await fetch(`${API_BASE_URL}/user`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });

        if (!response.ok) {
             if (response.status === 401) this.removeToken();
             throw new Error('Failed to fetch profile');
        }

        const data = await response.json();
        // Map backend response to UserProfile
        const user = data.user;
        const profile: UserProfile = {
            id: user.user_id.toString(),
            name: `${user.first_name} ${user.last_name}`,
            firstName: user.first_name,
            lastName: user.last_name,
            email: user.email,
            leaguePoints: data.leaguePoints,
            tier: data.tier as LeagueTier,
            level: 1, // Todo: calculate from XP or points
            xp: 0,
            xpToNextLevel: 1000,
            coins: data.coins || 0,
        };

        const inventory: InventoryData = {
            ownedItems: data.ownedItems || ['card_default', 'table_default'],
            equippedItems: data.equippedItems || { card: 'card_default', table: 'table_default' }
        };

        return { profile, inventory };
    }

    async updateInventory(ownedItems: string[], equippedItems: any, coins?: number): Promise<void> {
        const token = this.getToken();
        if (!token) return;

        await fetch(`${API_BASE_URL}/user/inventory`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ ownedItems, equippedItems, coins }),
        });
    }

    logout() {
        this.removeToken();
        // reload or clear state
    }
}

export const authService = new AuthService();
