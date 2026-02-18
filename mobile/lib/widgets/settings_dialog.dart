import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app.dart';
import '../core/theme/colors.dart';
import '../services/sound_service.dart';

class SettingsDialog extends ConsumerStatefulWidget {
  const SettingsDialog({super.key});

  @override
  ConsumerState<SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends ConsumerState<SettingsDialog> {
  late SoundService _sound;
  late bool _isMuted;
  final Map<String, double> _volumes = {};

  @override
  void initState() {
    super.initState();
    _sound = SoundService();
    _isMuted = _sound.isMuted;
    _volumes['cards'] = _sound.getVolume('cards');
    _volumes['ui'] = _sound.getVolume('ui');
    _volumes['events'] = _sound.getVolume('events');
    _volumes['bids'] = _sound.getVolume('bids');
  }

  void _toggleMute(bool val) {
    setState(() => _isMuted = val);
    _sound.setMute(val);
  }

  void _updateVolume(String category, double val) {
    setState(() => _volumes[category] = val);
    _sound.setVolume(category, val);
  }

  @override
  Widget build(BuildContext context) {
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == ThemeMode.dark ||
        (themeMode == ThemeMode.system &&
            MediaQuery.platformBrightnessOf(context) == Brightness.dark);

    return AlertDialog(
      title: const Text('إعدادات اللعبة'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Theme toggle
            SwitchListTile(
              title: const Text('الوضع الليلي'),
              secondary: Icon(
                isDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
                color: AppColors.goldPrimary,
              ),
              value: isDark,
              activeColor: AppColors.goldPrimary,
              onChanged: (val) {
                ref.read(themeModeProvider.notifier).setTheme(
                      val ? ThemeMode.dark : ThemeMode.light,
                    );
              },
            ),
            const Divider(),
            // Sound mute
            SwitchListTile(
              title: const Text('كتم الصوت'),
              secondary: Icon(
                _isMuted ? Icons.volume_off_rounded : Icons.volume_up_rounded,
                color: _isMuted ? AppColors.textMuted : AppColors.goldPrimary,
              ),
              value: _isMuted,
              onChanged: _toggleMute,
            ),
            const Divider(),
            const Text('مستوى الصوت', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            _VolumeSlider(label: 'المؤثرات', val: _volumes['events']!, onChanged: (v) => _updateVolume('events', v)),
            _VolumeSlider(label: 'البطاقات', val: _volumes['cards']!, onChanged: (v) => _updateVolume('cards', v)),
            _VolumeSlider(label: 'الأصوات', val: _volumes['ui']!, onChanged: (v) => _updateVolume('ui', v)),
            _VolumeSlider(label: 'المزايدات', val: _volumes['bids']!, onChanged: (v) => _updateVolume('bids', v)),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('إغلاق'),
        ),
      ],
    );
  }
}

class _VolumeSlider extends StatelessWidget {
  final String label;
  final double val;
  final ValueChanged<double> onChanged;

  const _VolumeSlider({required this.label, required this.val, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(width: 80, child: Text(label)),
        Expanded(
          child: Slider(
            value: val,
            onChanged: onChanged,
          ),
        ),
      ],
    );
  }
}
