---
description: streamlined mobile development workflow using Flutter and Dart MCP tools
---

# /mobile-dev - Flutter Development Workflow

Efficiently manage Flutter tasks, analysis, and testing using the Dart MCP server and standard CLI tools.

## 1. Dependency Management
// turbo
Update dependencies to ensure a clean state.
```bash
cd mobile
flutter pub get
```

## 2. Static Analysis (MCP Enhanced)
Use the Dart MCP server to analyze the project for errors and lint warnings.

1. **Analyze Project**:
   - Use `mcp_dart_analyze_files` on `mobile/lib`.
   - Review output for errors/warnings.

2. **Auto-Fix (Optional)**:
   - If minor formatting/lint issues exist, use `mcp_dart_dart_fix`.
   - **Command**: `dart fix --apply` (via MCP or shell).

## 3. Testing
Run tests to verify changes.

### Unit/Widget Tests
// turbo
```bash
cd mobile
flutter test
```

### Integration Tests (Optional)
If valid device connected:
```bash
cd mobile
flutter test integration_test
```

## 4. Build Verification
Ensure the app builds correctly.

// turbo
```bash
cd mobile
flutter build apk --debug
```

## 5. Dev Tools (MCP)
Leverage these MCP tools for deeper debugging:
- `mcp_dart_get_widget_tree`: Inspect UI hierarchy.
- `mcp_dart_get_runtime_errors`: Check active errors.
- `mcp_dart_hot_reload`: Trigger reload on connected device.
