---
description: Multi-agent coordination protocol (Antigravity ↔ Claude ↔ Jules)
---

# Multi-Agent Coordination Protocol

## Agents & Roles

| Agent | Role | Strengths |
|-------|------|-----------|
| **Claude** (MAX) | Architect | Multi-file refactors, system design, game theory, full-pipeline integration |
| **Antigravity** (Gemini) | Operator | Flutter MCP, browser QA, test runs, dashboard, file cleanup |
| **Jules** | Worker | Parallel file generation from specs, isolated new-file tasks |

---

## 1. Task Assignment Format

Claude writes tasks to `.agent/knowledge/tasks.md`. Antigravity polls this file during `/boot` or when asked to check for new tasks.

### Task File Format
```markdown
**Antigravity Tasks — [Mission Name]**

| # | Task | Command/Details |
|---|------|----------------|
| 1 | Description | `command` or details |

**Files to check:** (list)
**Commands:** (powershell block)
```

### Rules
- Claude marks completed tasks with ✅ prefix
- Antigravity updates the file with results (test counts, pass/fail)
- Each task has a clear success criterion

---

## 2. File Lock Convention

Before assigning Jules or any agent to modify files, check for active edits.

### Lock File: `.agent/knowledge/file_locks.md`

```markdown
| File | Agent | Since | Status |
|------|-------|-------|--------|
| action_dock.dart | Antigravity | 2026-02-18 | editing — do not touch |
```

### Rules
- **Claude**: Read locks before crafting Jules prompts. Add locked files to `FORBIDDEN_FILES`.
- **Antigravity**: Add locks when starting multi-step edits. Remove when done.
- **Jules**: Never receives locked files in its prompt. If Jules must touch a shared file, Claude must coordinate timing.

---

## 3. Jules Prompt Template

When Claude assigns Jules a task, use this structure to prevent conflicts:

```
## RULES
- DO NOT modify any existing files (only create new files)
- FORBIDDEN FILES (do not read or write):
  - [list of locked/recently-edited files]
- Only create the N new files listed below
- Run `cd mobile && flutter test` to verify all tests pass
- Match existing test/code style exactly

## CARD CREATION HELPER
[include any shared patterns]
```

### Anti-Conflict Rules for Jules
1. **New files only** — Jules should never modify existing files unless explicitly coordinated
2. **No import changes** — If Jules needs a new import in an existing file, flag it for Antigravity
3. **Run tests** — Jules must run `flutter test` before marking done
4. **No pubspec changes** — Flag dependency needs for Claude to review

---

## 4. Post-Merge Verification Checklist

After pulling Jules or Claude changes, Antigravity runs:

```powershell
# Step 1: Pull
git pull origin main

# Step 2: Analyze
// turbo
cd mobile && flutter analyze 2>&1 | Select-String -Pattern "error -|warning -"

# Step 3: Test
// turbo
cd mobile && flutter test

# Step 4: Check for regressions in previously-fixed files
git diff HEAD~1 -- [list of files Antigravity recently edited]
```

### If Step 4 shows reverted changes:
1. Re-apply Antigravity's fix
2. Log the conflict in task.md
3. Notify user with the diff

---

## 5. Conflict Resolution Protocol

### Priority Order
1. **Tests pass** — always the top priority
2. **Antigravity's fixes** take precedence over Jules' modifications to the same file
3. **Claude's architecture decisions** take precedence over both

### When Conflicts Happen
1. Antigravity re-applies its fix
2. Runs `flutter test` to verify
3. Logs: "Jules reverted [fix] in [file] — re-applied"
4. Reports to user in task summary

---

## 6. Communication Channels

| From → To | Method |
|-----------|--------|
| Claude → Antigravity | `.agent/knowledge/tasks.md` |
| Antigravity → Claude | Updated tasks.md with results, or user relays |
| Claude → Jules | `mcp_jules_create_session` with strict prompt |
| Jules → Antigravity | `mcp_jules_get_session_state` polling + code review |
| Antigravity → Jules | `mcp_jules_send_reply_to_session` (nudge/approve) |
