
import React, { useState, useEffect } from 'react';

import Table from './components/Table';
import Lobby from './components/Lobby';
import socketService from './services/SocketService';
import { ProfessorOverlay } from './components/overlays/ProfessorOverlay';
import { GameState, GamePhase, PlayerPosition, Suit, RoundResult, ProfessorIntervention } from './types';

import SettingsModal from './components/SettingsModal';
import VictoryModal from './components/VictoryModal';
import LevelUpModal from './components/LevelUpModal';
import StoreModal from './components/StoreModal';
import EmoteMenu from './components/EmoteMenu';
import RoundResultsModal from './components/RoundResultsModal';
import MatchReviewModal from './components/MatchReviewModal'; // Added
import VariantSelectionModal from './components/VariantSelectionModal'; // Added
import { Settings, ShoppingBag, Smile } from 'lucide-react';
import MultiplayerLobby from './components/MultiplayerLobby';
import { AIAnalysisPanel } from './components/AIAnalysisPanel';
import GameLayout from './components/GameLayout';
import AIStudio from './components/AIStudio'; // Added
import { VisionaryStudio } from './components/VisionaryStudio';

import { useGameState } from './hooks/useGameState';
import { soundManager } from './services/SoundManager';
import { getInvalidMoveReason } from './utils/gameLogic';
import ErrorBoundary from './components/ErrorBoundary';
import { submitTrainingData } from './services/trainingService';
import AcademyPage from './pages/AcademyPage';
import PuzzleArena from './components/Academy/PuzzleArena';
import ReplayPage from './pages/ReplayPage';


