import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:baloot_ai/services/inventory_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('InventoryService', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('getOwnedItems returns default items if empty', () async {
      final items = await InventoryService.getOwnedItems();
      expect(items, contains('card_default'));
      expect(items, contains('table_default'));
    });

    test('addOwnedItem adds item correctly', () async {
      await InventoryService.addOwnedItem('new_item');
      final items = await InventoryService.getOwnedItems();
      expect(items, contains('new_item'));
    });

    test('getOwnedItems persists data', () async {
       await InventoryService.addOwnedItem('persistent_item');
       // Re-read
       final items = await InventoryService.getOwnedItems();
       expect(items, contains('persistent_item'));
    });

    test('getEquippedItem returns default for unknown', () async {
      final card = await InventoryService.getEquippedItem('card');
      expect(card, 'card_default');
    });

    test('equipItem updates preference', () async {
      await InventoryService.equipItem('new_card_skin', 'card');
      final card = await InventoryService.getEquippedItem('card');
      expect(card, 'new_card_skin');
    });

    test('equipItem keeps other types', () async {
      await InventoryService.equipItem('new_card_skin', 'card');
      await InventoryService.equipItem('new_table_skin', 'table');

      final card = await InventoryService.getEquippedItem('card');
      final table = await InventoryService.getEquippedItem('table');

      expect(card, 'new_card_skin');
      expect(table, 'new_table_skin');
    });
  });
}
