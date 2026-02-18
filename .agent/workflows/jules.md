---
description: How to delegate tasks to Jules AI. Covers session creation, prompt rules, PR creation, monitoring, and integrating results.
---

# /jules — Delegate Tasks to Jules AI

Jules is a GitHub-integrated AI coding agent that creates branches and PRs autonomously.
Use Jules for **isolated, spec-driven tasks** — new files, test suites, ports, and mechanical refactors.

## When to Use Jules

✅ **Good for:**
- Creating new files from a spec (services, notifiers, tests)
- Porting TypeScript/Python to Dart (mechanical translation)
- Generating test suites for existing code
- Isolated widget creation with clear contracts

❌ **Not good for:**
- Multi-file refactors touching core systems (use Claude MAX)
- Architecture decisions or design work
- Changes requiring deep context of existing patterns
- Anything touching `game.py` or `brain.py`

## Creating a Jules Session

### Via MCP Tool (Antigravity)
```
mcp_jules_create_session({
  repo: "tazjel/baloot-ai",
  branch: "main",
  prompt: "...",        // The task prompt — see Prompt Rules below
  autoPr: true,         // CRITICAL: always set to true
  interactive: false     // false = automated run (no plan approval needed)
})
```

### Via Jules CLI
```powershell
jules session create --repo tazjel/baloot-ai --branch main --auto-pr --prompt "..."
```

## Prompt Rules — What Makes Jules Succeed or Fail

> [!CAUTION]
> Jules will NOT create a PR unless explicitly told to. The `autoPr: true` flag alone is not enough.
> **Always include PR instructions in the prompt text itself.**

### Required Prompt Structure

Every Jules prompt MUST follow this template:

```
[TASK DESCRIPTION]

[SPECIFIC FILE LIST with paths and contents/specs]

[RULES]
- Import models from `package:baloot_ai/models/models.dart`
- [Other project-specific rules]

[PR INSTRUCTION — MANDATORY]
When done, create a PR with your changes. Title: "[M-FXX] Brief description"
```

### Prompt Best Practices

1. **Be extremely specific** — Jules works best with exact file paths and code skeletons
2. **Provide import paths** — Jules doesn't know the project structure well
3. **Include code patterns** — Show the exact class/function pattern to follow
4. **List every file** — Don't say "create test files", say "create `mobile/test/services/hint_service_test.dart`"
5. **Set test targets** — "Write 15+ tests across 3 files"
6. **State DO NOTs** — "DO NOT modify any existing files" or "DO NOT create `providers.dart`"
7. **Keep scope small** — 2-5 files max per session. More = more errors.
8. **Always end with PR instruction** — "When done, create a PR with title '[M-FXX] description'"

### Example: Good Prompt ✅

```
Create a file mobile/test/services/hint_service_test.dart with tests for the HintService.

The test file should:
- Import `package:flutter_test/flutter_test.dart`
- Import `package:baloot_ai/services/hint_service.dart`
- Test getBiddingHint returns a non-null HintResult for a valid hand
- Test getPlayingHint returns card suggestions
- Test getHint returns null when phase is not playing/bidding
- Target: 8+ test cases

Rules:
- Use `flutter_test` only (no mockito needed)
- DO NOT modify any existing files
- DO NOT create any files outside mobile/test/

When done, create a PR with your changes. Title: "[M-F20] HintService unit tests"
```

### Example: Bad Prompt ❌

```
Write tests for the Flutter app's services.
```

Why it fails: No file paths, no patterns, no scope, no PR instruction.

## Monitoring a Jules Session

### Check Status
```
mcp_jules_get_session_state({ sessionId: "..." })
```

Status values:
- `busy` — Jules is working. Don't interrupt unless stuck (>30 min for simple tasks).
- `stable` — Work paused. Check for `pendingPlan` (needs approval) or `lastAgentMessage`.
- `failed` — Unrecoverable. Start a new session.

### Review Code Changes
```
mcp_jules_get_code_review_context({ sessionId: "..." })
```

### View Diffs
```
mcp_jules_show_code_diff({ sessionId: "...", file: "path/to/file.dart" })
```

### Approve a Plan (interactive mode only)
```
mcp_jules_send_reply_to_session({ sessionId: "...", action: "approve" })
```

## Integrating Jules Output

### If Jules Created a PR ✅

// turbo
1. Check the PR:
```powershell
gh pr list --repo tazjel/baloot-ai --author "jules-google[bot]"
```

// turbo
2. Pull and test:
```powershell
cd "C:/Users/MiEXCITE/Projects/baloot-ai"
git fetch origin
git checkout jules/session-XXXXX
cd mobile && flutter test
```

3. If tests pass → merge the PR
4. If tests fail → fix locally, push to the PR branch, or close and redo

### If Jules Completed Without a PR ❌

This happens when the prompt didn't include PR instructions. Options:

1. **Get the diff** and apply manually:
```
mcp_jules_show_code_diff({ sessionId: "..." })
```

2. **Create a new session** with proper PR instructions (see Prompt Rules above)

## Task Spec Files

For complex tasks, create a spec file in `.agent/delegations/jules/` first:

```
.agent/delegations/jules/
  MF2-services.md      # Service ports spec
  MF3-notifiers.md     # Notifier ports spec
  MF20-hint-tests.md   # New task spec
```

Reference the spec in the Jules prompt:
```
Follow the spec in `.agent/delegations/jules/MF20-hint-tests.md` to create the test files.
```

## Session History & Lessons Learned

| Session | Task | PR? | Lesson |
|---------|------|-----|--------|
| M-F7 | Tests | ✅ | Worked well with specific test specs |
| M-F12 | Tests (4 files) | ✅ PR #22 | Prompt included explicit PR instruction |
| M-F17 | Font bundling | ❌ | No PR instruction → Claude did the work instead |
| M-F18 | A11y tests | ❌ | No PR instruction → completed but no branch pushed |

> [!IMPORTANT]
> The pattern is clear: **always include "create a PR" in the prompt text**.
> `autoPr: true` alone is insufficient — Jules needs the instruction in natural language too.

## Failure Modes & Mitigations

| Failure | Mitigation |
|---------|-----------|
| No PR created | Add explicit PR instruction to prompt |
| Modifies wrong files | Add "DO NOT modify existing files" to prompt |
| Session stuck (>30 min) | Check status, send a nudge message, or start new session |
| Tests fail in output | Pull diff, fix locally, push to PR branch |
| Imports wrong packages | Provide exact import paths in the prompt |
