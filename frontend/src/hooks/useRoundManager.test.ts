import { describe, it, expect, vi, beforeEach, Mock } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRoundManager } from './useRoundManager';
import { GamePhase, GameState, PlayerPosition, DoublingLevel, Suit, Rank, CardModel } from '../types';
import { INITIAL_PLAYERS, AVATARS } from '../constants';
import { POINT_VALUES } from '../utils/gameLogic';
import React from 'react';

// ═══════════════════════════════════════════════════════════
// Helper: Create a minimal valid GameState
// ═══════════════════════════════════════════════════════════
const createCard = (suit: Suit, rank: Rank): CardModel => ({
    id: `${suit}-${rank}`,
    suit,
    rank,
    value: 0
});

const createInitialGameState = (overrides: Partial<GameState> = {}): GameState => ({
    players: INITIAL_PLAYERS.map((p, i) => ({
        position: [PlayerPosition.Bottom, PlayerPosition.Right, PlayerPosition.Top, PlayerPosition.Left][i],
        name: p.name,
        avatar: p.avatar || '🃏',
        hand: [],
        score: 0,
        isDealer: i === 3,
        isActive: i === 0,
        index: i,
        isBot: i !== 0,
    })),
    currentTurnIndex: 0,
    phase: GamePhase.Waiting,
    tableCards: [],
    bid: { type: null, suit: null, bidder: null, doubled: false },
    teamScores: { us: 0, them: 0 },
    matchScores: { us: 0, them: 0 },
    roundHistory: [],
    floorCard: null,
    deck: [],
    dealerIndex: 3,
    biddingRound: 1,
    declarations: {},
    doublingLevel: DoublingLevel.NORMAL,
    isLocked: false,
    settings: {
        turnDuration: 10,
        strictMode: false,
        soundEnabled: true,
        gameSpeed: 'NORMAL',
    },
    ...overrides
});

