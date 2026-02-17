---
description: Analyze the codebase structure and key files
---

1. List all files in the frontend and server directories to get an overview.
// turbo
2. run_command `find_by_name . -MaxDepth 2 -SearchDirectory c:\Users\MiEXCITE\Projects\baloot-ai`
3. Read the `package.json` files to understand dependencies.
// turbo
4. view_file `c:\Users\MiEXCITE\Projects\baloot-ai\frontend\package.json`
// turbo
5. view_file `c:\Users\MiEXCITE\Projects\baloot-ai\server\package.json`
6. Check for any TODOs or FIXMEs in the code.
// turbo
7. Use the `grep_search` tool to look for "TODO", "FIXME", or "HACK" in the codebase.
8. If `mobile` directory exists, suggest running `/analyze-flutter` for deep Dart analysis.
// turbo
9. view_file `c:\Users\MiEXCITE\Projects\baloot-ai\mobile\pubspec.yaml`
