
import React, { useState, useEffect } from 'react';

import Table from './components/Table';
import ClassicBoard from './components/classic/ClassicBoard';
import Lobby from './components/Lobby';
import socketService from './services/SocketService';
import { GameState, GamePhase, PlayerPosition, Suit, RoundResult, BotDifficulty } from './types';

import SettingsModal from './components/SettingsModal';
import VictoryModal from './components/VictoryModal';
import LevelUpModal from './components/LevelUpModal';
import StoreModal from './components/StoreModal';
import EmoteMenu from './components/EmoteMenu';
import RoundResultsModal from './components/RoundResultsModal';
import MatchReviewModal from './components/MatchReviewModal'; 
import VariantSelectionModal from './components/VariantSelectionModal'; 
import { Settings, ShoppingBag, Smile } from 'lucide-react';
import MultiplayerLobby from './components/MultiplayerLobby';

import GameLayout from './components/GameLayout';
import { useGameContext } from './contexts/GameContext';
import { soundManager } from './services/SoundManager';
import { getInvalidMoveReason } from './utils/gameLogic';
import ErrorBoundary from './components/ErrorBoundary';
import FeatureErrorBoundary from './components/FeatureErrorBoundary';
import ConnectionBanner from './components/ConnectionBanner';
import { devLogger } from './utils/devLogger';

import { useEmotes } from './hooks/useEmotes';
import { useShop } from './hooks/useShop';


