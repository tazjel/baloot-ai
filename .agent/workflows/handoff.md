---
description: Update all documentation and record session lessons/tips for the next agent session (Alias for /finalize-session).
---

# Session Handoff

Write a summary of the current session to `.agent/knowledge/handoff.md` before switching tools or ending work.

## When to Use

- **Before leaving Antigravity** to work in Claude Desktop
- **Before leaving Claude Desktop** to work in Antigravity
- **Before ending a long session** (even if not switching tools)
- **When hitting usage limits** (quick handoff before timeout)

## Steps

### 1. Gather Session Info

- What files were modified?
- What was accomplished?
- What's the current state (committed? tested? broken?)
- What should be done next?

### 2. Update Handoff File

// turbo
- Read `.agent/knowledge/handoff.md` for the current template.
- Update all sections with current session info.
- Be concise but complete.

### 3. Commit (Optional but Recommended)

If there are uncommitted changes:
```powershell
git add -A
git commit -m "wip: Session handoff checkpoint"
```

### 4. Confirm to User

Tell the user:
- "Handoff complete. Ready to switch tools."
- Summarize the key points for quick verbal handoff.

---

## Quick Handoff (Emergency)

If running out of time/tokens, write at minimum:

```markdown
## Last Updated
- **Tool**: [Tool Name]
- **Time**: [Now]

## Current State
- [One-liner: committed/uncommitted, working/broken]

## Next Steps
1. [Most important next action]
```

---

## For Claude Desktop Users

Copy this prompt to use in Claude Desktop before ending:

> Please write a session handoff summary to `.agent/knowledge/handoff.md` with:
> - What you did
> - Files modified
> - Current state
> - Next steps
> - Any gotchas discovered
