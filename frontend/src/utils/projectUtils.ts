/**
 * projectUtils.ts — Project detection, comparison, and conflict resolution.
 * 
 * Handles Mashaari (sequences, 4-of-a-kind), Baloot detection, project value
 * comparison, and inter-team conflict resolution rules.
 */
import { CardModel, Rank, Suit, DeclaredProject, ProjectType, PlayerPosition } from "../types";

// Rank order for sequences (A, K, Q, J, 10, 9, 8, 7) - strict descending
export const SEQUENCE_ORDER = [Rank.Ace, Rank.King, Rank.Queen, Rank.Jack, Rank.Ten, Rank.Nine, Rank.Eight, Rank.Seven];

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
export const PROJECT_SCORES = {
    SUN: {
        [ProjectType.FOUR_HUNDRED]: 400,
        [ProjectType.HUNDRED]: 200,
        [ProjectType.FIFTY]: 100,
        [ProjectType.SIRA]: 40,
        [ProjectType.BALOOT]: 0
    },
    HOKUM: {
        [ProjectType.FOUR_HUNDRED]: 0,
        [ProjectType.HUNDRED]: 100,
        [ProjectType.FIFTY]: 50,
        [ProjectType.SIRA]: 20,
        [ProjectType.BALOOT]: 20
    }
};

const getProjectValue = (p: DeclaredProject, mode: 'SUN' | 'HOKUM') => PROJECT_SCORES[mode][p.type];

export const detectProjects = (hand: CardModel[], playerPos: PlayerPosition, trumpSuit?: Suit | null): DeclaredProject[] => {
    const projects: DeclaredProject[] = [];

    const bySuit: { [key in Suit]?: CardModel[] } = {};
    Object.values(Suit).forEach(s => bySuit[s] = []);
    hand.forEach(c => bySuit[c.suit]?.push(c));

    const rankCounts: { [key in Rank]?: number } = {};
    hand.forEach(c => rankCounts[c.rank] = (rankCounts[c.rank] || 0) + 1);

    // 400 (4 Aces)
    if (rankCounts[Rank.Ace] === 4) {
        projects.push({ type: ProjectType.FOUR_HUNDRED, rank: Rank.Ace, suit: Suit.Spades, owner: playerPos });
    }

    // 100 (4 K, Q, J, 10)
    [Rank.King, Rank.Queen, Rank.Jack, Rank.Ten].forEach(r => {
        if (rankCounts[r] === 4) {
            projects.push({ type: ProjectType.HUNDRED, rank: r, suit: Suit.Spades, owner: playerPos });
        }
    });

    // Sequences (Sira, 50, 100)
    for (const suit of Object.values(Suit)) {
        const cards = bySuit[suit as Suit];
        if (!cards || cards.length < 3) continue;
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

    // Baloot (K + Q of Trump)
    if (trumpSuit) {
        const hasKing = hand.some(c => c.suit === trumpSuit && c.rank === Rank.King);
        const hasQueen = hand.some(c => c.suit === trumpSuit && c.rank === Rank.Queen);
        if (hasKing && hasQueen) {
            projects.push({ type: ProjectType.BALOOT, rank: Rank.King, suit: trumpSuit, owner: playerPos });
        }
    }

    return projects;
};

export const compareProjects = (p1: DeclaredProject, p2: DeclaredProject, mode: 'SUN' | 'HOKUM' = 'HOKUM'): number => {
    const val1 = getProjectValue(p1, mode);
    const val2 = getProjectValue(p2, mode);
    if (val1 !== val2) return val1 - val2;

    const r1 = SEQUENCE_ORDER.indexOf(p1.rank);
    const r2 = SEQUENCE_ORDER.indexOf(p2.rank);
    return r2 - r1;
};

export const getProjectScoreValue = (type: ProjectType, mode: 'SUN' | 'HOKUM'): number => {
    return PROJECT_SCORES[mode][type] || 0;
};

export const resolveProjectConflicts = (
    declarations: { [key: string]: DeclaredProject[] },
    mode: 'SUN' | 'HOKUM'
): { [key: string]: DeclaredProject[] } => {
    const resolved: { [key: string]: DeclaredProject[] } = {};
    const mashaari: { us: DeclaredProject[], them: DeclaredProject[] } = { us: [], them: [] };

    Object.keys(declarations).forEach(pos => resolved[pos] = []);

    Object.entries(declarations).forEach(([pos, projects]) => {
        const isUs = pos === PlayerPosition.Bottom || pos === PlayerPosition.Top;
        projects.forEach(p => {
            if (p.type === ProjectType.BALOOT) {
                resolved[pos].push(p);
            } else {
                if (isUs) mashaari.us.push(p);
                else mashaari.them.push(p);
            }
        });
    });

    mashaari.us.sort((a, b) => compareProjects(b, a, mode));
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
        else winningTeam = 'none'; // Equality cancels
    }

    if (winningTeam === 'us') {
        Object.entries(declarations).forEach(([pos, projects]) => {
            if (pos === PlayerPosition.Bottom || pos === PlayerPosition.Top) {
                projects.forEach(p => { if (p.type !== ProjectType.BALOOT) resolved[pos].push(p); });
            }
        });
    } else if (winningTeam === 'them') {
        Object.entries(declarations).forEach(([pos, projects]) => {
            if (pos === PlayerPosition.Right || pos === PlayerPosition.Left) {
                projects.forEach(p => { if (p.type !== ProjectType.BALOOT) resolved[pos].push(p); });
            }
        });
    }

    return resolved;
};
