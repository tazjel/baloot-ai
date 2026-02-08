# 🎯 The Big Split - Visual Architecture

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         useGameState                             │
│                      (Pure State Container)                      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Core State                                               │   │
│  │ - gameState, messages, userProfile                       │   │
│  │ - isCuttingDeck, isSendingAction, roomId, myIndex        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │ useGameSocket   │  │ useGameAudio    │  │ useLocalBot     ││
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤│
│  │ • sendAction    │  │ • speakAction   │  │ • isBotThinking ││
│  │ • addBot        │  │ • Auto sounds:  │  │ • Bot heartbeat ││
│  │ • onGameUpdate  │  │   - Card played │  │ • Decision loop ││
│  │ • onGameStart   │  │   - Trick won   │  │ • Validity check││
│  │ • isConnected   │  │   - Akka claim  │  │                 ││
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘│
│           │                    │                     │          │
└───────────┼────────────────────┼─────────────────────┼──────────┘
            │                    │                     │
            ▼                    ▼                     ▼
    ┌───────────────┐    ┌──────────────┐    ┌──────────────┐
    │ SocketService │    │ SoundManager │    │  botService  │
    └───────────────┘    └──────────────┘    └──────────────┘
```

## State Flow: Card Play Example

### Before (Monolithic)
```
User clicks card
    ↓
handlePlayerAction (in useGameState)
    ↓
if (roomId) → socketService.sendAction
    ↓
soundManager.playCardSound() ← Manual call
    ↓
setGameState (massive re-render)
    ↓
Bot effect triggers
    ↓
Audio effects trigger
    ↓
Everything re-renders
```

### After (Separated)
```
User clicks card
    ↓
handlePlayerAction (pure dispatch)
    ↓
socket.sendAction → useGameSocket (isolated)
    ↓
gameState updates (targeted re-render)
    ↓                           ↓                       ↓
useGameAudio detects      useLocalBot detects     UI re-renders
tableCards change         turn change              (minimal scope)
    ↓                           ↓
Plays sound               Bot decides next move
automatically             (offline only)
```

## Responsibility Matrix

| Concern              | Before           | After              |
|---------------------|------------------|--------------------|
| Socket I/O          | useGameState     | **useGameSocket**  |
| Sound effects       | useGameState     | **useGameAudio**   |
| Bot decisions       | useGameState     | **useLocalBot**    |
| State management    | useGameState     | useGameState       |
| Game logic          | useGameState     | useGameState       |

## File Size Comparison

```
useGameState.ts (before)
████████████████████████████████████████ 800+ lines

useGameSocket.ts
████████ 150 lines

useGameAudio.ts
█████ 90 lines

useLocalBot.ts
███████ 130 lines

useGameState.ts (after)
██████████████████████ 450 lines
```

## Hook Dependency Graph

```
┌─────────────────────────────────────────────────┐
│              Component Layer                     │
│  (Table.tsx, BiddingControls.tsx, etc.)         │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │  useGameState  │
            └────────┬───────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐┌──────────┐┌──────────┐
│useGameSocket ││useGameAu.││useLocalB.│
└──────┬───────┘└─────┬────┘└────┬─────┘
       │              │           │
       ▼              ▼           ▼
┌────────────┐  ┌──────────┐┌─────────┐
│socketServ. │  │soundMgr. ││botServ. │
└────────────┘  └──────────┘└─────────┘
```

## Testing Strategy

### Unit Testing (Now Possible!)

```typescript
// Test socket hook in isolation
describe('useGameSocket', () => {
  it('should send PLAY action', () => {
    const { result } = renderHook(() => useGameSocket({
      roomId: 'test-room',
      myIndex: 0,
      onGameUpdate: jest.fn(),
      onGameStart: jest.fn()
    }));
    
    result.current.sendAction('PLAY', { cardIndex: 2 });
    expect(mockSocketService.sendAction).toHaveBeenCalled();
  });
});

// Test audio hook in isolation
describe('useGameAudio', () => {
  it('should play sound when tableCards increases', () => {
    const { rerender } = renderHook(
      ({ gameState }) => useGameAudio({ gameState }),
      { initialProps: { gameState: { tableCards: [] } } }
    );
    
    rerender({ gameState: { tableCards: [card1] } });
    expect(mockSoundManager.playCardSound).toHaveBeenCalled();
  });
});

// Test bot hook in isolation
describe('useLocalBot', () => {
  it('should call onBotAction for bot turn', async () => {
    const onBotAction = jest.fn();
    renderHook(() => useLocalBot({
      gameState: { currentTurnIndex: 1, /* bot turn */ },
      roomId: null,
      isCuttingDeck: false,
      onBotAction
    }));
    
    await waitFor(() => {
      expect(onBotAction).toHaveBeenCalled();
    });
  });
});
```

## Migration Checklist

### Phase 1: Preparation
- [x] Create `useGameSocket.ts`
- [x] Create `useGameAudio.ts`
- [x] Create `useLocalBot.ts`
- [x] Create `useGameState.refactored.ts`
- [x] Write migration guide

### Phase 2: Testing
- [ ] Test socket hook with mock server
- [ ] Test audio hook with state changes
- [ ] Test bot hook in offline mode
- [ ] Integration test: Full game flow
- [ ] Performance test: Check re-render count

### Phase 3: Deployment
- [ ] Backup original `useGameState.ts`
- [ ] Rename `useGameState.refactored.ts` → `useGameState.ts`
- [ ] Test in production-like environment
- [ ] Monitor for regressions
- [ ] Remove backup after 1 week of stability

### Phase 4: Cleanup
- [ ] Add unit tests for each hook
- [ ] Document hook APIs
- [ ] Remove any duplicate sound calls
- [ ] Optimize dependency arrays
- [ ] Add TypeScript strict mode

## Performance Metrics

### Expected Improvements

| Metric                     | Before | After | Improvement |
|---------------------------|--------|-------|-------------|
| Re-renders per card play  | ~5-8   | ~2-3  | **60% ↓**   |
| Hook execution time (ms)  | 15-20  | 8-12  | **45% ↓**   |
| Lines of code (useGameS.) | 800+   | 450   | **44% ↓**   |
| Testability score         | 2/10   | 8/10  | **300% ↑**  |

### Measurement Tools
```typescript
// Add to useGameState for monitoring
useEffect(() => {
  const start = performance.now();
  return () => {
    const duration = performance.now() - start;
    console.log('useGameState render:', duration);
  };
});
```

## Future Enhancements

### Phase 5: Further Decomposition
```
useGameState (current ~450 lines)
    ↓
Could split into:
- useRoundManager (deal, round end)
- usePlayerActions (bid, play, double)
- useTrickResolver (trick completion)
- useScoreCalculator (accounting)
```

### Phase 6: State Management Library
Consider migrating to:
- Zustand (lightweight)
- Jotai (atomic state)
- Redux Toolkit (full featured)

Criteria: If hooks exceed 600 lines again, or state becomes too complex.

---

**Result:** Clean, maintainable, testable architecture ✨
