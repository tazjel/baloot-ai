import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { AuthProvider } from '../contexts/AuthContext';
import AuthModal from '../components/auth/AuthModal';
import AuthService from '../services/AuthService';

// Mock AuthService
vi.mock('../services/AuthService', () => ({
    default: {
        login: vi.fn(),
        register: vi.fn(),
        getUser: vi.fn(),
        logout: vi.fn(),
        getToken: vi.fn(),
        setToken: vi.fn(),
        updateProfile: vi.fn()
    }
}));

describe('Auth Flow', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders AuthModal and handles login', async () => {
        const mockLogin = vi.spyOn(AuthService, 'login').mockResolvedValue({ token: 'fake-token' });
        const mockGetUser = vi.spyOn(AuthService, 'getUser').mockResolvedValue({
            id: '1',
            name: 'Test User',
            firstName: 'Test',
            lastName: 'User',
            email: 'test@example.com',
            leaguePoints: 1000,
            tier: 'Bronze',
            coins: 100,
            level: 1,
            xp: 0,
            xpToNextLevel: 1000
        });

        const TestComponent = () => {
            const [isOpen, setIsOpen] = React.useState(true);
            return (
                <AuthProvider>
                    <AuthModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
                </AuthProvider>
            );
        };

        render(<TestComponent />);

        // Check if Modal is open
        expect(screen.getByText('تسجيل الدخول')).toBeInTheDocument();

        // Wait for initial loading to finish (reloadUser)
        await waitFor(() => {
            expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
            // Or check for the button text
            expect(screen.getAllByText('دخول').length).toBeGreaterThan(0);
        });

        // Fill form
        fireEvent.change(screen.getByPlaceholderText('example@email.com'), { target: { value: 'test@example.com' } });
        fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'password' } });

        // Click Login
        const loginButtons = screen.getAllByText('دخول');
        const loginButton = loginButtons.find(el => el.tagName === 'BUTTON');
        if (loginButton) fireEvent.click(loginButton);
        else throw new Error("Login button not found");

        // Wait for login to be called
        await waitFor(() => {
            expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password');
        });

        // Wait for getUser to be called (reloadUser)
        // Note: reloadUser is called on mount too, so getUser might be called multiple times.
        await waitFor(() => {
            expect(mockGetUser).toHaveBeenCalled();
        });
    });
});
