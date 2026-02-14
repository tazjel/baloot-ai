Review a strategy module for correctness and quality.

Usage: /review-strategy [module_name]
Example: /review-strategy follow_optimizer

If a module name is provided as $ARGUMENTS, review that specific module at `ai_worker/strategies/components/$ARGUMENTS.py`.

If no module name is provided, ask which module to review.

Check:
1. Constants imported from `ai_worker/strategies/constants.py` (no local duplicates)
2. Pure function pattern (no classes, no cross-imports between components)
3. Confidence scores are well-calibrated (0.0-1.0, higher = more certain)
4. All code paths return valid output (no dead code, no unreachable branches)
5. Baloot rules correctness (SUN vs HOKUM scoring, rank orders)
6. Integration with brain.py cascade (if applicable)
7. Docstrings and type hints on public functions

Use the baloot-reviewer agent for rule verification.