const App: React.FC = () => {
  // ... existing hook calls ...
  useEffect(() => {
    // @ts-ignore
    import('./utils/devLogger').then(({ devLogger }) => devLogger.log('APP', 'App Component Mounted'));
  }, []);
  // Phase VII: Connect logger to socket for remote telemetry
  useEffect(() => {
    if (socketService.socket) {
      // @ts-ignore
      import('./utils/devLogger').then(({ devLogger }) => {
        devLogger.setSocket(socketService.socket);
        devLogger.log('APP', 'Telemetry Connected');
      });
    }
  }, [socketService.socket]);

  const {
    gameState,
    messages,
    userProfile,
    setUserProfile,
    isCuttingDeck,
    handlePlayerAction,
    handleDebugAction,
    handlePurchase,
    startNewRound,
    joinGame,
    addSystemMessage,
    addBot,
    handleFastForward, // Phase V
    roomId, // Phase VII
    updateSettings,
    isSendingAction // Added
  } = useGameState();

  const [isStoreOpen, setIsStoreOpen] = useState(false);
  const [isEmoteMenuOpen, setIsEmoteMenuOpen] = useState(false);
  const [flyingItems, setFlyingItems] = useState<{ id: string, type: string, startX: number, startY: number, endX: number, endY: number }[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false); // Settings UI
  const [showMindMap, setShowMindMap] = useState(false); // Mind Map State (Lifted)
  const [levelUpData, setLevelUpData] = useState<{ newLevel: number, rewards: { coins: number } } | null>(null);



  // Round Results Modal - Standard Style
  const [roundResultToShow, setRoundResultToShow] = useState<RoundResult | null>(null);
  const [lastSeenRoundCount, setLastSeenRoundCount] = useState(0);
  const [showReviewModal, setShowReviewModal] = useState(false); // Added state

  // Item Persistence (UI)
  const [ownedItems, setOwnedItems] = useState<string[]>(() => {
    const saved = localStorage.getItem('baloot_owned_items');
    return saved ? JSON.parse(saved) : ['card_default', 'table_default'];
  });
  const [equippedItems, setEquippedItems] = useState<{ card: string, table: string }>(() => {
    const saved = localStorage.getItem('baloot_equipped_items');
    return saved ? JSON.parse(saved) : { card: 'card_default', table: 'table_default' };
  });

  // Reporting Logic (AI Training)
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportReason, setReportReason] = useState("");
  const [reportCorrectMove, setReportCorrectMove] = useState("");

  // Professor Mode State
  const [profIntervention, setProfIntervention] = useState<ProfessorIntervention | null>(null);
  const [pendingPlay, setPendingPlay] = useState<{ cardIndex: number, metadata?: any } | null>(null);

  useEffect(() => {
    localStorage.setItem('baloot_owned_items', JSON.stringify(ownedItems));
    localStorage.setItem('baloot_equipped_items', JSON.stringify(equippedItems));
  }, [ownedItems, equippedItems]);

  const handlePurchaseWrapper = (itemId: string, cost: number) => {
    if (userProfile.coins >= cost) {
      handlePurchase(itemId, cost);
      setOwnedItems(prev => [...prev, itemId]);
    }
  };

  const handleEquip = (itemId: string, type: 'card' | 'table') => setEquippedItems(prev => ({ ...prev, [type]: itemId }));

  // --- EMOTES & FX ---
  const handleSendEmote = (msg: string) => {
    addSystemMessage(`أنا: ${msg} `);
    setIsEmoteMenuOpen(false);
  };

  const handleThrowItem = (itemId: string) => {
    setIsEmoteMenuOpen(false);
    // Target logic: 0=Me, 1=Right, 2=Top, 3=Left (relative to view)
    // currentTurnIndex is rotated in hook, so it matches visual position relative to "Me" at 0.
    const targetIdx = gameState.currentTurnIndex === 0 ? 3 : gameState.currentTurnIndex;
    let endX = 50, endY = 50;
    switch (targetIdx) {
      case 1: endX = 85; endY = 50; break;
      case 2: endX = 50; endY = 15; break;
      case 3: endX = 15; endY = 50; break;
    }
    const newItem = { id: Date.now().toString(), type: itemId, startX: 50, startY: 90, endX, endY };
    setFlyingItems(prev => [...prev, newItem]);
    soundManager.playShuffleSound();
    setTimeout(() => setFlyingItems(prev => prev.filter(i => i.id !== newItem.id)), 1000);
  };

  const handleChallenge = () => {
    // Legacy Dispute Modal - Deprecated
    // setIsDisputeModalOpen(true);
  };

  // --- PROFESSOR MODE HANDLERS ---
  const handleProfUndo = () => {
    setProfIntervention(null);
    setPendingPlay(null);
  };

  const handleProfContinue = () => {
    if (pendingPlay) {
      // Retry with skip flag
      // We use the original handler but append skip_professor to payload
      // Note: App doesn't modify payload deep usually, but let's do it right.
      const newPayload = { ...pendingPlay, skip_professor: true };
      if (roomId) {
        // Determine card index again? No, it's in payload
        socketService.sendAction(roomId, 'PLAY', newPayload);
      } else {
        handlePlayerAction('PLAY', newPayload);
      }
    }
    setProfIntervention(null);
    setPendingPlay(null);
  };

  const handlePlayerActionWithProfessor = (action: string, payload: any) => {
    // Intercept PLAY if connected to server
    if (action === 'PLAY' && roomId && !payload?.skip_professor && !userProfile.disableProfessor) {
      // We initiate the action via SocketService manually to catch the 200 OK w/ Error Code
      // Actually, 'sendAction' callback receives the response.

      // We must bypass handlePlayerAction's internal sends to avoid double send if we want custom error handling.
      // However, handlePlayerAction ALSO blocks duplicates.

      // Let's call socketService directly.
      socketService.sendAction(roomId, 'PLAY', payload, (res) => {
        if (!res.success && res.error === 'PROFESSOR_INTERVENTION') {
          setProfIntervention(res.intervention);
          setPendingPlay(payload); // Contains cardIndex and metadata
        } else if (!res.success) {
          addSystemMessage(`Action Failed: ${res.error}`);
        }
      });
      return;
    }

    // Default
    handlePlayerAction(action, payload);
  };



  // --- CONTENT RENDER ---
  const [currentView, setCurrentView] = useState<'LOBBY' | 'GAME' | 'MULTIPLAYER_LOBBY' | 'AI_STUDIO' | 'PUZZLE_LIST' | 'PUZZLE_BOARD' | 'REPLAY' | 'VISIONARY'>('LOBBY');
  const [selectedPuzzleId, setSelectedPuzzleId] = useState<string | null>(null);
  const [replayGameId, setReplayGameId] = useState<string | null>(null);
  const [errorObj, setErrorObj] = useState<string | null>(null);

  // Global Error Handler
  useEffect(() => {
    const errorHandler = (event: ErrorEvent) => setErrorObj(`${event.message} \n ${event.filename} : ${event.lineno} `);
    window.addEventListener('error', errorHandler);
    return () => window.removeEventListener('error', errorHandler);
  }, []);

  // Show Round Results Modal when a new round completes
  useEffect(() => {
    const currentRoundCount = gameState.roundHistory.length;
    if (currentRoundCount > lastSeenRoundCount && currentRoundCount > 0) {
      // A new round just completed - show the results
      const latestResult = gameState.roundHistory[currentRoundCount - 1];
      setRoundResultToShow(latestResult);
      setLastSeenRoundCount(currentRoundCount);
      soundManager.playProjectSound(); // Celebratory sound

      // Check if it was a QAYD result
      // Backend doesn't explicitly flag "isQayd" in roundHistory structure usually,
      // but we can infer or use latestResult if weird scores (0 vs Max).
      // Or better: Listen to system message or check if qaydPenalty exists in state.
    }
  }, [gameState.roundHistory.length, lastSeenRoundCount]);



  if (errorObj) {
    return (
      <div className="fixed inset-0 z-[9999] bg-red-900 text-white p-10 flex flex-col items-center justify-center font-mono text-lg overflow-auto">
        <h1 className="text-4xl font-bold mb-4">GAME CRASHED</h1>
        <pre className="bg-black p-4 rounded border border-red-500 max-w-4xl whitespace-pre-wrap">{errorObj}</pre>
        <button onClick={() => window.location.reload()} className="mt-8 bg-white text-red-900 px-6 py-3 rounded-full font-bold">Reload Game</button>
      </div>
    );
  }

  let content;

  if (currentView === 'LOBBY') {
    content = (
      <Lobby
        onStartGame={(settings) => {
          console.log("App: onStartGame triggered");
          import('./utils/devLogger').then(({ devLogger }) => devLogger.log('LOBBY', 'Start Game Clicked', settings));

          handleDebugAction('TOGGLE_DEBUG', { enable: settings.isDebug });

          try {
            soundManager.playShuffleSound();
          } catch (e) {
            console.warn("Sound play failed (interaction policy?):", e);
          }

          // UNIFICATION: Use Python Backend for Single Player too
          gameState.settings = settings;
          addSystemMessage("Connecting to Game Server...");

          socketService.connect();

          // 1. Create Room (Hidden)
          socketService.createRoom((res) => {
            import('./utils/devLogger').then(({ devLogger }) => devLogger.log('LOBBY', 'Create Room Response', res));

            if (res.success) {
              const rid = res.roomId as string;
              // 2. Join as Me
              const myName = userProfile.firstName || 'Me';

              socketService.joinRoom(rid, myName, (joinRes) => {
                import('./utils/devLogger').then(({ devLogger }) => devLogger.log('LOBBY', 'Join Room Response', joinRes));

                if (joinRes.success) {
                  try {
                    console.log("Joining game with state:", joinRes.gameState);
                    joinGame(rid, joinRes.yourIndex as number, joinRes.gameState as GameState);
                    updateSettings(settings);
                    setCurrentView('GAME');

                    import('./utils/devLogger').then(({ devLogger }) => devLogger.log('LOBBY', 'Transitioning to GAME view'));

                  } catch (e) {
                    console.error("Join Game Error:", e);
                    setErrorObj("Join Error: " + e);
                    import('./utils/devLogger').then(({ devLogger }) => devLogger.error('LOBBY', 'Join Exception', { error: e.toString() }));
                  }

                  // 3. Add Bots - HANDLED BY SERVER AUTOMATICALLY
                  // (See socket_handler.py:join_room which adds 3 bots for first player)
                } else {
                  setErrorObj("Failed to join single player room: " + joinRes.error);
                  import('./utils/devLogger').then(({ devLogger }) => devLogger.error('LOBBY', 'Join Room Failed', joinRes));
                }
              });
            } else {
              setErrorObj("Failed to create single player room: " + res.error);
              import('./utils/devLogger').then(({ devLogger }) => devLogger.error('LOBBY', 'Create Room Failed', res));
            }
          });
        }}
        onMultiplayer={() => setCurrentView('MULTIPLAYER_LOBBY')}
        onAIStudio={() => setCurrentView('AI_STUDIO')}
        onAIClassroom={() => setCurrentView('PUZZLE_LIST')}
        onReplay={() => {
          setReplayGameId(""); // Start empty to show list
          setCurrentView('REPLAY');
        }}
        onVisionary={() => setCurrentView('VISIONARY')}
      />
    );
  } else if (currentView === 'VISIONARY') {
    content = <VisionaryStudio onBack={() => setCurrentView('LOBBY')} />;
  } else if (currentView === 'REPLAY') {
    content = (
      <ReplayPage
        gameId={replayGameId || ""}
        onBack={() => setCurrentView('LOBBY')}
        onFork={(newId) => {
          // Debugging user report: "Fork not working"
          // Force ensure socket is connected
          if (!socketService.socket || !socketService.socket.connected) {
            socketService.connect();
            // Wait a tiny bit? Or assume connect() is fast/async?
            // We'll proceed, but if it fails, the callback will catch it.
          }

          // Join the forked game as a player
          const myName = userProfile.firstName || 'Me';

          import('./utils/devLogger').then(({ devLogger }) => devLogger.log('REPLAY', 'Fork Attempt Start', { newId }));

          socketService.joinRoom(newId, myName, (joinRes) => {
            if (joinRes.success) {
              joinGame(newId, joinRes.yourIndex as number, joinRes.gameState as GameState);
              setCurrentView('GAME');
              import('./utils/devLogger').then(({ devLogger }) => devLogger.log('REPLAY', 'Fork Joined Successfully', joinRes));
            } else {
              const msg = "Failed to join forked game: " + joinRes.error;
              setErrorObj(msg);
              alert(msg); // Force user visibility
              import('./utils/devLogger').then(({ devLogger }) => devLogger.log('REPLAY', 'Fork Join Error', joinRes));
            }
          });
        }}
        onLoadReplay={(id) => setReplayGameId(id)}
      />
    );

  } else if (currentView === 'AI_STUDIO') {
    content = <AIStudio onBack={() => setCurrentView('LOBBY')} />;
  } else if (currentView === 'PUZZLE_LIST') {
    content = (
      <AcademyPage
        onSelectPuzzle={(id) => {
          setSelectedPuzzleId(id);
          setCurrentView('PUZZLE_BOARD');
        }}
        onBack={() => setCurrentView('LOBBY')}
      />
    );
  } else if (currentView === 'PUZZLE_BOARD') {
    content = (
      <PuzzleArena
        id={selectedPuzzleId || ""}
        onBack={() => setCurrentView('PUZZLE_LIST')}
      />
    );
  } else if (currentView === 'MULTIPLAYER_LOBBY') {
    content = (
      <MultiplayerLobby
        onBack={() => setCurrentView('LOBBY')}
        onGameStart={(init, idx, rid) => {
          joinGame(rid, idx, init);
          setCurrentView('GAME');
        }}
      />
    );
  } else {
    // GAME VIEW
    content = (
      <div className="flex h-full w-full overflow-hidden bg-black font-tajawal text-white relative" dir="rtl">
        <div className="flex-1 relative bg-black shadow-[inset_0_0_100px_rgba(0,0,0,0.8)] h-full">
          <Table
            gameState={gameState}
            onPlayerAction={handlePlayerActionWithProfessor}
            onChallenge={handleChallenge}
            onAddBot={addBot}
            onDebugAction={handleDebugAction}
            isCuttingDeck={isCuttingDeck}
            tableSkin={equippedItems.table}
            cardSkin={equippedItems.card}
            onFastForward={handleFastForward}
            onEmoteClick={() => setIsEmoteMenuOpen(!isEmoteMenuOpen)}
            isSendingAction={isSendingAction}
            isPaused={!!profIntervention}
            // Mind Map Props (Lifted)
            showMindMap={showMindMap}
            setShowMindMap={setShowMindMap}
          />

          {/* AI Report Button (Only visible if game is active) */}
          {gameState.phase === GamePhase.Playing && (
            <button
              onClick={() => setIsReportModalOpen(true)}
              className="absolute top-20 left-4 z-50 bg-red-500/80 hover:bg-red-600 text-white p-2 rounded-full shadow-lg transition-all"
              title="Report Bad Bot Move"
            >
              ⚠️
            </button>
          )}

          {/* Report Modal */}
          {isReportModalOpen && (
            <div className="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-4">
              <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md text-right border border-slate-700" dir="rtl">
                <h2 className="text-xl font-bold text-yellow-500 mb-4">تصحيح حركة البوت</h2>

                <div className="mb-4">
                  <label className="block text-slate-300 mb-2">الحركة الصحيحة</label>
                  <input
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                    placeholder="مثال: A S"
                    value={reportCorrectMove}
                    onChange={e => setReportCorrectMove(e.target.value)}
                  />
                </div>

                <div className="mb-6">
                  <label className="block text-slate-300 mb-2">السبب</label>
                  <textarea
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white h-24"
                    placeholder="لماذا كان قرار البوت خاطئاً؟"
                    value={reportReason}
                    onChange={e => setReportReason(e.target.value)}
                  />
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setIsReportModalOpen(false)}
                    className="px-4 py-2 text-slate-400 hover:text-white"
                  >
                    إلغاء
                  </button>
                  <button
                    onClick={async () => {
                      await submitTrainingData({
                        contextHash: `live - ${Date.now()} `,
                        gameState: JSON.stringify(gameState), // Capture current state
                        badMove: "Unknown (User Reported)", // Ideally track last move
                        correctMove: reportCorrectMove,
                        reason: reportReason
                      });
                      addSystemMessage("شكراً! تم حفظ التصحيح.");
                      setIsReportModalOpen(false);
                      setReportReason("");
                      setReportCorrectMove("");
                    }}
                    className="px-6 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg font-bold"
                  >
                    حفظ
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>




        {/* Settings Button */}
        <button
          onClick={() => setIsSettingsOpen(true)}
          className="absolute top-4 right-4 z-[60] bg-black/40 hover:bg-black/60 p-2 rounded-full text-white/50 hover:text-white transition-all backdrop-blur-sm border border-white/10"
        >
          <Settings size={20} />
        </button>

        {/* Settings and Store buttons removed per user request - RESTORED SETTINGS */}

        {/* Emote Menu (rendered by ActionBar button click) */}
        {isEmoteMenuOpen && gameState.phase === GamePhase.Playing && (
          <div className="absolute bottom-28 left-1/2 -translate-x-1/2 z-[150]">
            <EmoteMenu onSelectEmote={handleSendEmote} onSelectThrowable={handleThrowItem} onClose={() => setIsEmoteMenuOpen(false)} />
          </div>
        )}

        {flyingItems.map(item => (
          <div key={item.id} className="fixed z-[9999] pointer-events-none text-4xl animate-fly-throwable" style={{ left: `${item.startX}% `, top: `${item.startY}% `, '--end-x': `${item.endX}% `, '--end-y': `${item.endY}% ` } as React.CSSProperties & { [key: string]: string | number }}>
            {item.type === 'slipper' ? '🩴' : item.type === 'tomato' ? '🍅' : item.type === 'flower' ? '🌹' : '🥚'}
          </div>
        ))}

        {isStoreOpen && <StoreModal userProfile={userProfile} onClose={() => setIsStoreOpen(false)} onPurchase={handlePurchaseWrapper} onEquip={handleEquip} ownedItems={ownedItems} equippedItems={equippedItems} />}

        {profIntervention && <ProfessorOverlay intervention={profIntervention} onUndo={handleProfUndo} onInsist={handleProfContinue} />}
        {isSettingsOpen && <SettingsModal
          settings={gameState.settings}
          equippedItems={equippedItems}
          onUpdate={(s) => updateSettings(s)}
          onEquip={handleEquip}
          onClose={() => setIsSettingsOpen(false)}
        />}
        {levelUpData && <LevelUpModal newLevel={levelUpData.newLevel} rewards={levelUpData.rewards} onClose={() => setLevelUpData(null)} />}
        {gameState.phase === GamePhase.GameOver && <VictoryModal scores={gameState.matchScores} onHome={() => { setCurrentView('LOBBY'); startNewRound(); }} onRematch={() => startNewRound()} onReview={() => setShowReviewModal(true)} />}

        {/* Match Review Modal */}
        <MatchReviewModal
          isOpen={showReviewModal}
          onClose={() => setShowReviewModal(false)}
          fullMatchHistory={gameState.fullMatchHistory || []}
          players={gameState.players}
        />

        {/* Variant Selection Modal (Open/Closed) */}
        <VariantSelectionModal
          phase={gameState.phase}
          isMyTurn={gameState.players.find(p => p.position === PlayerPosition.Bottom)?.isActive || false}
          onSelect={(variant) => handlePlayerAction('VARIANT_SELECTED', { variant })}
        />


        {/* Round Results Modal */}
        <RoundResultsModal
          result={roundResultToShow}
          bidderTeam={gameState.bid?.bidder === PlayerPosition.Bottom || gameState.bid?.bidder === PlayerPosition.Top ? 'us' : gameState.bid?.bidder ? 'them' : null}
          bidType={gameState.bid?.type || null}

          isOpen={!!roundResultToShow}
          onClose={() => {
            setRoundResultToShow(null);
            // Trigger next round (Backend expects this now)
            handlePlayerAction('NEXT_ROUND', {});
          }}
          onReview={() => setShowReviewModal(true)}
        />

        {/* New Left-Side Analysis Panel */}
        <AIAnalysisPanel
          players={gameState.players}
          gameId={gameState.gameId}
          onOpenMindMap={() => setShowMindMap(true)}
        />
      </div>
    );
  }

  const isStudioMode = currentView === 'AI_STUDIO' || currentView === 'VISIONARY';

  return (
    <GameLayout variant={isStudioMode ? 'studio' : 'mobile'}>
      <ErrorBoundary>
        {content}
      </ErrorBoundary>
    </GameLayout>
  );
}

export default App;
