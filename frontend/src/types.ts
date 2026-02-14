export enum Suit {
  Hearts = '♥',
  Diamonds = '♦',
  Clubs = '♣',
  Spades = '♠'
}

export enum Rank {
  Seven = '7',
  Eight = '8',
  Nine = '9',
  Ten = '10',
  Jack = 'J',
  Queen = 'Q',
  King = 'K',
  Ace = 'A'
}

export interface CardModel {
  id: string;
  suit: Suit;
  rank: Rank;
  value: number; // Raw value for sorting
}

export enum GamePhase {
  Waiting = 'WAITING',
  Bidding = 'BIDDING',
  Doubling = 'DOUBLING',
  VariantSelection = 'VARIANT_SELECTION', // Open/Closed choice
  Playing = 'PLAYING',
  GameOver = 'GAMEOVER'
}

export enum PlayerPosition {
  Bottom = 'Bottom',
  Right = 'Right',
  Top = 'Top',
  Left = 'Left'
}

export interface Player {
  position: PlayerPosition;
  name: string;
  avatar: string; // URL or emoji
  hand: CardModel[];
  score: number; // Cards won or points
  isDealer: boolean;
  isActive: boolean; // Is it their turn?
  actionText?: string; // e.g. "Pass", "Sun" displayed briefly
  lastReasoning?: string; // AI Reasoning text
  index: number; // Player index (0-3)
  isBot?: boolean; // Added for AI identification

}

export interface Bid {
  type: 'SUN' | 'HOKUM' | null;
  suit: Suit | null; // NEW: Explicitly store suit
  bidder: PlayerPosition | null;
  doubled: boolean;
}

export interface TableCardMetadata {
  akka?: boolean;
  [key: string]: unknown;
}

export type BotDifficulty = 'EASY' | 'MEDIUM' | 'HARD' | 'KHALID';

export interface GameSettings {
  turnDuration: number; // Seconds (e.g. 5, 10, 15)
  strictMode: boolean; // True = Auto-block illegal moves, False = Allow illegal + Disputes
  soundEnabled: boolean;
  gameSpeed: 'NORMAL' | 'FAST';
  botDifficulty?: BotDifficulty; // Bot AI difficulty level
  isDebug?: boolean;
  fourColorMode?: boolean; // NEW: Accessibility
  highContrastMode?: boolean; // NEW: Accessibility
  cardLanguage?: 'EN' | 'AR'; // NEW: Arabic/English Indices
  theme?: 'auto' | 'light' | 'dark'; // M18: Theme preference
  animationsEnabled?: boolean; // M18: Toggle animations
  soundVolumes?: { cards: number; ui: number; events: number; bids: number }; // M18: Per-category volume (0-1)
}

export interface DetailedScore {
  aklat: number;
  ardh: number;
  mashaari: number;
  abnat: number;
  result: number;
  projects: DeclaredProject[];
  
  // UI Helper Props (Optional)
  rawCardPoints?: number;
  projectPoints?: number;
  totalRaw?: number;
  gamePoints?: number;
}

export interface ScoreBreakdown {
  rawCardPoints: number;
  projectPoints: number;
  totalRaw: number;
  gamePoints: number;
  isKaboot: boolean;
  multiplierApplied: number;
}

export interface RoundResult {
  roundNumber?: number; // Added
  us: DetailedScore;
  them: DetailedScore;
  winner: 'us' | 'them' | 'tie' | 'NONE';
  bidder?: string;
  gameMode?: 'SUN' | 'HOKUM';
  doubling?: number;
  reason?: string;
}

/** Extended round data from server replay system — includes trick-level detail. */
export interface MatchHistoryRound extends RoundResult {
  bid?: Bid;
  scores?: { us: DetailedScore; them: DetailedScore };
  tricks?: {
    cards: { card: CardModel; playedBy: string }[];
    winner?: string;
    points?: number;
  }[];
}



export enum ProjectType {
  SIRA = 'SIRA',       // Sequence of 3
  FIFTY = 'FIFTY',     // Sequence of 4
  HUNDRED = 'HUNDRED', // Sequence of 5 or 4-of-a-kind (Tens, J, Q, K - sometimes A in Sun)
  FOUR_HUNDRED = 'FOUR_HUNDRED', // 4 Aces (Sun only)
  BALOOT = 'BALOOT'    // K + Q of Trump
}

export enum DoublingLevel {
  NORMAL = 1,
  DOUBLE = 2,
  TRIPLE = 3,
  QUADRUPLE = 4,
  GAHWA = 100 // Instant Win
}

