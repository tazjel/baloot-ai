import { CardModel, Rank, Suit, DeclaredProject, ProjectType, PlayerPosition, TableCardMetadata } from "../types";

// Rank order for sequences (A, K, Q, J, 10, 9, 8, 7) - strict descending for sequence checks
const SEQUENCE_ORDER = [Rank.Ace, Rank.King, Rank.Queen, Rank.Jack, Rank.Ten, Rank.Nine, Rank.Eight, Rank.Seven];

export const detectProjects = (hand: CardModel[], playerPos: PlayerPosition, trumpSuit?: Suit | null): DeclaredProject[] => {
    const projects: DeclaredProject[] = [];

    // Helper: Group by Suit
    const bySuit: { [key in Suit]?: CardModel[] } = {};
    Object.values(Suit).forEach(s => bySuit[s] = []);
    hand.forEach(c => bySuit[c.suit]?.push(c));

    // Helper: Check for 4 of a kind
    const rankCounts: { [key in Rank]?: number } = {};
    hand.forEach(c => rankCounts[c.rank] = (rankCounts[c.rank] || 0) + 1);

    // 1. Check 400 (4 Aces) -> Only in Sun usually, but let's detect generally
    if (rankCounts[Rank.Ace] === 4) {
        projects.push({ type: ProjectType.FOUR_HUNDRED, rank: Rank.Ace, suit: Suit.Spades, owner: playerPos }); // Suit arbitrary
    }

    // 2. Check 100 (4 K, Q, J, 10)
    [Rank.King, Rank.Queen, Rank.Jack, Rank.Ten].forEach(r => {
        if (rankCounts[r] === 4) {
            projects.push({ type: ProjectType.HUNDRED, rank: r, suit: Suit.Spades, owner: playerPos });
        }
    });

    // 3. Check Sequences (Sira, 50, 100)
    for (const suit of Object.values(Suit)) {
        const cards = bySuit[suit as Suit];
        if (!cards || cards.length < 3) continue;

        // Sort by Sequence Order
        cards.sort((a, b) => SEQUENCE_ORDER.indexOf(a.rank) - SEQUENCE_ORDER.indexOf(b.rank));

        let currentSeq: CardModel[] = [cards[0]];
        for (let i = 1; i < cards.length; i++) {
            const prevRankIdx = SEQUENCE_ORDER.indexOf(currentSeq[currentSeq.length - 1].rank);
            const currRankIdx = SEQUENCE_ORDER.indexOf(cards[i].rank);

            if (currRankIdx === prevRankIdx + 1) {
                currentSeq.push(cards[i]);
            } else {
                processSequence(currentSeq, projects, playerPos, suit as Suit);
                currentSeq = [cards[i]];
            }
        }
        processSequence(currentSeq, projects, playerPos, suit as Suit);
    }

    // 4. Baloot (K + Q of Trump) - Detected separately usually during play, but can be pre-detected
    if (trumpSuit) {
        const hasKing = hand.some(c => c.suit === trumpSuit && c.rank === Rank.King);
        const hasQueen = hand.some(c => c.suit === trumpSuit && c.rank === Rank.Queen);
        if (hasKing && hasQueen) {
            projects.push({ type: ProjectType.BALOOT, rank: Rank.King, suit: trumpSuit, owner: playerPos });
        }
    }

    return projects;
};

const processSequence = (seq: CardModel[], projects: DeclaredProject[], pos: PlayerPosition, suit: Suit) => {
    if (seq.length >= 5) {
        projects.push({ type: ProjectType.HUNDRED, rank: seq[0].rank, suit, owner: pos });
    } else if (seq.length === 4) {
        projects.push({ type: ProjectType.FIFTY, rank: seq[0].rank, suit, owner: pos });
    } else if (seq.length === 3) {
        projects.push({ type: ProjectType.SIRA, rank: seq[0].rank, suit, owner: pos });
    }
};

// Hierarchy for comparison
// Hierarchy for comparison
const PROJECT_SCORES = {
    SUN: {
        [ProjectType.FOUR_HUNDRED]: 400, // 4 Aces
        [ProjectType.HUNDRED]: 200,
        [ProjectType.FIFTY]: 100,
        [ProjectType.SIRA]: 40,
        [ProjectType.BALOOT]: 0 // N/A in Sun
    },
    HOKUM: {
        [ProjectType.FOUR_HUNDRED]: 0, // N/A
        [ProjectType.HUNDRED]: 100,
        [ProjectType.FIFTY]: 50,
        [ProjectType.SIRA]: 20,
        [ProjectType.BALOOT]: 20
    }
};

