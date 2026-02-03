import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi } from 'vitest';
import Lobby from '../Lobby';

// Mock Lucide icons
vi.mock('lucide-react', () => ({
    Clock: () => <span data-testid="icon-clock">Clock</span>,
    Shield: () => <span data-testid="icon-shield">Shield</span>,
    ShieldAlert: () => <span data-testid="icon-shield-alert">ShieldAlert</span>,
    Play: () => <span data-testid="icon-play">Play</span>,
    Gamepad2: () => <span data-testid="icon-gamepad">Gamepad</span>,
    Brain: () => <span data-testid="icon-brain">Brain</span>,
    RefreshCcw: () => <span data-testid="icon-refresh">Refresh</span>,
}));

// Mock dynamic import
vi.mock('../utils/devLogger', () => ({
    devLogger: {
        log: vi.fn(),
    }
}));

describe('Lobby Component', () => {
    const mockOnStartGame = vi.fn();
    const mockOnMultiplayer = vi.fn();
    const mockOnAIStudio = vi.fn();
    const mockOnAIClassroom = vi.fn();
    const mockOnReplay = vi.fn();

    const defaultProps = {
        onStartGame: mockOnStartGame,
        onMultiplayer: mockOnMultiplayer,
        onAIStudio: mockOnAIStudio,
        onAIClassroom: mockOnAIClassroom,
        onReplay: mockOnReplay,
    };

    it('renders correctly', () => {
        render(<Lobby {...defaultProps} />);
        expect(screen.getByText('بلوت')).toBeInTheDocument();
        expect(screen.getByText('إعدادات الجلسة')).toBeInTheDocument();
    });

    it('allows changing turn duration', () => {
        render(<Lobby {...defaultProps} />);

        // Find by accessible name which we will add
        const duration5Btn = screen.getByRole('button', { name: /^5 seconds$/i });
        fireEvent.click(duration5Btn);

        const startBtn = screen.getByRole('button', { name: /Start Game against Computer/i });
        fireEvent.click(startBtn);

        expect(mockOnStartGame).toHaveBeenCalledWith(expect.objectContaining({
            turnDuration: 5
        }));
    });

    it('allows toggling strict mode', () => {
        render(<Lobby {...defaultProps} />);

        const challengeBtn = screen.getByText('نظام التحدي');
        fireEvent.click(challengeBtn);

        const startBtn = screen.getByRole('button', { name: /Start Game against Computer/i });
        fireEvent.click(startBtn);

        expect(mockOnStartGame).toHaveBeenCalledWith(expect.objectContaining({
            strictMode: false
        }));
    });

    it('has accessibility attributes for turn duration', () => {
        render(<Lobby {...defaultProps} />);

        const group = screen.getByRole('group', { name: /Turn duration/i });
        expect(group).toBeInTheDocument();

        const button3 = screen.getByRole('button', { name: /^3 seconds$/i });
        expect(button3).toHaveAttribute('aria-pressed', 'true');

        const button5 = screen.getByRole('button', { name: /^5 seconds$/i });
        expect(button5).toHaveAttribute('aria-pressed', 'false');
    });

    it('has accessibility attributes for game mode', () => {
        render(<Lobby {...defaultProps} />);

        const group = screen.getByRole('group', { name: /Game mode/i });
        expect(group).toBeInTheDocument();

        const strictBtn = screen.getByRole('button', { name: /منع الغش تلقائياً/i });
        expect(strictBtn).toHaveAttribute('aria-pressed', 'true');

        const challengeBtn = screen.getByRole('button', { name: /نظام التحدي/i });
        expect(challengeBtn).toHaveAttribute('aria-pressed', 'false');
    });
});
