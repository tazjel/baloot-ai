import { CardModel, Rank, Suit } from './types';

export const RANKS_ORDER = [Rank.Seven, Rank.Eight, Rank.Nine, Rank.Jack, Rank.Queen, Rank.King, Rank.Ten, Rank.Ace];

export const generateDeck = (): CardModel[] => {
  const suits = [Suit.Hearts, Suit.Diamonds, Suit.Clubs, Suit.Spades];
  const ranks = [Rank.Seven, Rank.Eight, Rank.Nine, Rank.Ten, Rank.Jack, Rank.Queen, Rank.King, Rank.Ace];

  let deck: CardModel[] = [];
  let idCounter = 0;

  suits.forEach(suit => {
    ranks.forEach((rank, index) => {
      deck.push({
        id: `card-${idCounter++}`,
        suit,
        rank,
        value: index
      });
    });
  });

  // Shuffle
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }

  return deck;
};

export const AVATARS = {
  ME: "https://picsum.photos/id/64/100/100",
  RIGHT: "https://picsum.photos/id/65/100/100",
  TOP: "https://picsum.photos/id/66/100/100",
  LEFT: "https://picsum.photos/id/67/100/100"
};

// ── Centralized Player Configuration ──
// Bot names and positions — single source of truth.
import { PlayerPosition } from './types';

export const BOT_PLAYERS = {
  RIGHT: { position: PlayerPosition.Right, name: 'سالم', avatar: AVATARS.RIGHT },
  TOP:   { position: PlayerPosition.Top, name: 'شريكي', avatar: AVATARS.TOP },
  LEFT:  { position: PlayerPosition.Left, name: 'عمر', avatar: AVATARS.LEFT },
} as const;

export const INITIAL_PLAYERS = [
  { position: PlayerPosition.Bottom, name: 'أنا', avatar: AVATARS.ME },
  BOT_PLAYERS.RIGHT,
  BOT_PLAYERS.TOP,
  BOT_PLAYERS.LEFT,
] as const;

export const VISUAL_ASSETS = {
  CARDS: [
    { id: 'card_default', name: 'Royal Back', type: 'image', value: '/assets/royal_card_back.png' },
    { id: 'card_classic_blue', name: 'Classic Blue', type: 'css', value: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)' },
    { id: 'card_classic_red', name: 'Classic Red', type: 'css', value: 'linear-gradient(135deg, #991b1b 0%, #ef4444 100%)' },
    { id: 'card_modern_black', name: 'Modern Black', type: 'css', value: 'linear-gradient(135deg, #000000 0%, #444444 100%)' },
  ],
  TABLES: [
    { id: 'table_default', name: 'Premium Wood', type: 'image', value: 'PREMIUM_ASSETS' }, // Special handling for our complex wood+felt
    { id: 'table_classic_green', name: 'Classic Green', type: 'css', value: '#1a472a' },
    { id: 'table_royal_blue', name: 'Royal Blue', type: 'css', value: '#1e3a8a' },
    { id: 'table_midnight', name: 'Midnight', type: 'css', value: '#0f172a' },
  ]
};
