import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baloot_ai/state/providers.dart';

void main() {
  test('Initial state has isFastForwarding=false', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final state = container.read(actionDispatcherProvider);
    expect(state.isFastForwarding, false);
  });

  test('enableFastForward sets isFastForwarding=true', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    container.read(actionDispatcherProvider.notifier).enableFastForward();

    final state = container.read(actionDispatcherProvider);
    expect(state.isFastForwarding, true);
  });

  test('disableFastForward sets isFastForwarding=false', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final notifier = container.read(actionDispatcherProvider.notifier);
    notifier.enableFastForward();
    expect(container.read(actionDispatcherProvider).isFastForwarding, true);

    notifier.disableFastForward();
    expect(container.read(actionDispatcherProvider).isFastForwarding, false);
  });
}
