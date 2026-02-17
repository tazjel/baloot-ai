class PurchaseService {
  /// Check if user can afford the item.
  static bool canAfford(int coins, int cost) {
    return coins >= cost;
  }

  /// Process transaction and return new coin balance.
  /// Throws Exception if insufficient funds.
  static int processTransaction(int currentCoins, int cost) {
    if (currentCoins < cost) {
      throw Exception('Insufficient funds');
    }
    return currentCoins - cost;
  }

  /// Generate receipt string.
  static String generateReceipt(String itemId, int cost, int remainingCoins) {
    return 'Purchased $itemId for $cost. Remaining balance: $remainingCoins';
  }
}
