/// shop_notifier.dart — Store management with persistence.
///
/// Port of frontend/src/hooks/useShop.ts (53 lines).
///
/// Manages owned and equipped cosmetic items (card backs, table skins).
/// Persists inventory to shared_preferences.
///
/// ## Item Types
/// - Card backs: visual card back designs
/// - Table skins: table felt textures/colors
library;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Cosmetic item category.
enum ItemCategory { cardBack, tableSkin }

/// A purchasable cosmetic item.
class ShopItem {
  final String id;
  final String name;
  final ItemCategory category;
  final int price;
  final String assetPath;

  const ShopItem({
    required this.id,
    required this.name,
    required this.category,
    required this.price,
    required this.assetPath,
  });
}

/// Store state: owned items and equipped selections.
class ShopState {
  /// Set of owned item IDs.
  final Set<String> ownedItems;

  /// Currently equipped card back ID.
  final String equippedCardBack;

  /// Currently equipped table skin ID.
  final String equippedTableSkin;

  /// User's coin balance.
  final int coins;

  const ShopState({
    this.ownedItems = const {},
    this.equippedCardBack = 'default',
    this.equippedTableSkin = 'default',
    this.coins = 1000,
  });

  ShopState copyWith({
    Set<String>? ownedItems,
    String? equippedCardBack,
    String? equippedTableSkin,
    int? coins,
  }) {
    return ShopState(
      ownedItems: ownedItems ?? this.ownedItems,
      equippedCardBack: equippedCardBack ?? this.equippedCardBack,
      equippedTableSkin: equippedTableSkin ?? this.equippedTableSkin,
      coins: coins ?? this.coins,
    );
  }
}

/// Manages store inventory, purchases, and equipped items.
///
/// Persists state to shared_preferences on changes.
class ShopNotifier extends StateNotifier<ShopState> {
  ShopNotifier() : super(const ShopState()) {
    _loadFromPrefs();
  }

  Future<void> _loadFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final owned = prefs.getStringList('shop_owned') ?? [];
      final cardBack = prefs.getString('shop_cardBack') ?? 'default';
      final tableSkin = prefs.getString('shop_tableSkin') ?? 'default';
      final coins = prefs.getInt('shop_coins') ?? 1000;

      if (mounted) {
        state = ShopState(
          ownedItems: owned.toSet(),
          equippedCardBack: cardBack,
          equippedTableSkin: tableSkin,
          coins: coins,
        );
      }
    } catch (_) {
      // Ignore storage errors, use defaults
    }
  }

  Future<void> _saveToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('shop_owned', state.ownedItems.toList());
      await prefs.setString('shop_cardBack', state.equippedCardBack);
      await prefs.setString('shop_tableSkin', state.equippedTableSkin);
      await prefs.setInt('shop_coins', state.coins);
    } catch (_) {
      // Ignore storage errors
    }
  }

  /// Purchase an item if the player can afford it.
  ///
  /// Returns true if purchase succeeded, false if insufficient funds
  /// or already owned.
  bool purchase(ShopItem item) {
    if (state.ownedItems.contains(item.id)) return false;
    if (state.coins < item.price) return false;

    state = state.copyWith(
      ownedItems: {...state.ownedItems, item.id},
      coins: state.coins - item.price,
    );
    _saveToPrefs();
    return true;
  }

  /// Equip an owned item.
  void equip(String itemId, ItemCategory category) {
    if (!state.ownedItems.contains(itemId) && itemId != 'default') return;

    switch (category) {
      case ItemCategory.cardBack:
        state = state.copyWith(equippedCardBack: itemId);
        break;
      case ItemCategory.tableSkin:
        state = state.copyWith(equippedTableSkin: itemId);
        break;
    }
    _saveToPrefs();
  }

  /// Add coins (from match rewards, etc.).
  void addCoins(int amount) {
    state = state.copyWith(coins: state.coins + amount);
    _saveToPrefs();
  }

  /// Check if player owns an item.
  bool isOwned(String itemId) => state.ownedItems.contains(itemId);

  /// Check if player can afford an item.
  bool canAfford(int price) => state.coins >= price;
}

final shopProvider =
    StateNotifierProvider<ShopNotifier, ShopState>((ref) {
  return ShopNotifier();
});
