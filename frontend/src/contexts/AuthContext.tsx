import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AuthService from '../services/AuthService';
import { UserProfile } from '../types';

interface AuthContextType {
    user: UserProfile | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<string | null>;
    register: (firstName: string, lastName: string, email: string, password: string) => Promise<string | null>;
    logout: () => void;
    updateProfile: (updates: Partial<UserProfile>) => Promise<void>;
    reloadUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const reloadUser = async () => {
        try {
            const profile = await AuthService.getUser();
            if (profile) {
                setUser(profile);
            } else {
                setUser(null);
            }
        } catch (e) {
            console.error("AuthContext: Failed to reload user", e);
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        reloadUser();
    }, []);

    const login = async (email: string, password: string) => {
        setIsLoading(true);
        const res = await AuthService.login(email, password);
        if (res.token) {
            await reloadUser();
            return null; // Success
        }
        setIsLoading(false);
        return res.error || "Login failed";
    };

    const register = async (firstName: string, lastName: string, email: string, password: string) => {
        setIsLoading(true);
        const res = await AuthService.register(firstName, lastName, email, password);
        setIsLoading(false);
        if (res.error) return res.error;
        return null; // Success
    };

    const logout = () => {
        AuthService.logout();
        setUser(null);
    };

    const updateProfile = async (updates: Partial<UserProfile>) => {
        // Optimistic update
        if (user) {
            setUser({ ...user, ...updates });
        }

        // Map updates to backend format if needed
        const backendUpdates: any = {};
        if (updates.coins !== undefined) backendUpdates.coins = updates.coins;
        // Logic for other fields if we add them to UserProfile later

        await AuthService.updateProfile(backendUpdates);
    };

    return (
        <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, register, logout, updateProfile, reloadUser }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error("useAuth must be used within AuthProvider");
    return context;
};
