const { validateProject } = require('./gameLogic');
const { SUITS, PROEJCT_TYPES } = require('./constants'); // Typos in valid require? No, constants has PROJECT_TYPES.

// Mock Constants if needed, but we require real ones.
// Logic relies on ORDER_PROJECTS which is exported.

function test(name, result, expected) {
    if (result === expected) console.log(`✅ ${name}`);
    else console.log(`❌ ${name}: Expected ${expected}, got ${result}`);
}

function runTests() {
    console.log("--- Testing Project Validation ---");

    // SIRA (3 consecutive)
    const handSira = [
        { suit: '♠', rank: 'A' },
        { suit: '♠', rank: 'K' },
        { suit: '♠', rank: 'Q' },
        { suit: '♥', rank: '7' },
        { suit: '♦', rank: '9' }
    ];
    const resSira = validateProject(handSira, 'SIRA', 'SUN');
    test('Sira Valid', resSira.valid, true);

    const handSiraFail = [
        { suit: '♠', rank: 'A' },
        { suit: '♠', rank: 'Q' },
        { suit: '♠', rank: '10' } // Gap
    ];
    const resSiraFail = validateProject(handSiraFail, 'SIRA', 'SUN');
    test('Sira Fail (Gap)', resSiraFail.valid, false);

    // FIFTY (4)
    const hand50 = [
        { suit: '♦', rank: '7' },
        { suit: '♦', rank: '8' },
        { suit: '♦', rank: '9' },
        { suit: '♦', rank: '10' },
        { suit: '♣', rank: 'A' }
    ];
    const res50 = validateProject(hand50, 'FIFTY', 'SUN');
    test('Fifty Valid', res50.valid, true);

    // HUNDRED (5)
    const hand100Seq = [
        { suit: '♣', rank: '7' },
        { suit: '♣', rank: '8' },
        { suit: '♣', rank: '9' },
        { suit: '♣', rank: '10' },
        { suit: '♣', rank: 'J' }
    ];
    const res100Seq = validateProject(hand100Seq, 'HUNDRED', 'SUN');
    test('Hundred Seq Valid', res100Seq.valid, true);

    // HUNDRED (4 of Kind)
    const hand100Kind = [
        { suit: '♣', rank: 'K' },
        { suit: '♦', rank: 'K' },
        { suit: '♠', rank: 'K' },
        { suit: '♥', rank: 'K' },
        { suit: '♣', rank: '7' }
    ];
    const res100Kind = validateProject(hand100Kind, 'HUNDRED', 'SUN');
    test('Hundred Kind Valid', res100Kind.valid, true);

    // 400 (4 Aces in Sun)
    const hand400 = [
        { suit: '♣', rank: 'A' },
        { suit: '♦', rank: 'A' },
        { suit: '♠', rank: 'A' },
        { suit: '♥', rank: 'A' },
        { suit: '♣', rank: '7' }
    ];
    const res400 = validateProject(hand400, 'FOUR_HUNDRED', 'SUN');
    test('400 Valid in Sun', res400.valid, true);

    const res400Hokum = validateProject(hand400, 'FOUR_HUNDRED', 'HOKUM');
    test('400 Invalid in Hokum (Should be 100)', res400Hokum.valid, false);
    // Wait, if I declare 400 in Hokum, it should fail. My logic:
    // if (rank === 'A' && type === 'FOUR_HUNDRED' && mode === 'SUN') ...
    // So yes, fails 400 check.

    // 100 with A in Hokum?
    const res100AcesHokum = validateProject(hand400, 'HUNDRED', 'HOKUM');
    test('100 (Aces) Valid in Hokum', res100AcesHokum.valid, true);

}

runTests();
