import { API_BASE_URL } from '../config';
import { UserProfile, LeagueTier } from '../types';

interface AuthResponse {
    token?: string;
    error?: string;
    email?: string;
    firstName?: string;
    lastName?: string;
    user_id?: number;
}

interface BackendUserResponse {
    user: {
        user_id: number;
        email: string;
        first_name: string;
        last_name: string;
    };
    leaguePoints: number;
    tier: string;
    coins: number;
    ownedItems: string[];
    equippedItems: Record<string, string>;
}

const TOKEN_KEY = 'baloot_auth_token';

class AuthService {
    getToken(): string | null {
        return localStorage.getItem(TOKEN_KEY);
    }

    setToken(token: string) {
        localStorage.setItem(TOKEN_KEY, token);
    }

    logout() {
        localStorage.removeItem(TOKEN_KEY);
        // Clear local profile cache if used
        localStorage.removeItem('baloot_user_profile');
    }

    async login(email: string, password: string): Promise<AuthResponse> {
        try {
            const res = await fetch(`${API_BASE_URL}/signin`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok && data.token) {
                this.setToken(data.token);
            }
            return data;
        } catch (e) {
            console.error("AuthService: Login failed", e);
            return { error: "Network Error" };
        }
    }

    async register(firstName: string, lastName: string, email: string, password: string): Promise<AuthResponse> {
        try {
            const res = await fetch(`${API_BASE_URL}/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ firstName, lastName, email, password })
            });
            const data = await res.json();
            return data;
        } catch (e) {
            console.error("AuthService: Register failed", e);
            return { error: "Network Error" };
        }
    }

    async getUser(): Promise<UserProfile | null> {
        const token = this.getToken();
        if (!token) return null;

        try {
            const res = await fetch(`${API_BASE_URL}/user`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (res.ok) {
                const data: BackendUserResponse = await res.json();

                // Map to frontend UserProfile
                const profile: UserProfile = {
                    id: String(data.user.user_id),
                    name: `${data.user.first_name} ${data.user.last_name}`.trim(),
                    firstName: data.user.first_name,
                    lastName: data.user.last_name,
                    email: data.user.email,
                    leaguePoints: data.leaguePoints,
                    tier: data.tier as LeagueTier,
                    coins: data.coins,
                    // Defaults for fields not yet in backend
                    level: 1,
                    xp: 0,
                    xpToNextLevel: 1000,
                    avatar: 'avatar_default'
                };

                // Also update legacy InventoryService cache
                this.syncLegacyInventory(data.ownedItems, data.equippedItems);

                return profile;
            } else {
                if (res.status === 401) {
                    this.logout();
                }
                return null;
            }
        } catch (e) {
            console.error("AuthService: getUser failed", e);
            return null;
        }
    }

    async updateProfile(updates: Partial<{ coins: number, ownedItems: string[], equippedItems: any }>): Promise<boolean> {
        const token = this.getToken();
        if (!token) return false;

        try {
             const res = await fetch(`${API_BASE_URL}/user/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(updates)
            });
            return res.ok;
        } catch (e) {
             console.error("AuthService: updateProfile failed", e);
             return false;
        }
    }

    private syncLegacyInventory(owned: string[], equipped: any) {
        // We sync backend data to localStorage so that legacy InventoryService continues to work
        if (owned && Array.isArray(owned)) {
            localStorage.setItem('baloot_owned_items', JSON.stringify(owned));
        }
        if (equipped && typeof equipped === 'object') {
            localStorage.setItem('baloot_equipped_items', JSON.stringify(equipped));
        }
    }
}

export default new AuthService();