export enum LeagueTier {
  BRONZE = 'Bronze',
  SILVER = 'Silver',
  GOLD = 'Gold',
  PLATINUM = 'Platinum',
  DIAMOND = 'Diamond',
  grandmaster = "Grandmaster"
}

export interface UserProfile {
  id: string;
  name: string;
  avatar?: string;
  leaguePoints: number;
  tier: LeagueTier;
  level: number;
  xp: number;
  xpToNextLevel: number;
  coins: number;
  firstName?: string;
  lastName?: string;
  email?: string;
  disableProfessor?: boolean;
}

export interface DeclaredProject {
  type: ProjectType;
  rank: Rank;
  suit: Suit;
  owner: PlayerPosition;
  score?: number; // Added score for round result display
  cards?: CardModel[]; // The actual cards in this project (for reveal display)
}



export type QaydStep = 'IDLE' | 'MAIN_MENU' | 'VIOLATION_SELECT' | 'SELECT_CARD_1' | 'SELECT_CARD_2' | 'ADJUDICATION' | 'RESULT';

export interface QaydState {
  active: boolean;
  step?: QaydStep;
  reporter: PlayerPosition | null;
  reporter_is_bot?: boolean;
  menu_option?: string | null;
  violation_type?: string | null;
  crime_card?: CardModel | { card: CardModel } | null;
  proof_card?: CardModel | { card: CardModel } | null;
  verdict?: string | null; // 'CORRECT' | 'WRONG'
  verdict_message?: string | null;
  loser_team?: 'us' | 'them' | null;
  penalty_points?: number;
  timer_duration?: number;
  timer_start?: number;
  // Legacy compat
  reason?: string | null;
  target_play?: { card: CardModel; playedBy: PlayerPosition; metadata?: TableCardMetadata } | null;
  status?: 'REVIEW' | 'RESOLVED' | null;
}

export interface GameState {
  gameId?: string; // Phase VII: For Remote Debugging & AI
  players: Player[];
  currentTurnIndex: number;
  phase: GamePhase;
  biddingPhase?: string; // e.g. "GABLAK_WINDOW"
  tableCards: { card: CardModel; playedBy: PlayerPosition; metadata?: TableCardMetadata }[];
  gameMode?: 'SUN' | 'HOKUM';
  trumpSuit?: Suit;
  bid: Bid;
  teamScores: { us: number; them: number };
  matchScores: { us: number; them: number }; // For Championship (152)
  roundHistory: RoundResult[];

  // Scored Tricks History
  currentRoundTricks?: {
    cards: (CardModel | { card: CardModel; playedBy: string })[];
    playedBy?: string[];
    winner?: string;
    points?: number;
    metadata?: Record<string, unknown>;
  }[];

  floorCard: CardModel | null;
  deck: CardModel[];
  dealerIndex: number;
  biddingRound: number;
  declarations: { [key: string]: DeclaredProject[] };

  // Transition Flags
  isRoundTransitioning?: boolean;
  isTrickTransitioning?: boolean;
  isProjectRevealing?: boolean;
  trickCount?: number; // Completed tricks in current round (0 = still trick 1)

  doublingLevel: DoublingLevel;
  isLocked: boolean;
  settings: GameSettings;

  // Phase V: Sawa
  sawaState?: {
    active: boolean;
    claimer: PlayerPosition;
    responses: Record<string, 'ACCEPT' | 'REFUSE'>;
    status: 'PENDING' | 'ACCEPTED' | 'REFUSED' | 'NONE';
    challenge_active: boolean;
  } | null;
  sawaClaimed?: PlayerPosition;

  // Phase V: Sawa
  isFastForwarding?: boolean;

  // Phase VII: Qayd
  qaydPenalty?: { team: 'us' | 'them', round: number };
  lastTrick?: { cards: { card: CardModel; playedBy: PlayerPosition }[]; winner: PlayerPosition } | null;
  qaydState?: QaydState;

  // Akka
  akkaState?: { claimer: PlayerPosition; suits: string[]; timestamp: number } | null;

  // Debug/Dev
  fullMatchHistory?: MatchHistoryRound[];
  analytics?: {
    winProbability: { trick: number; us: number }[];
    blunders?: { [key: string]: number }; // Map "Bottom": count
  };
  metadata?: {
    source_game_id?: string;
    forked_at_round?: number;
    forked_at_trick?: number;
    original_final_scores?: { us: number; them: number };
    [key: string]: unknown;
  };
}