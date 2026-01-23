import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Table from '../Table';
import { GameState, GamePhase, PlayerPosition, Suit, Player, Rank } from '../../types';

// Mock dependencies
vi.mock('../../services/SoundManager', () => ({
    soundManager: {
        playDealSequence: vi.fn(),
        playProjectSound: vi.fn(),
        playAkkaSound: vi.fn(),
        playCardSound: vi.fn(),
    }
}));

// Mock devLogger to avoid console spam or errors
vi.mock('../../utils/devLogger', () => ({
    devLogger: {
        log: vi.fn(),
    }
}));

// Mock child components to simplify testing the Table logic itself
// We want to test that Table renders them and passes props, not test the children themselves.
vi.mock('../Card', () => ({
    default: ({ card, onClick, className }: any) => (
        <div
            data-testid={`card-${card.rank}-${card.suit}`}
            onClick={onClick}
            className={className}
        >
            {card.rank}{card.suit}
        </div>
    )
}));

vi.mock('../PlayerAvatar', () => ({
    // PlayerAvatar is local to Table.tsx, so this mock might not work if it's not exported.
    // However, it's a functional component, so as long as it doesn't crash, we are fine.
}));

// Mock DevLogSidebar to prevent its useEffect from crashing due to missing devLogger.getHistory
vi.mock('../DevLogSidebar', () => ({
    DevLogSidebar: () => <div data-testid="dev-log-sidebar" />
}));

vi.mock('../ActionBar', () => ({
    default: () => <div data-testid="action-bar" />
}));

vi.mock('../GablakTimer', () => ({
    default: () => <div data-testid="gablak-timer" />
}));

vi.mock('../../utils/gameLogic', () => ({
    sortHand: (hand: any) => hand,
    canDeclareAkka: () => false
}));

// Helper to create a dummy player
const createPlayer = (index: number, position: PlayerPosition, name: string): Player => ({
    index,
    name,
    position,
    avatar: 'avatar.png',
    hand: [],
    score: 0,
    isDealer: false,
    isActive: false,
    actionText: '',
    lastReasoning: ''
});

// Helper to create a basic game state
const createGameState = (): any => ({
    gameMode: 'SUN',
    phase: GamePhase.Playing,
    players: [
        createPlayer(0, PlayerPosition.Bottom, 'Me'),
        createPlayer(1, PlayerPosition.Right, 'Right'),
        createPlayer(2, PlayerPosition.Top, 'Partner'),
        createPlayer(3, PlayerPosition.Left, 'Left'),
    ],
    currentTurnIndex: 0,
    deck: [],
    tableCards: [],
    declarations: {},
    matchScores: { us: 0, them: 0 },
    teamScores: { us: 0, them: 0 },
    roundHistory: [],
    floorCard: null,
    dealerIndex: 0,
    isLocked: false,
    biddingPhase: 'SUN_OR_HOKUM',
    biddingRound: 1,
    doublingLevel: 1,
    bid: { type: 'SUN', bidder: PlayerPosition.Bottom, suit: null, doubled: false },
    settings: {
        turnDuration: 30,
        fourColorMode: false,
        highContrastMode: false,
        cardLanguage: 'EN',
        strictMode: true,
        soundEnabled: true,
        gameSpeed: 'NORMAL'
    }
});


describe('Table Component', () => {
    let mockGameState: GameState;
    const mockOnPlayerAction = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        mockGameState = createGameState();
        // Give "Me" some cards
        mockGameState.players[0].hand = [
            { rank: Rank.Ace, suit: Suit.Hearts, id: 'Ah', value: 10 },
            { rank: Rank.King, suit: Suit.Spades, id: 'Ks', value: 4 }
        ];
    });

    it('renders loading state when players are missing', () => {
        // @ts-ignore
        render(<Table gameState={{ players: [] } as any} onPlayerAction={mockOnPlayerAction} />);
        expect(screen.getByText(/Loading Game Table/i)).toBeInTheDocument();
    });

    it('renders the game table with players properly', () => {
        render(<Table gameState={mockGameState} onPlayerAction={mockOnPlayerAction} />);

        // Check for player names
        expect(screen.getByText('Me')).toBeInTheDocument();
        expect(screen.getByText('Right')).toBeInTheDocument();
        // Partner name is hidden in UI, so we check the avatar alt text
        expect(screen.getByAltText('Partner')).toBeInTheDocument();
        expect(screen.getByText('Left')).toBeInTheDocument();
    });

    it('renders my hand cards', () => {
        render(<Table gameState={mockGameState} onPlayerAction={mockOnPlayerAction} />);

        // Based on our mock Card, we look for text content
        expect(screen.getByText('A♥')).toBeInTheDocument();
        expect(screen.getByText('K♠')).toBeInTheDocument();
    });

    it('allows selecting a card on first click', () => {
        render(<Table gameState={mockGameState} onPlayerAction={mockOnPlayerAction} />);

        const aceCard = screen.getByTestId('card-A-♥');

        // Click once to select
        fireEvent.click(aceCard);

        expect(mockOnPlayerAction).not.toHaveBeenCalled();
    });

    it('plays a card on second click (double click behavior)', () => {
        render(<Table gameState={mockGameState} onPlayerAction={mockOnPlayerAction} />);

        const aceCard = screen.getByTestId('card-A-♥');

        // First click: Select
        fireEvent.click(aceCard);

        // Second click: Play
        fireEvent.click(aceCard);

        expect(mockOnPlayerAction).toHaveBeenCalledWith('PLAY', { cardIndex: 0 });
    });

    it('prevents playing invalid card in strict mode', () => {
        // Setup: Table has a Spades card led.
        mockGameState.tableCards = [
            { card: { rank: Rank.Ten, suit: Suit.Spades, id: '10s', value: 10 }, playedBy: PlayerPosition.Left }
        ];
        // Me has Hearts and Spades. Must play Spades.
        mockGameState.players[0].hand = [
            { rank: Rank.Ace, suit: Suit.Hearts, id: 'Ah', value: 11 },
            { rank: Rank.King, suit: Suit.Spades, id: 'Ks', value: 4 }
        ];

        render(<Table gameState={mockGameState} onPlayerAction={mockOnPlayerAction} />);

        // Try to play Hearts (Invalid)
        const aceHearts = screen.getByTestId('card-A-♥');
        fireEvent.click(aceHearts); // Select
        fireEvent.click(aceHearts); // Try Play

        expect(mockOnPlayerAction).not.toHaveBeenCalled();

        // Try to play Spades (Valid)
        const kingSpades = screen.getByTestId('card-K-♠');
        fireEvent.click(kingSpades); // Select
        fireEvent.click(kingSpades); // Play

        expect(mockOnPlayerAction).toHaveBeenCalledWith('PLAY', { cardIndex: 1 });
    });
});
