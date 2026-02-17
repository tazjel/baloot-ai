# Jules Task: M-F2 Pure Service Ports

## Overview
Port 4 TypeScript services to Dart for the Flutter mobile app.
All services are in `mobile/lib/services/`.

## Task 1: InventoryService (Port from frontend/src/services/InventoryService.ts)

Create `mobile/lib/services/inventory_service.dart`:
- Use `shared_preferences` package for persistence
- Store: owned items (Set<String>), equipped items (Map<String, String>)
- Methods: `getOwnedItems()`, `addOwnedItem(id)`, `getEquippedItem(category)`, `equipItem(category, id)`
- Keys: `baloot_owned_items`, `baloot_equipped_items`

## Task 2: PurchaseService (Port from frontend/src/services/PurchaseService.ts)

Create `mobile/lib/services/purchase_service.dart`:
- Pure Dart, no external deps
- Methods: `canAfford(price, balance) -> bool`, `processTransaction(price, balance) -> TransactionResult`, `generateReceipt(item, price) -> Receipt`
- Keep it simple — coins-based economy

## Task 3: HintService (Port from frontend/src/services/hintService.ts)

Create `mobile/lib/services/hint_service.dart`:
- Import from `mobile/lib/models/models.dart` and `mobile/lib/utils/game_logic.dart`
- Port `getHint(gameState) -> HintResult?` function
- Port `getBiddingHint(hand, mode, trumpSuit) -> HintResult`
- Port `getPlayingHint(hand, tableCards, mode, trumpSuit) -> HintResult`
- Arabic reasoning strings must be preserved exactly

## Task 4: DevLogger

Create `mobile/lib/services/dev_logger.dart`:
- Simple logging wrapper using `dart:developer`
- Methods: `info(msg)`, `warn(msg)`, `error(msg, [stackTrace])`
- Conditional: only log in debug mode

## Tests Required
Create test files in `mobile/test/services/` for each service.
Target: 15+ tests total.

## Rules
- Import models from `package:baloot_ai/models/models.dart`
- Import utils from `package:baloot_ai/utils/game_logic.dart`
- Pure functions preferred, no classes unless needed for state
- Use `dart:developer` log, not `print()`
