---
description: reference guide for available mcp tools and usage
---

# /mcp - MCP Tool Reference

Guide to using the active Model Context Protocol (MCP) servers and tools.

## 1. Flutter & Dart (Server: `dart`)
- **Analysis**: `mcp_dart_analyze_files` (static analysis), `mcp_dart_get_runtime_errors`.
- **Inspection**: `mcp_dart_get_widget_tree`, `mcp_dart_get_selected_widget`.
- **Management**: `mcp_dart_pub` (dependencies), `mcp_dart_dart_fix` (auto-fixes).
- **Execution**: `mcp_dart_hot_reload`, `mcp_dart_hot_restart`.

## 2. Browser Automation (Server: `playwright`)
- **Control**: `mcp_playwright_browser_navigate`, `mcp_playwright_browser_click`, `mcp_playwright_browser_type`.
- **Inspection**: `mcp_playwright_browser_take_screenshot`, `mcp_playwright_browser_console_messages`.

## 3. Stitch (Server: `stitch`)
- **Prototyping**: `mcp_stitch_generate_screen_from_text`, `mcp_stitch_edit_screens`.
- **Management**: `mcp_stitch_list_projects`, `mcp_stitch_get_screen`.

## 4. Jules (Server: `jules`)
- **Delegation**: `mcp_jules_create_session`, `mcp_jules_get_session_state`.
- **Review**: `mcp_jules_get_code_review_context`, `mcp_jules_show_code_diff`.

## 5. Usage Tips
- **Always** use `dart` tools for file analysis instead of `grep` when working in `mobile/`.
- **Always** use `playwright` for end-to-end testing verification.
- Use `jules` for creating PRs and managing complex async tasks.
