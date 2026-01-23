
const SUITS = ['♠', '♥', '♦', '♣']; // Spades, Hearts, Diamonds, Clubs
const RANKS = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A'];

// Need to update Logic if it relies on 'S'/'H'.
// Frontend `utils/gameLogic.ts` uses the Enums. 
// So Server should too.

const POINT_VALUES_SUN = {
    '7': 0, '8': 0, '9': 0, 'J': 2, 'Q': 3, 'K': 4, '10': 10, 'A': 11
};

const POINT_VALUES_HOKUM = {
    '7': 0, '8': 0, 'Q': 3, 'K': 4, '10': 10, 'A': 11, '9': 14, 'J': 20
};

const ORDER_SUN = ['7', '8', '9', 'J', 'Q', 'K', '10', 'A'];
const ORDER_HOKUM = ['7', '8', 'Q', 'K', '10', 'A', '9', 'J'];

const PROJECT_TYPES = {
    SIRA: 'SIRA',
    FIFTY: 'FIFTY',
    HUNDRED: 'HUNDRED',
    FOUR_HUNDRED: 'FOUR_HUNDRED',
    BALOOT: 'BALOOT'
};

const PROJECT_SCORES = {
    SIRA: 20,
    FIFTY: 50,
    HUNDRED: 100,
    FOUR_HUNDRED: 400,
    BALOOT: 20
};

// Sequence Order: A, K, Q, J, 10, 9, 8, 7.
const ORDER_PROJECTS = ['A', 'K', 'Q', 'J', '10', '9', '8', '7'];

module.exports = {
    SUITS, RANKS, POINT_VALUES_SUN, POINT_VALUES_HOKUM, ORDER_SUN, ORDER_HOKUM,
    PROJECT_TYPES, PROJECT_SCORES, ORDER_PROJECTS
};
