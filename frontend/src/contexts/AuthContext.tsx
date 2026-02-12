import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authService, SignupResponse } from '../services/AuthService';
import { UserProfile } from '../types';

interface AuthContextType {
    userProfile: UserProfile | null;
    ownedItems: string[];
    equippedItems: { card: string; table: string };
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    signup: (firstName: string, lastName: string, email: string, password: string) => Promise<SignupResponse>;
    logout: () => void;
    updateInventory: (ownedItems: string[], equippedItems: any, coins?: number) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [ownedItems, setOwnedItems] = useState<string[]>(() => {
         const saved = localStorage.getItem('baloot_owned_items');
         return saved ? JSON.parse(saved) : ['card_default', 'table_default'];
    });
    const [equippedItems, setEquippedItems] = useState<{ card: string, table: string }>(() => {
        const saved = localStorage.getItem('baloot_equipped_items');
        return saved ? JSON.parse(saved) : { card: 'card_default', table: 'table_default' };
    });
    const [isLoading, setIsLoading] = useState(true);

    const fetchProfile = async () => {
        try {
            if (authService.isAuthenticated()) {
                const { profile, inventory } = await authService.getProfile();
                setUserProfile(profile);
                setOwnedItems(inventory.ownedItems);
                setEquippedItems(inventory.equippedItems);

                // Sync to localStorage
                localStorage.setItem('baloot_user_profile', JSON.stringify(profile));
                localStorage.setItem('baloot_owned_items', JSON.stringify(inventory.ownedItems));
                localStorage.setItem('baloot_equipped_items', JSON.stringify(inventory.equippedItems));
            } else {
                 // Guest mode or token expired
                 const savedProfile = localStorage.getItem('baloot_user_profile');
                 if (savedProfile) {
                     // We have a saved profile but no token (maybe guest profile?)
                     // If it was a real user profile, it might be stale.
                     // But for now let's assume if no token, we are guest.
                     setUserProfile(JSON.parse(savedProfile));
                 }
            }
        } catch (e) {
            console.error("Auth check failed:", e);
            authService.removeToken();
            // Fallback to guest
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchProfile();
    }, []);

    useEffect(() => {
        if (userProfile) {
            localStorage.setItem('baloot_user_profile', JSON.stringify(userProfile));
        }
    }, [userProfile]);

    const login = async (email: string, password: string) => {
        setIsLoading(true);
        try {
            await authService.login(email, password);
            await fetchProfile();
        } catch (e) {
            setIsLoading(false);
            throw e;
        }
    };

    const signup = async (firstName: string, lastName: string, email: string, password: string) => {
        return await authService.signup(firstName, lastName, email, password);
    };

    const logout = () => {
        authService.logout();
        setUserProfile(null);
        // Reset to defaults or keep local items?
        // Better to reset to safe defaults to avoid leaking user data
        setOwnedItems(['card_default', 'table_default']);
        setEquippedItems({ card: 'card_default', table: 'table_default' });

        localStorage.removeItem('baloot_user_profile');
        localStorage.removeItem('baloot_auth_token');
        // We might want to clear items too
        localStorage.setItem('baloot_owned_items', JSON.stringify(['card_default', 'table_default']));
        localStorage.setItem('baloot_equipped_items', JSON.stringify({ card: 'card_default', table: 'table_default' }));
    };

    const updateInventory = async (newOwned: string[], newEquipped: any, coins?: number) => {
        setOwnedItems(newOwned);
        setEquippedItems(newEquipped);

        if (coins !== undefined && userProfile) {
            setUserProfile(prev => prev ? ({ ...prev, coins }) : null);
        }

        if (authService.isAuthenticated()) {
            try {
                await authService.updateInventory(newOwned, newEquipped, coins);
            } catch (e) {
                console.error("Failed to sync inventory", e);
            }
        }

        localStorage.setItem('baloot_owned_items', JSON.stringify(newOwned));
        localStorage.setItem('baloot_equipped_items', JSON.stringify(newEquipped));
    };

    return (
        <AuthContext.Provider value={{
            userProfile,
            ownedItems,
            equippedItems,
            isAuthenticated: authService.isAuthenticated(),
            isLoading,
            login,
            signup,
            logout,
            updateInventory
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
