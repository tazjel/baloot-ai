# Agent Rules

1. **OS Compatibility**: The user is on **Windows**.
    - DO NOT use `grep`, `ls`, `cat`, `touch`, `rm` via `run_command`.
    - Use MCP tools like `grep_search`, `find_by_name`, `read_text_file` whenever possible.
    - If you MUST use a shell command, use PowerShell syntax (e.g., `Select-String`, `Get-ChildItem`).

2. **Efficiency**:
    - Do not run `grep` or `find` on the entire `node_modules` or `.git` directories. Always exclude them.
    - Use `// turbo` in workflows only for safe, side-effect-free commands.

3. **Codebase Awareness**:
    - The project uses Python (Backend) and React/TypeScript (Frontend).
    - Tests are run via `python run_test_suite.py` and `npm test`.

4. **Architecture**:
    - **Shared Constants**: Enums for Game State (`BiddingPhase`, `BidType`, `GamePhase`) MUST live in `game_engine/models/constants.py`.
    - **Do NOT** define these Enums in `server/` or `ai_worker/` files. Always import them.

5. **Identity & Conversation**:
    - **Rule**: Always sign your response with BOTH your Agent Name and Model Name at the very end of your reply or conversation.
    - **Format**: Enclosed in square brackets in the format `[AgentName (ModelName)]`, e.g., `[Antigravity (Gemini 2.0 Flash)]`.
    - **Implementation**: You MUST include both. If the Model Name is not explicitly known, make a best-effort identification or use generic model family names (e.g., `(Gemini)`).
