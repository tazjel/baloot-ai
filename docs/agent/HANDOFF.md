# Session Handoff — 2026-02-12

## Commits
- `91e93d0` feat(projects): add ProjectReveal component + fix trickCount schema bug

## What Was Done
- **ProjectReveal feature**: Built full 3-phase display — labels in Trick 1, card fan in Trick 2, hidden in Trick 3+. Includes `ProjectReveal.tsx`, ActionBar declaration UI, and PlayerAvatar integration.
- **Fixed trickCount bug**: `GameStateModel` Pydantic schema in `server/schemas/game.py` was silently dropping `trickCount` during `model_dump()`. Added the missing field. Verified via Playwright MCP console logs.
- **Playwright MCP**: Configured and tested in `.gemini/settings.json` for browser automation.

## What's Still Open
- Remove temporary `console.log('[ProjectReveal]', ...)` debug line from `ProjectReveal.tsx` (~line 209).
- Visually verify the card fan display in Trick 2 (labels in Trick 1 confirmed working, but human player rarely has projects to see the fan).
- Consider adding project declaration prompt/toast for human player during Trick 1.

## Known Gotchas
- **Pydantic schema gatekeeper**: Any new field added to `game.py:to_json()` must ALSO be added to `server/schemas/game.py:GameStateModel`, otherwise `broadcast.py` silently drops it via `model_dump()`.
- **Bot auto-declaration**: Happens in `game.py:start_playing_phase()`, not in `trick_manager.py`.
- **Antigravity allow-list**: Stored in LevelDB (volatile), not `settings.json`. The `settings.json` key `geminicodeassist.agent.allowedTerminalCommands` does NOT work for the UI. User must add entries via the Settings → Agent UI.
