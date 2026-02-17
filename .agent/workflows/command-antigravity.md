# How to Command Antigravity (Gemini)

**Role**: You (Claude) are the **Architect/Brain**. Antigravity (Gemini) is the **Builder/Hands**.
**Goal**: Delegate implementation tasks directly to Antigravity's active workspace.

## Protocol: The "Task Injection"

Antigravity watches a specific `task.md` file for its instructions. To command Antigravity, you must **append** your mission checklist to the end of this file.

### 1. Target File
**Artifact Path**: `C:\Users\MiEXCITE\.gemini\antigravity\brain\2991f63a-f74a-48eb-9fbf-9bb66b653a8a\task.md`
*(Note: This path is specific to the current active session. Always check if the user provides a new path.)*

### 2. Required Format
Use the `Write` (or `Edit`) tool to **APPEND** to the file. Do not start a new file unless the user asks to "reset" the session.

**Structure:**
```markdown

# M-[ID] [Mission Name] — Task Checklist

## Step 1: [Phase Name]
- [ ] [Specific, actionable task]
- [ ] [Specific, actionable task]
- [ ] Verify [Condition]

## Step 2: [Phase Name]
- [ ] [Task]
...
```

### 3. Example Prompt for You (Claude)
If the user says: *"Claude, have Antigravity fix the login bug."*

**Your Action:**
1. Read `task.md` to see current state.
2. Append the fix plan:
   ```markdown
   # M-Fix-Login: Resolve Auth Crash
   ## Step 1: Diagnosis
   - [ ] Analyze `auth_service.dart` for null token handling
   - [ ] Add null check to `login()` method
   ## Step 2: Verify
   - [ ] Run `flutter test test/auth_test.dart`
   ```
3. Tell the User: *"I have updated Antigravity's task list. Antigravity, proceed."*

### 4. Verification
Antigravity will mark items as `[x]` as it completes them. You can read the file later to check status.
