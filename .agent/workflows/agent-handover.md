# Agent Handover Protocol

To delegate tasks from Claude to Antigravity (me), use this file:
**`.agent/delegations/INBOX.md`**

## 1. Claude's Role
Claude should write a checklist of tasks to this file in the following format:

```markdown
# Mission: [Mission Name]
> Status: PENDING

## Context
[Brief context on what needs to be done]

## Tasks
- [ ] Create file `lib/new_feature.dart`
- [ ] Refactor `backend/api.py` to add endpoint X
- [ ] Run tests for module Y
```

## 2. Antigravity's Role
1. I will check `.agent/delegations/INBOX.md`.
2. If `Status: PENDING` is found:
   - I will Parse the tasks.
   - I will Execute them one by one.
   - I will Mark them as `[x]`.
   - I will Update status to `DONE`.

## 3. How to Trigger
- **User**: "Claude has updated the inbox. Go execute."
- **Me**: I look at the file and start working.
