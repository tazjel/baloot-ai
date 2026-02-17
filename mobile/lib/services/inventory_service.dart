import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class InventoryService {
  static const String _ownedKey = 'baloot_owned_items';
  static const String _equippedKey = 'baloot_equipped_items';

  /// Get list of owned item IDs.
  static Future<Set<String>> getOwnedItems() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_ownedKey);
    if (saved != null) {
      final List<dynamic> list = jsonDecode(saved);
      return list.cast<String>().toSet();
    }
    return {'card_default', 'table_default'};
  }

  /// Add an item to owned list.
  static Future<void> addOwnedItem(String itemId) async {
    final items = await getOwnedItems();
    if (items.add(itemId)) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_ownedKey, jsonEncode(items.toList()));
    }
  }

  /// Get currently equipped item ID for a given type (e.g., 'card', 'table').
  static Future<String> getEquippedItem(String type) async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_equippedKey);
    final Map<String, dynamic> map = saved != null
        ? jsonDecode(saved)
        : {'card': 'card_default', 'table': 'table_default'};

    return map[type] as String? ?? (type == 'card' ? 'card_default' : 'table_default');
  }

  /// Equip an item of a given type.
  static Future<void> equipItem(String itemId, String type) async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_equippedKey);
    final Map<String, dynamic> current = saved != null
        ? jsonDecode(saved)
        : {'card': 'card_default', 'table': 'table_default'};

    current[type] = itemId;
    await prefs.setString(_equippedKey, jsonEncode(current));
  }
}