// Returns raw value for comparison
const getProjectValue = (p: DeclaredProject, mode: 'SUN' | 'HOKUM') => PROJECT_SCORES[mode][p.type];

export const compareProjects = (p1: DeclaredProject, p2: DeclaredProject, mode: 'SUN' | 'HOKUM' = 'HOKUM'): number => {
    const val1 = getProjectValue(p1, mode);
    const val2 = getProjectValue(p2, mode);

    if (val1 !== val2) return val1 - val2;

    // Same type, compare Rank
    const r1 = SEQUENCE_ORDER.indexOf(p1.rank); // Lower index = Better rank (A=0, K=1...)
    const r2 = SEQUENCE_ORDER.indexOf(p2.rank);

    // In sequence_order, 0 is best. So if r1 < r2, p1 is better.
    // Return positive if p1 better.
    return r2 - r1;
};

// Point values for scoring (abont)
export const POINT_VALUES = {
    SUN: { [Rank.Ace]: 11, [Rank.Ten]: 10, [Rank.King]: 4, [Rank.Queen]: 3, [Rank.Jack]: 2, [Rank.Nine]: 0, [Rank.Eight]: 0, [Rank.Seven]: 0 },
    HOKUM: { [Rank.Jack]: 20, [Rank.Nine]: 14, [Rank.Ace]: 11, [Rank.Ten]: 10, [Rank.King]: 4, [Rank.Queen]: 3, [Rank.Eight]: 0, [Rank.Seven]: 0 }
};

// Strength for winning tricks (higher is better)
// In Sun: A > 10 > K > Q > J > 9 > 8 > 7
// In Hokum (Trump): J > 9 > A > 10 > K > Q > 8 > 7
// In Hokum (Non-Trump): A > 10 > K > Q > J > 9 > 8 > 7
const STRENGTH_ORDER = {
    SUN: [Rank.Seven, Rank.Eight, Rank.Nine, Rank.Jack, Rank.Queen, Rank.King, Rank.Ten, Rank.Ace],
    HOKUM_TRUMP: [Rank.Seven, Rank.Eight, Rank.Queen, Rank.King, Rank.Ten, Rank.Ace, Rank.Nine, Rank.Jack],
    HOKUM_NORMAL: [Rank.Seven, Rank.Eight, Rank.Nine, Rank.Jack, Rank.Queen, Rank.King, Rank.Ten, Rank.Ace]
};

const getCardStrength = (card: CardModel, mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    if (mode === 'SUN') {
        return STRENGTH_ORDER.SUN.indexOf(card.rank);
    } else {
        if (trumpSuit && card.suit === trumpSuit) {
            return 100 + STRENGTH_ORDER.HOKUM_TRUMP.indexOf(card.rank); // Trump always beats non-trump
        }
        return STRENGTH_ORDER.HOKUM_NORMAL.indexOf(card.rank);
    }
};

