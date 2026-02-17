import 'package:flutter_test/flutter_test.dart';
import 'package:baloot_ai/services/purchase_service.dart';

void main() {
  group('PurchaseService', () {
    test('canAfford returns true if sufficient funds', () {
      expect(PurchaseService.canAfford(100, 50), isTrue);
      expect(PurchaseService.canAfford(100, 100), isTrue);
    });

    test('canAfford returns false if insufficient funds', () {
      expect(PurchaseService.canAfford(50, 100), isFalse);
    });

    test('processTransaction deducts cost correctly', () {
      expect(PurchaseService.processTransaction(100, 50), 50);
    });

    test('processTransaction throws on insufficient funds', () {
      expect(
        () => PurchaseService.processTransaction(50, 100),
        throwsA(isA<Exception>()),
      );
    });

    test('generateReceipt creates correct string', () {
      final receipt = PurchaseService.generateReceipt('item_1', 50, 50);
      expect(receipt, contains('item_1'));
      expect(receipt, contains('50'));
    });
  });
}
