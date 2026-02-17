---
description: analyze flutter codebase structure and quality using mcp tools
---

# /analyze-flutter - Deep Static Analysis

Use the Dart MCP server to perform comprehensive analysis of the Flutter codebase.

## 1. Static Analysis
// turbo
Run the analyzer on the `mobile` directory:
```bash
dart mcp-server --analyze mobile
```

## 2. Widget Tree Inspection
If the app is running:
1. Connect to the device using `mcp_dart_connect_dart_tooling_daemon`.
2. Retrieve the widget tree: `mcp_dart_get_widget_tree`.
3. Inspect specific widgets: `mcp_dart_get_selected_widget`.

## 3. Dependency Audit
Check for outdated packages:
```bash
cd mobile
flutter pub outdated
```

## 4. Fix Issues
Automatically apply safe fixes:
```bash
cd mobile
dart fix --apply
```