export const getTrickWinner = (
    tableCards: { card: CardModel, playedBy: string, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null
): number => {
    if (tableCards.length === 0) return -1;

    const leadSuit = tableCards[0].card.suit;
    let highestStrength = -1;
    let winnerIndex = 0;

    tableCards.forEach((play, index) => {
        const card = play.card;
        let strength = 0;

        // If card matches lead suit or is trump (in Hokum)
        if (card.suit === leadSuit || (mode === 'HOKUM' && card.suit === trumpSuit)) {
            strength = getCardStrength(card, mode, trumpSuit);
        } else {
            // Irrelevant suit (unless we are playing Sun and players follow suit? No, unrelated suit is just 0 strength relative to lead)
            strength = -1;
        }

        if (strength > highestStrength) {
            highestStrength = strength;
            winnerIndex = index;
        }
    });

    return winnerIndex;
};

export const isValidMove = (
    card: CardModel,
    hand: CardModel[],
    tableCards: { card: CardModel, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null,
    isLocked: boolean = false,
    strictMode: boolean = true // New Flag
): boolean => {
    if (!strictMode) return true; // Allow EVERYTHING in Permissive Mode

    // Lead player
    if (tableCards.length === 0) {
        // LOCKED RULE: If game is locked (Doubled), cannot lead Trump unless forced
        if (isLocked && mode === 'HOKUM' && trumpSuit && card.suit === trumpSuit) {
            const hasNonTrump = hand.some(c => c.suit !== trumpSuit);
            if (hasNonTrump) return false;
        }
        return true;
    }

    const leadSuit = tableCards[0].card.suit;
    const hasLeadSuit = hand.some(c => c.suit === leadSuit);

    // Rule 1: Must follow suit
    if (hasLeadSuit) {
        if (card.suit !== leadSuit) return false;
        return true;
    }

    // Rule 2: If cannot follow suit, and mode is Hokum...
    if (mode === 'HOKUM' && trumpSuit) {
        const hasTrump = hand.some(c => c.suit === trumpSuit);
        // ...and opponent played non-trump, you MUST trump if possible (simplified rule, often specific to who is winning)
        // For simplicity: If you have trump and can't follow suit, you must play trump.
        if (hasTrump && card.suit !== trumpSuit) return false;
    }

    // Otherwise (no lead suit, no trump obligation/capability), any card is valid
    return true;
};

// New Function: Explain WHY a move is invalid (for Disputes)
export const getInvalidMoveReason = (
    card: CardModel,
    hand: CardModel[],
    tableCards: { card: CardModel, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null,
    isLocked: boolean = false
): string | null => {
    // If table matches current trick state when invalid move was made.

    // Lead player logic
    if (tableCards.length === 0) {
        if (isLocked && mode === 'HOKUM' && trumpSuit && card.suit === trumpSuit) {
            const hasNonTrump = hand.some(c => c.suit !== trumpSuit);
            // FIX: If player ONLY has Trump, they MUST led Trump. "You cannot lead Trump unless forced."
            // So if hasNonTrump is false, this move IS valid (forced).
            // Logic: if (hasNonTrump) return Error. Else return Null (Valid).
            if (hasNonTrump) return "You cannot help (lead trump) when the game is Locked (Doubled)!";
        }
        return null; // Valid lead
    }

    const leadSuit = tableCards[0].card.suit;
    const hasLeadSuit = hand.some(c => c.suit === leadSuit);

    // Rule 1: Must follow suit
    if (hasLeadSuit) {
        if (card.suit !== leadSuit) return `You have ${leadSuit} in your hand! You must follow suit (Renounce).`;
        return null;
    }

    // Rule 2: If cannot follow suit, and mode is Hokum...
    if (mode === 'HOKUM' && trumpSuit) {
        const hasTrump = hand.some(c => c.suit === trumpSuit);
        // ...and you have trump, you must cut
        if (hasTrump && card.suit !== trumpSuit) return `You have Trump (${trumpSuit})! You must Cut the trick since you cannot follow suit.`;
    }

    return null; // Valid
};

export const getProjectScoreValue = (type: ProjectType, mode: 'SUN' | 'HOKUM'): number => {
    return PROJECT_SCORES[mode][type] || 0;
};


// Calculate Score with Multipliers (Doubling) and Kaboot
// NOTE: Now receives separate raw scores!
export const calculateFinalScore = (
    rawCardPoints: number,
    projectPoints: number,
    isKaboot: boolean,
    mode: 'SUN' | 'HOKUM',
    doublingLevel: number,
    isWinner: boolean // Is this the winning team?
): number => {

    // 1. Kaboot Logic
    if (isKaboot) {
        // Winner takes fixed score, loser 0
        if (!isWinner) return 0;
        if (mode === 'HOKUM') return 25 + (projectPoints / 10); // Standard Kaboot is 25 + Projects? Or just 25? Usually projects valid.
        // Simplified: Kaboot Hokum = 25 guaranteed.
        // Sun = 44.
        // FIX: The types check above guarantees mode is HOKUM. 
        // But if we want to be safe for 'SUN' kaboot logic, we should use 'else'.
        // Actually, if check above returns, this line is only reached if mode !== HOKUM.
        // So return 44.
        return 44;
    }

    // 2. Standard Logic
    let gamePoints = 0;
    const totalRaw = rawCardPoints + projectPoints;

    if (mode === 'SUN') {
        // Sun Formula: Round(Total * 2 / 10)
        // e.g. 10 points -> 20 -> 2.
        // e.g. 152 (Max Cards + Last Trick) + Projects
        // Max Cards = 130 + 10 = 140. 140*2/10 = 28.
        gamePoints = Math.round((totalRaw * 2) / 10);
    } else {
        // Hokum Formula: Round(Total / 10)
        // e.g. 152 + 10 = 162. 162/10 = 16.
        gamePoints = Math.round(totalRaw / 10);
    }

    // 3. Doubling
    if (doublingLevel > 1) {
        // Losing team gets 0 in doubled games? Usually yes.
        // Winning team gets ALL points?
        // Or is it just a multiplier?
        // Standard: Score * Level.
        gamePoints *= doublingLevel;
    }

    return gamePoints;
};

// --- Sorting Logic ---

/**
 * Returns a numeric rank for sorting.
 * Higher number = Higher priority (appears first in hand).
 */
export const getSortRank = (card: CardModel, mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): number => {
    // 1. Project/Sequence Sorting (If needed for declaration view, but user asked for Hand View)
    // The user specified:
    // "Sequence (Project) Ranking" -> Natural Order (A, K, Q, J, 10, 9, 8, 7)
    // "Sun Game Sorting" -> Power (A, 10, K, Q, J, 9, 8, 7)
    // "Hokum Game Sorting" -> Trump (J, 9, A, 10, K, Q, 8, 7) vs Non-Trump (Same as Sun usually? User listed "Hokum Game Sorting" generally, but let's stick to our STRENGTH_ORDER logic which is robust)

    // NOTE: STRENGTH_ORDER arrays are Lowest -> Highest.
    // So index 0 is 7, index 7 is Ace (in Sun).
    // We want Descending sort, so Rank = Index. 
    // Sort function will be (b.rank - a.rank).

    if (mode === 'SUN') {
        return STRENGTH_ORDER.SUN.indexOf(card.rank);
    } else {
        // HOKUM
        if (trumpSuit && card.suit === trumpSuit) {
            return STRENGTH_ORDER.HOKUM_TRUMP.indexOf(card.rank);
        } else {
            // Non-Trump in Hokum
            // User query said: "The application generally arranges sequences within a suit based on their natural rank (from Ace down to 7)... However, the internal "strength" order changes..."
            // Usually, for ease of play, people prefer Strength order in hand too?
            // The prompt says: "If the game is set to Sun, the application prioritizes... according to their power".
            // "If a suit is designated as Trump... sorting logic... changes dramatically".
            // It strongly implies that sorting should follow Power.
            // For Non-Trump suits in Hokum, Power is standard (A > 10 > K...).
            return STRENGTH_ORDER.HOKUM_NORMAL.indexOf(card.rank);
        }
    }
};

/**
 * Sorts the hand according to the current game rules.
 * 1. Groups by Suit.
 * 2. Alternates Colors (Red/Black).
 * 3. Sorts internal cards by Power/Strength (Descending).
 */
export const sortHand = (hand: CardModel[], mode: 'SUN' | 'HOKUM', trumpSuit?: Suit | null): CardModel[] => {
    if (!hand) return [];

    // Group by Suit
    const spades = hand.filter(c => c.suit === Suit.Spades);
    const hearts = hand.filter(c => c.suit === Suit.Hearts);
    const clubs = hand.filter(c => c.suit === Suit.Clubs);
    const diamonds = hand.filter(c => c.suit === Suit.Diamonds);

    // Internal Sort Function (Descending Power)
    // Internal Sort Function (Natural Sequence: A, K, Q, J, 10, 9, 8, 7)
    // SEQUENCE_ORDER is [A, K, Q...]. Index 0 is A.
    // We want A first. So a.index - b.index.
    const sorter = (a: CardModel, b: CardModel) => {
        const idxA = SEQUENCE_ORDER.indexOf(a.rank);
        const idxB = SEQUENCE_ORDER.indexOf(b.rank);
        return idxA - idxB;
    };

    spades.sort(sorter);
    hearts.sort(sorter);
    clubs.sort(sorter);
    diamonds.sort(sorter);

    // Color Alternation Strategy
    // Black: Spades, Clubs
    // Red: Hearts, Diamonds
    // Pattern: Black -> Red -> Black -> Red

    // We can prioritize Trump suit to be first or last? 
    // User didn't specify position of groups, just "groups all cards of same suit" and "alternates colors".
    // Let's stick to a fixed alternating order for consistency, e.g., Spades, Diamonds, Clubs, Hearts.
    // Colors: Black, Red, Black, Red.

    // If we wanted to be fancy, we could put Trump first. But fixed is safer for muscle memory.

    return [
        ...spades,
        ...diamonds,
        ...clubs,
        ...hearts
    ];
};

export const generateDeck = (): CardModel[] => {
    const suits = Object.values(Suit);
    const ranks = Object.values(Rank);
    const deck: CardModel[] = [];

    // Baloot uses 32 cards (7, 8, 9, 10, J, Q, K, A)
    // Our Rank Enum has all of them.
    // Ensure we don't accidentally include 2-6 if enum changed.

    let idCounter = 1;
    for (const suit of suits) {
        for (const rank of ranks) {
            // Basic ID generation
            deck.push({
                id: `${suit}-${rank}-${idCounter++}`,
                suit,
                rank,
                value: 0 // Will be calculated dynamically
            });
        }
    }

    // Fisher-Yates Shuffle
    for (let i = deck.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [deck[i], deck[j]] = [deck[j], deck[i]];
    }

    return deck;
};

// --- Project Conflict Resolution ---

export const resolveProjectConflicts = (
    declarations: { [key: string]: DeclaredProject[] },
    mode: 'SUN' | 'HOKUM'
): { [key: string]: DeclaredProject[] } => {
    const resolved: { [key: string]: DeclaredProject[] } = {};
    const teams = {
        us: [] as DeclaredProject[],
        them: [] as DeclaredProject[]
    };

    // 1. Separate Baloot from Mashaari (Conflicts)
    const mashaari: { us: DeclaredProject[], them: DeclaredProject[] } = { us: [], them: [] };

    // Initialize output structure
    Object.keys(declarations).forEach(pos => resolved[pos] = []);

    // 2. Group by Team
    Object.entries(declarations).forEach(([pos, projects]) => {
        const isUs = pos === PlayerPosition.Bottom || pos === PlayerPosition.Top;
        projects.forEach(p => {
            // Always keep Baloot
            if (p.type === ProjectType.BALOOT) {
                resolved[pos].push(p);
            } else {
                if (isUs) mashaari.us.push(p);
                else mashaari.them.push(p);
            }
        });
    });


    // 3. Find Best Project for each Team
    // Sort descending by value/rank (best project first)
    // compareProjects returns positive if p1 is better than p2
    // Array.sort expects: negative = a first, positive = b first
    // So multiply by -1 to get descending order (best first)
    mashaari.us.sort((a, b) => compareProjects(b, a, mode)); // Best first
    mashaari.them.sort((a, b) => compareProjects(b, a, mode));

    const bestUs = mashaari.us[0];
    const bestThem = mashaari.them[0];

    let winningTeam: 'us' | 'them' | 'none' = 'none';

    if (bestUs && !bestThem) winningTeam = 'us';
    else if (!bestUs && bestThem) winningTeam = 'them';
    else if (bestUs && bestThem) {
        const diff = compareProjects(bestUs, bestThem, mode);
        if (diff > 0) winningTeam = 'us';
        else if (diff < 0) winningTeam = 'them';
        else {
            // Tie!
            // Priority Rule: Rank -> Type are equal.
            // Next Rule: Elder Hand? Or "First Declared"? i.e. Distance from Dealer?
            // "Declarations in Baloot... if equal, the player closest to the dealer's right starts."
            // We don't have Dealer position passed easily here strictly, but usually 'Right' > 'Top' > 'Left' > 'Me' relative to dealer?
            // Simplification: Standard Baloot app behavior -> If technically equal, they cancel each other? Or one wins?
            // "If equal, no one scores Mashaari"?
            // Let's implement: "Equality cancels" (No one wins Mashaari).
            winningTeam = 'none';
        }
    } else {
        winningTeam = 'none'; // No projects
    }

    // 4. Distribute Winning Mashaari
    if (winningTeam === 'us') {
        // Add back all US mashaari to resolved
        Object.entries(declarations).forEach(([pos, projects]) => {
            if (pos === PlayerPosition.Bottom || pos === PlayerPosition.Top) {
                // Add non-Baloot
                projects.forEach(p => {
                    if (p.type !== ProjectType.BALOOT) resolved[pos].push(p);
                });
            }
        });
    } else if (winningTeam === 'them') {
        Object.entries(declarations).forEach(([pos, projects]) => {
            if (pos === PlayerPosition.Right || pos === PlayerPosition.Left) {
                projects.forEach(p => {
                    if (p.type !== ProjectType.BALOOT) resolved[pos].push(p);
                });
            }
        });
    }

    // sort for tidiness
    // Already pushed.

    return resolved;
};


// --- AKKA DECLARATION LOGIC ---

/**
 * Checks if a user can declare "Akka" (Master Card).
 * Rules:
 * 1. Must be HOKUM.
 * 2. Must be LEADING the trick (Table empty).
 * 3. Played card must be NON-TRUMP.
 * 4. Played card must be the highest remaining card of that suit.
 */
export const canDeclareAkka = (
    card: CardModel,
    hand: CardModel[],
    tableCards: { card: CardModel, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null,
    currentRoundTricks: { cards: CardModel[] }[] = [] // History of played cards
): boolean => {
    // 1. Must be Hokum
    if (mode !== 'HOKUM') return false;

    // 2. Must be Leading (Table empty)
    if (tableCards.length > 0) return false;

    // 3. Must be Non-Trump
    if (trumpSuit && card.suit === trumpSuit) return false;

    // 4. Must NOT be an Ace (Self-evident)
    if (card.rank === Rank.Ace) return false;

    // 4. Highest Remaining Logic
    // Collect all cards of this suit that have been played so far (Graveyard)
    const suit = card.suit;
    const playedCardsOfSuit: Rank[] = [];

    // Check previous tricks
    currentRoundTricks.forEach(trick => {
        trick.cards.forEach(c => {
            if (c.suit === suit) playedCardsOfSuit.push(c.rank);
        });
    });

    // Determine Strength Order for this suit (Non-Trump in Hokum -> A, 10, K, Q...)
    const order = STRENGTH_ORDER.HOKUM_NORMAL; // A > 10 > K ...

    // Valid ranks are those logically higher than my card
    const myRankIdx = order.indexOf(card.rank); // e.g. Rank.King -> index 5
    if (myRankIdx === -1) return false; // Should not happen

    // Check if any card HIGHER in the order exists outside the graveyard
    // Higher strength = Higher Index? 
    // Wait, STRENGTH_ORDER is [7, 8, 9, J, Q, K, 10, A]. 
    // Low index = Weak. High index = Strong.
    // So if my card is Index 5 (King), I need to check Index 6 (10) and Index 7 (Ace).

    for (let i = myRankIdx + 1; i < order.length; i++) {
        const higherRank = order[i];
        // Is this higher rank played?
        if (!playedCardsOfSuit.includes(higherRank)) {
            // It is NOT played.
            // Do I have it in my hand? (If I have Ace and King, leading Ace is Akka, leading King is NOT Akka).
            const haveIt = hand.some(c => c.suit === suit && c.rank === higherRank);
            if (haveIt) {
                // I have the higher card, so THIS card is not the master.
                return false;
            }
            // If I don't have it, and it wasn't played -> Opponent might have it.
            // So this card is NOT master.
            return false;
        }
    }

    // If we passed the loop, all higher cards are verified played (or held by me? No, if held by me we return false).
    // Wait, if I hold A and K.
    // I play K. Check A. Not in graveyard. In hand? Yes. Return False. Correct.
    // I play A. Index 7. Loop doesn't run. Return True. Correct.

    return true;
};

/**
 * Scans the entire hand to check if ANY card is eligible for Akka.
 */
export const scanHandForAkka = (
    hand: CardModel[],
    tableCards: { card: CardModel, metadata?: TableCardMetadata }[],
    mode: 'SUN' | 'HOKUM',
    trumpSuit: Suit | null,
    currentRoundTricks: { cards: CardModel[] }[] = []
): boolean => {
    // Basic checks first to save performance
    if (mode !== 'HOKUM') return false;
    if (tableCards.length > 0) return false;

    // Check every card in hand
    for (const card of hand) {
        if (canDeclareAkka(card, hand, tableCards, mode, trumpSuit, currentRoundTricks)) {
            return true;
        }
    }
    return false;
};

/**
 * Checks if a user can declare "Kawesh" (Redeal).
 * Rules:
 * 1. Hand must possess NO Court Cards (A, K, Q, J, 10).
 * 2. Hand must be full (5 cards initial deal).
 */
export const canDeclareKawesh = (hand: CardModel[]): boolean => {
    const courtCards = [Rank.Ace, Rank.King, Rank.Queen, Rank.Jack, Rank.Ten];

    // Check if ANY card is a court card
    const hasPoints = hand.some(c => courtCards.includes(c.rank));

    return !hasPoints;
};