describe('useRoundManager', () => {
    let mockSetGameState: Mock & React.Dispatch<React.SetStateAction<GameState>>;
    let mockAddSystemMessage: Mock & ((text: string) => void);
    let mockPlayAkkaSound: Mock & (() => void);
    let initialState: GameState;

    beforeEach(() => {
        mockSetGameState = vi.fn() as Mock & React.Dispatch<React.SetStateAction<GameState>>;
        mockAddSystemMessage = vi.fn() as Mock & ((text: string) => void);
        mockPlayAkkaSound = vi.fn() as Mock & (() => void);
        initialState = createInitialGameState();
    });

    const renderTestHook = (stateOverrides: Partial<GameState> = {}) => {
        const state = createInitialGameState(stateOverrides);
        return renderHook(() =>
            useRoundManager({
                gameState: state,
                setGameState: mockSetGameState,
                addSystemMessage: mockAddSystemMessage,
                playAkkaSound: mockPlayAkkaSound,
            })
        );
    };

    // ═══════════════════════════════════════════════════════════
    // startNewRound
    // ═══════════════════════════════════════════════════════════
    describe('startNewRound', () => {
        it('should return startNewRound and completeTrick functions', () => {
            const { result } = renderTestHook();
            expect(result.current.startNewRound).toBeDefined();
            expect(typeof result.current.startNewRound).toBe('function');
            expect(result.current.completeTrick).toBeDefined();
            expect(typeof result.current.completeTrick).toBe('function');
        });

        it('should call setGameState when startNewRound is invoked', () => {
            const { result } = renderTestHook();

            act(() => {
                result.current.startNewRound(0);
            });

            expect(mockSetGameState).toHaveBeenCalled();
        });

        it('should add system messages on new round', () => {
            const { result } = renderTestHook();

            act(() => {
                result.current.startNewRound(0);
            });

            expect(mockAddSystemMessage).toHaveBeenCalledTimes(2);
            // First message: deck cut + dealer name
            expect(mockAddSystemMessage).toHaveBeenCalledWith(
                expect.stringContaining('الموزع')
            );
            // Second message: round started
            expect(mockAddSystemMessage).toHaveBeenCalledWith('بدأت الجولة');
        });

        it('should generate new state with Bidding phase via updater function', () => {
            const { result } = renderTestHook();

            act(() => {
                result.current.startNewRound(2);
            });

            // setGameState is called with an updater function
            const updater = mockSetGameState.mock.calls[0][0];
            expect(typeof updater).toBe('function');

            // Execute the updater with the initial state
            const newState = updater(initialState);

            expect(newState.phase).toBe(GamePhase.Bidding);
            expect(newState.dealerIndex).toBe(2);
            expect(newState.currentTurnIndex).toBe(3); // (2+1) % 4
            expect(newState.floorCard).toBeDefined();
            expect(newState.tableCards).toEqual([]);
            expect(newState.isLocked).toBe(false);
        });

        it('should deal 5 cards to each player', () => {
            const { result } = renderTestHook();

            act(() => {
                result.current.startNewRound(0);
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const newState = updater(initialState);

            newState.players.forEach((player: any) => {
                expect(player.hand.length).toBe(5);
            });
        });

        it('should mark the correct player as dealer', () => {
            const { result } = renderTestHook();

            act(() => {
                result.current.startNewRound(1);
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const newState = updater(initialState);

            expect(newState.players[0].isDealer).toBe(false);
            expect(newState.players[1].isDealer).toBe(true);
            expect(newState.players[2].isDealer).toBe(false);
            expect(newState.players[3].isDealer).toBe(false);
        });

        it('should set first turn to player after dealer', () => {
            const { result } = renderTestHook();

            // Test wraparound: dealer=3, first turn should be 0
            act(() => {
                result.current.startNewRound(3);
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const newState = updater(initialState);

            expect(newState.currentTurnIndex).toBe(0);
            expect(newState.players[0].isActive).toBe(true);
        });

        it('should pass match scores through', () => {
            const { result } = renderTestHook();

            const scores = { us: 44, them: 26 };
            act(() => {
                result.current.startNewRound(0, scores);
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const newState = updater(initialState);

            expect(newState.matchScores).toEqual(scores);
        });

        it('should reset bid and declarations', () => {
            const { result } = renderTestHook();

            act(() => {
                result.current.startNewRound(0);
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const newState = updater(initialState);

            expect(newState.bid).toEqual({ type: null, suit: null, bidder: null, doubled: false });
            expect(newState.declarations).toEqual({});
            expect(newState.doublingLevel).toBe(DoublingLevel.NORMAL);
        });
    });

    // ═══════════════════════════════════════════════════════════
    // completeTrick
    // ═══════════════════════════════════════════════════════════
    describe('completeTrick', () => {
        it('should be a no-op if table has fewer than 4 cards', () => {
            const { result } = renderTestHook({
                tableCards: [
                    { card: createCard(Suit.Hearts, Rank.Ace), playedBy: PlayerPosition.Bottom },
                ],
                phase: GamePhase.Playing,
            });

            act(() => {
                result.current.completeTrick();
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const state = createInitialGameState({
                tableCards: [
                    { card: createCard(Suit.Hearts, Rank.Ace), playedBy: PlayerPosition.Bottom },
                ],
                phase: GamePhase.Playing,
            });
            const newState = updater(state);

            expect(newState.isTrickTransitioning).toBe(false);
        });

        it('should clear table cards after a full trick', () => {
            const playingState = createInitialGameState({
                phase: GamePhase.Playing,
                bid: { type: 'SUN', suit: null, bidder: PlayerPosition.Bottom, doubled: false },
                tableCards: [
                    { card: createCard(Suit.Hearts, Rank.Ace), playedBy: PlayerPosition.Bottom },
                    { card: createCard(Suit.Hearts, Rank.Ten), playedBy: PlayerPosition.Right },
                    { card: createCard(Suit.Hearts, Rank.King), playedBy: PlayerPosition.Top },
                    { card: createCard(Suit.Hearts, Rank.Seven), playedBy: PlayerPosition.Left },
                ],
                players: INITIAL_PLAYERS.map((p, i) => ({
                    position: [PlayerPosition.Bottom, PlayerPosition.Right, PlayerPosition.Top, PlayerPosition.Left][i],
                    name: p.name,
                    avatar: p.avatar || '🃏',
                    hand: [createCard(Suit.Diamonds, Rank.Seven)], // 1 card left each
                    score: 0,
                    isDealer: i === 3,
                    isActive: false,
                    index: i,
                    isBot: i !== 0,
                })),
            });

            const { result } = renderTestHook(playingState);

            act(() => {
                result.current.completeTrick();
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const newState = updater(playingState);

            expect(newState.tableCards).toEqual([]);
        });

        it('should determine the correct trick winner in SUN mode', () => {
            const playingState = createInitialGameState({
                phase: GamePhase.Playing,
                bid: { type: 'SUN', suit: null, bidder: PlayerPosition.Bottom, doubled: false },
                tableCards: [
                    { card: createCard(Suit.Hearts, Rank.Seven), playedBy: PlayerPosition.Bottom },
                    { card: createCard(Suit.Hearts, Rank.Ace), playedBy: PlayerPosition.Right }, // Ace wins in SUN
                    { card: createCard(Suit.Hearts, Rank.King), playedBy: PlayerPosition.Top },
                    { card: createCard(Suit.Hearts, Rank.Queen), playedBy: PlayerPosition.Left },
                ],
                players: INITIAL_PLAYERS.map((p, i) => ({
                    position: [PlayerPosition.Bottom, PlayerPosition.Right, PlayerPosition.Top, PlayerPosition.Left][i],
                    name: p.name,
                    avatar: p.avatar || '🃏',
                    hand: [createCard(Suit.Diamonds, Rank.Seven), createCard(Suit.Clubs, Rank.Eight)],
                    score: 0,
                    isDealer: i === 3,
                    isActive: false,
                    index: i,
                    isBot: i !== 0,
                })),
            });

            const { result } = renderTestHook(playingState);

            act(() => {
                result.current.completeTrick();
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const newState = updater(playingState);

            // Right (index 1) played Ace → wins. Them team (1, 3).
            expect(newState.currentTurnIndex).toBe(1);
            // SUN Points: 7=0, A=11, K=4, Q=3 = 18 total.
            // Them wins (Right is 'them' team)
            expect(newState.teamScores.them).toBe(18);
        });

        it('should add 10 bonus points for last trick', () => {
            const playingState = createInitialGameState({
                phase: GamePhase.Playing,
                bid: { type: 'SUN', suit: null, bidder: PlayerPosition.Bottom, doubled: false },
                tableCards: [
                    { card: createCard(Suit.Hearts, Rank.Seven), playedBy: PlayerPosition.Bottom },
                    { card: createCard(Suit.Hearts, Rank.Eight), playedBy: PlayerPosition.Right },
                    { card: createCard(Suit.Hearts, Rank.Nine), playedBy: PlayerPosition.Top },
                    { card: createCard(Suit.Hearts, Rank.Queen), playedBy: PlayerPosition.Left }, // Q=3 in SUN
                ],
                players: INITIAL_PLAYERS.map((p, i) => ({
                    position: [PlayerPosition.Bottom, PlayerPosition.Right, PlayerPosition.Top, PlayerPosition.Left][i],
                    name: p.name,
                    avatar: p.avatar || '🃏',
                    hand: [], // Empty hands = last trick
                    score: 0,
                    isDealer: i === 3,
                    isActive: false,
                    index: i,
                    isBot: i !== 0,
                })),
            });

            const { result } = renderTestHook(playingState);

            act(() => {
                result.current.completeTrick();
            });

            const updater = mockSetGameState.mock.calls[0][0];
            const newState = updater(playingState);

            // SUN points: 7=0, 8=0, 9=0, Q=3. Raw=3. +10 last trick bonus = 13.
            // Total across both teams should include the 10-pt bonus
            const totalPoints = newState.teamScores.us + newState.teamScores.them;
            expect(totalPoints).toBe(13); // 3 card points + 10 last trick
        });
    });
});
