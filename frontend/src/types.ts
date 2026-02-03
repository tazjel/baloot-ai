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

  // Director Configs
  strategy?: 'heuristic' | 'mcts' | 'neural' | 'hybrid';
  profile?: 'Aggressive' | 'Conservative' | 'Balanced';
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

export interface GameSettings {
  turnDuration: number; // Seconds (e.g. 5, 10, 15)
  strictMode: boolean; // True = Auto-block illegal moves, False = Allow illegal + Disputes
  soundEnabled: boolean;
  gameSpeed: 'NORMAL' | 'FAST';
  isDebug?: boolean;
  fourColorMode?: boolean; // NEW: Accessibility
  highContrastMode?: boolean; // NEW: Accessibility
  cardLanguage?: 'EN' | 'AR'; // NEW: Arabic/English Indices
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
}

export interface ProfessorIntervention {
  type: string;
  message: string;
  suggestion?: {
    action: string;
    cardIndex?: number;
    reasoning?: string;
  };
  confidence: number;
}

export interface QaydState {
  active: boolean;
  reporter: PlayerPosition | null; // Backend uses Position string
  reason: string | null;
  target_play: { card: CardModel; playedBy: PlayerPosition; metadata?: TableCardMetadata };
  status?: 'REVIEW' | 'RESOLVED';
  verdict?: string;
  loser_team?: 'us' | 'them'; // Added
}

export interface GameState {
  gameId?: string; // Phase VII: For Remote Debugging & AI
  players: Player[];
  currentTurnIndex: number;
  phase: GamePhase;
  biddingPhase?: string; // e.g. "GABLAK_WINDOW"
  tableCards: { card: CardModel; playedBy: PlayerPosition; metadata?: TableCardMetadata }[];
  gameMode?: string;
  trumpSuit?: Suit;
  bid: Bid;
  teamScores: { us: number; them: number };
  matchScores: { us: number; them: number }; // For Championship (152)
  roundHistory: RoundResult[];

  // Scored Tricks History
  currentRoundTricks?: { cards: CardModel[] }[];

  floorCard: CardModel | null;
  deck: CardModel[];
  dealerIndex: number;
  biddingRound: number;
  declarations: { [key: string]: DeclaredProject[] };

  // Transition Flags
  isRoundTransitioning?: boolean;
  isTrickTransitioning?: boolean;
  isProjectRevealing?: boolean;

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
  fullMatchHistory?: any[];
  analytics?: {
    winProbability: { trick: number; us: number }[];
    blunders?: { [key: string]: number }; // Map "Bottom": count
  };
  metadata?: {
    source_game_id?: string;
    forked_at_round?: number;
    forked_at_trick?: number;
    original_final_scores?: { us: number; them: number };
    [key: string]: any;
  };
}