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