const App: React.FC = () => {
  // ... existing hook calls ...
  useEffect(() => {
    devLogger.log('APP', 'App Component Mounted');
  }, []);
  // Phase VII: Connect logger to socket for remote telemetry
  useEffect(() => {
    if (socketService.socket) {
      devLogger.setSocket(socketService.socket);
      devLogger.log('APP', 'Telemetry Connected');
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
  } = useGameContext();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false); // Settings UI
  const [levelUpData, setLevelUpData] = useState<{ newLevel: number, rewards: { coins: number } } | null>(null);

  // Extracted hooks
  const {
    isStoreOpen,
    setIsStoreOpen,
    ownedItems,
    equippedItems,
    handlePurchaseWrapper,
    handleEquip
  } = useShop(userProfile, handlePurchase);

  const {
    isEmoteMenuOpen,
    setIsEmoteMenuOpen,
    flyingItems,
    handleSendEmote,
    handleThrowItem,
    toggleEmoteMenu
  } = useEmotes(gameState, addSystemMessage);


  // Round Results Modal - Standard Style
  const [roundResultToShow, setRoundResultToShow] = useState<RoundResult | null>(null);
  const [lastSeenRoundCount, setLastSeenRoundCount] = useState(0);
  const [showReviewModal, setShowReviewModal] = useState(false); // Added state

  // M18: Theme class effect
  useEffect(() => {
    const theme = gameState.settings.theme || 'auto';
    const html = document.documentElement;
    html.classList.remove('dark', 'light');
    if (theme === 'dark') html.classList.add('dark');
    else if (theme === 'light') html.classList.add('light');
    // 'auto' = no class = OS preference via @media query
  }, [gameState.settings.theme]);

  // M18: Animation toggle effect
  useEffect(() => {
    const html = document.documentElement;
    if (gameState.settings.animationsEnabled === false) {
      html.classList.add('reduce-motion');
    } else {
      html.classList.remove('reduce-motion');
    }
  }, [gameState.settings.animationsEnabled]);

  // M18: Volume sync effect
  useEffect(() => {
    const vols = gameState.settings.soundVolumes;
    if (vols) {
      soundManager.setVolume('cards', vols.cards ?? 1);
      soundManager.setVolume('ui', vols.ui ?? 1);
      soundManager.setVolume('events', vols.events ?? 1);
      soundManager.setVolume('bids', vols.bids ?? 1);
    }
  }, [gameState.settings.soundVolumes]);

  const handleChallenge = () => {
    // Legacy Dispute Modal - Deprecated
    // setIsDisputeModalOpen(true);
  };

  // --- CONTENT RENDER ---
  const [currentView, setCurrentView] = useState<'LOBBY' | 'GAME' | 'MULTIPLAYER_LOBBY'>('LOBBY');
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
          devLogger.log('LOBBY', 'Start Game Clicked', settings);

          handleDebugAction('TOGGLE_DEBUG', { enable: settings.isDebug });

          try {
            soundManager.playShuffleSound();
          } catch (e) {
            devLogger.error('LOBBY', 'Sound play failed (interaction policy?)', e);
          }

          // UNIFICATION: Use Python Backend for Single Player too
          gameState.settings = settings;
          addSystemMessage("Connecting to Game Server...");

          socketService.connect();

          // 1. Create Room (Hidden)
          socketService.createRoom((res) => {
            devLogger.log('LOBBY', 'Create Room Response', res);

            if (res.success) {
              const rid = res.roomId as string;
              // 2. Join as Me
              const myName = userProfile.firstName || 'Me';
              const difficulty = settings.botDifficulty || 'HARD';
              socketService.activeBotDifficulty = difficulty;

              socketService.joinRoom(rid, myName, (joinRes) => {
                devLogger.log('LOBBY', 'Join Room Response', joinRes);

                if (joinRes.success) {
                  try {
                    devLogger.log('LOBBY', 'Joining game with state', joinRes.gameState);
                    joinGame(rid, joinRes.yourIndex as number, joinRes.gameState as GameState);
                    updateSettings(settings);
                    setCurrentView('GAME');


                    devLogger.log('LOBBY', 'Transitioning to GAME view');

                  } catch (e) {
                    devLogger.error('LOBBY', 'Join Exception', { error: String(e) });
                    setErrorObj("Join Error: " + String(e));
                  }
                } else {
                  setErrorObj("Failed to join single player room: " + joinRes.error);
                  devLogger.error('LOBBY', 'Join Room Failed', joinRes);
                }
              });
            } else {
              setErrorObj("Failed to create single player room: " + res.error);
              devLogger.error('LOBBY', 'Create Room Failed', res);
            }
          });
        }}
        onMultiplayer={() => setCurrentView('MULTIPLAYER_LOBBY')}
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
          <FeatureErrorBoundary featureName="الطاولة">
          {equippedItems.table === 'table_classic' ? (
            <ClassicBoard
              gameState={gameState}
              onPlayerAction={handlePlayerAction}
              onChallenge={handleChallenge}
              onAddBot={addBot}
              onDebugAction={handleDebugAction}
              isCuttingDeck={isCuttingDeck}
              tableSkin={equippedItems.table}
              cardSkin={equippedItems.card}
              onFastForward={handleFastForward}
              onEmoteClick={toggleEmoteMenu}
              isSendingAction={isSendingAction}
            />
          ) : (
            <Table
              gameState={gameState}
              onPlayerAction={handlePlayerAction}
              onChallenge={handleChallenge}
              onAddBot={addBot}
              onDebugAction={handleDebugAction}
              isCuttingDeck={isCuttingDeck}
              tableSkin={equippedItems.table}
              cardSkin={equippedItems.card}
              onFastForward={handleFastForward}
              onEmoteClick={toggleEmoteMenu}
              isSendingAction={isSendingAction}
            />
          )}
          </FeatureErrorBoundary>


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

        <FeatureErrorBoundary featureName="المتجر">
        {isStoreOpen && <StoreModal userProfile={userProfile} onClose={() => setIsStoreOpen(false)} onPurchase={handlePurchaseWrapper} onEquip={handleEquip} ownedItems={ownedItems} equippedItems={equippedItems} />}
        </FeatureErrorBoundary>

        <FeatureErrorBoundary featureName="الإعدادات">
        {isSettingsOpen && <SettingsModal
          settings={gameState.settings}
          equippedItems={equippedItems}
          onUpdate={(s) => updateSettings(s)}
          onEquip={handleEquip}
          onClose={() => setIsSettingsOpen(false)}
        />}
        </FeatureErrorBoundary>
        <FeatureErrorBoundary featureName="الترقية">
        {levelUpData && <LevelUpModal newLevel={levelUpData.newLevel} rewards={levelUpData.rewards} onClose={() => setLevelUpData(null)} />}
        </FeatureErrorBoundary>
        <FeatureErrorBoundary featureName="النتيجة">
        {gameState.phase === GamePhase.GameOver && <VictoryModal scores={gameState.matchScores} onHome={() => { setCurrentView('LOBBY'); startNewRound(); }} onRematch={() => startNewRound()} onReview={() => setShowReviewModal(true)} />}
        </FeatureErrorBoundary>

        {/* Match Review Modal */}
        <FeatureErrorBoundary featureName="مراجعة المباراة">
        <MatchReviewModal
          isOpen={showReviewModal}
          onClose={() => setShowReviewModal(false)}
          fullMatchHistory={gameState.fullMatchHistory || []}
          players={gameState.players}
        />
        </FeatureErrorBoundary>

        {/* Variant Selection Modal (Open/Closed) */}
        <FeatureErrorBoundary featureName="اختيار النوع">
        <VariantSelectionModal
          phase={gameState.phase}
          isMyTurn={gameState.players.find(p => p.position === PlayerPosition.Bottom)?.isActive || false}
          onSelect={(variant) => handlePlayerAction('VARIANT_SELECTED', { variant })}
        />
        </FeatureErrorBoundary>


        {/* Round Results Modal */}
        <FeatureErrorBoundary featureName="نتائج الجولة">
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
        </FeatureErrorBoundary>


      </div>
    );
  }

  return (
    <GameLayout variant='mobile'>
      <ConnectionBanner />
      <ErrorBoundary>
        {content}
      </ErrorBoundary>
    </GameLayout>
  );
}

export default App;
