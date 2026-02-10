"""
Serialization Guard — Quick CI/pre-commit check that all stateful properties
survive a JSON round-trip.

Usage:
    python scripts/verification/run_serialization_guard.py

Runs ONLY the round-trip tests (fast <2s) to catch serialization regressions.
Exit code 0 = pass, 1 = fail.
"""
import subprocess
import sys
import os

# Always run from project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def main():
    print("=" * 60)
    print("  SERIALIZATION GUARD — Round-Trip Tests")
    print("=" * 60)

    result = subprocess.run(
        [
            sys.executable, '-m', 'pytest',
            'tests/game_logic/test_round_trip.py',
            '-v', '--tb=short', '-q'
        ],
        cwd=PROJECT_ROOT,
        capture_output=False,
    )

    if result.returncode == 0:
        print("\n✅ All round-trip tests passed. Serialization is safe.")
    else:
        print("\n❌ SERIALIZATION REGRESSION DETECTED!")
        print("   Fix the failing tests before committing.")

    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
