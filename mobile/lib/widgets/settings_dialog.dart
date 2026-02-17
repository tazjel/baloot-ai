import 'package:flutter/material.dart';
import '../services/sound_service.dart';

class SettingsDialog extends StatefulWidget {
  const SettingsDialog({super.key});

  @override
  State<SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends State<SettingsDialog> {
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
    return AlertDialog(
      title: const Text('إعدادات اللعبة'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SwitchListTile(
              title: const Text('كتم الصوت'),
              value: _isMuted,
              onChanged: _toggleMute,
            ),
            const Divider(),
            const Text('مستوى الصوت', style: TextStyle(fontWeight: FontWeight.bold)),
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
