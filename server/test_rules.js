const RuleVerifier = require('./RuleVerifier');

// Mock Data
function createCard(suit, rank) { return { suit, rank }; }
const SUITS = ['♠', '♥', '♦', '♣'];

function runTest(name, result, expected) {
    if (result === expected) console.log(`✅ ${name}`);
    else console.error(`❌ ${name}: Expected ${expected}, Got ${result}`);
}

console.log("--- TEST: RuleVerifier ---");

// Scenario 1: Follow Suit (Simple)
const hand1 = [createCard('♠', 'A'), createCard('♥', 'K')];
const table1 = [{ card: createCard('♠', '7'), playedBy: 'Right' }]; // Lead Spades
const r1 = RuleVerifier.isValidMove(createCard('♠', 'A'), hand1, table1, 'SUN', null, 'us', 'them');
runTest('Follow Suit (Valid)', r1, true);

const r2 = RuleVerifier.isValidMove(createCard('♥', 'K'), hand1, table1, 'SUN', null, 'us', 'them');
runTest('Follow Suit (Invalid)', r2, false);

// Scenario 2: Hokum Overtrump
const handTrump = [createCard('♦', 'K'), createCard('♦', '7')]; // Diamonds = Trump
const tableTrump = [
    { card: createCard('♠', '7'), playedBy: 'Right' }, // Lead Spades
    { card: createCard('♦', '9'), playedBy: 'Top' }    // Partner? No, let's say Top is Opponent
];
// Check overtrump logic
// Opponent played Trump 9 (Val 14). We have K (Val 4) and 7 (Val 0). We can't beat.
// Rule: Undertrump (play trump anyway).
// Since we have trump, and lead was Spades, and we (assume) don't have Spades.
// handTrump has no spades.
const r3 = RuleVerifier.isValidMove(createCard('♦', 'K'), handTrump, tableTrump, 'HOKUM', '♦', 'us', 'them');
runTest('Undertrump (Valid)', r3, true);

// Scenario 3: Must Overtrump
const handOver = [createCard('♦', 'J'), createCard('♦', '7')]; // J=20
const tableOver = [
    { card: createCard('♠', '7'), playedBy: 'Right' },
    { card: createCard('♦', '9'), playedBy: 'Top' } // Opponent
];
// We MUST play J to beat 9. Playing 7 is failing to overtrump.
const r4 = RuleVerifier.isValidMove(createCard('♦', '7'), handOver, tableOver, 'HOKUM', '♦', 'us', 'them');
runTest('Fail Overtrump (Invalid)', r4, false);

const r5 = RuleVerifier.isValidMove(createCard('♦', 'J'), handOver, tableOver, 'HOKUM', '♦', 'us', 'them');
runTest('Overtrump with J (Valid)', r5, true);

// Scenario 4: Partner Winning (Locked)
const tableLocked = [
    { card: createCard('♠', '7'), playedBy: 'Right' }, // Lead
    { card: createCard('♦', 'J'), playedBy: 'Top' } // Partner played J (Winning)
];
// We act as 'Left' (Partner of 'Top' probably?? Pos logic needed)
// winningTeam passed as 'us'.
const handLocked = [createCard('♦', 'Q'), createCard('♣', 'A')];
// If we have trump Q, do we HAVE to play it?
// We have no Spades.
// Locked -> We can play ANYTHING? Or just don't need to trump?
// RuleVerifier logic: `if (winningTeam === playerTeam) return true;`
const r6 = RuleVerifier.isValidMove(createCard('♣', 'A'), handLocked, tableLocked, 'HOKUM', '♦', 'us', 'us');
runTest('Partner Winner (Trash Allowed)', r6, true);
