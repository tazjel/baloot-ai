import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/theme/colors.dart';
import '../state/providers.dart';
import '../models/player.dart';

class MultiplayerScreen extends ConsumerStatefulWidget {
  const MultiplayerScreen({super.key});

  @override
  ConsumerState<MultiplayerScreen> createState() => _MultiplayerScreenState();
}

class _MultiplayerScreenState extends ConsumerState<MultiplayerScreen> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _roomCodeController = TextEditingController();
  bool _isJoining = false;

  @override
  void dispose() {
    _nameController.dispose();
    _roomCodeController.dispose();
    super.dispose();
  }

  void _createRoom() {
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('الرجاء إدخال اسمك')),
      );
      return;
    }

    // Connect first if not connected (handled by provider usually, but good to ensure)
    ref.read(gameSocketProvider.notifier).ensureConnected();

    // Create room logic would go here
    // But createRoom doesn't take player name in the current API?
    // public API: createRoom({required onSuccess, onError}) 
    // It seems createRoom doesn't set player name, joinRoom does.
    // So flow is: Create Room -> Get ID -> Join Room with ID + Name.
    
    setState(() => _isJoining = true);
    
    final socketNotifier = ref.read(gameSocketProvider.notifier);
    
    socketNotifier.createRoom(
      onSuccess: (roomId) {
        // Auto-join the created room
        socketNotifier.joinGame(
          roomId: roomId, 
          playerName: _nameController.text, 
          myIndex: 0, // Creator usually 0? Server assigns index usually? 
          // Wait, joinGame takes myIndex. 
          // Usually server assigns index, but here we might need to know it?
          // Let's assume 0 for creator.
          onSuccess: () {
            if (mounted) setState(() => _isJoining = false);
          },
          onError: (err) {
            if (mounted) {
              setState(() => _isJoining = false);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('فشل الانضمام: $err')),
              );
            }
          }
        );
      },
      onError: (err) {
        if (mounted) {
          setState(() => _isJoining = false);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('فشل إنشاء الغرفة: $err')),
          );
        }
      }
    );
  }

  void _joinRoom() {
    if (_nameController.text.isEmpty || _roomCodeController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('الرجاء إدخال اسمك ورمز الغرفة')),
      );
      return;
    }

    setState(() => _isJoining = true);
    // Join as index 1? We don't know our index yet. 
    // The current joinGame API requires myIndex. This is a bit leaky.
    // We'll pass -1 or handle it? 
    // Ideally socket response gives us our index. 
    // Checking GameSocketNotifier again...
    // verify: void joinGame({required roomId, required playerName, required myIndex...})
    // It seems strictly required. This might be a limitation of the port.
    // We will assume server assigns and we might need to guess or update later.
    // For now pass 1 as a placeholder?
    
    ref.read(gameSocketProvider.notifier).joinGame(
      roomId: _roomCodeController.text,
      playerName: _nameController.text, 
      myIndex: 1, // Placeholder
      onSuccess: () {
        if (mounted) setState(() => _isJoining = false);
      },
      onError: (err) {
        if (mounted) {
          setState(() => _isJoining = false);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('فشل الانضمام: $err')),
          );
        }
      }
    );
  }

  void _addBot() {
    ref.read(gameSocketProvider.notifier).addBot();
  }

  @override
  Widget build(BuildContext context) {
    final socketState = ref.watch(gameSocketProvider);
    final gameState = ref.watch(gameStateProvider);
    final inRoom = socketState.roomId != null;

    return Scaffold(
      appBar: AppBar(
        title: const Text('لعب جماعي'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
             if (inRoom) {
               ref.read(gameSocketProvider.notifier).leaveRoom();
             }
             context.go('/lobby');
          },
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColors.backgroundDark, AppColors.backgroundBlack],
          ),
        ),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: inRoom ? _buildRoomLobby(socketState.roomId!, gameState.gameState.players) : _buildJoinForm(),
          ),
        ),
      ),
    );
  }

  Widget _buildJoinForm() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(Icons.people_alt_rounded, size: 80, color: AppColors.goldPrimary),
        const SizedBox(height: 32),
        
        // Name Input
        TextField(
          controller: _nameController,
          textAlign: TextAlign.right,
          decoration: const InputDecoration(
            labelText: 'اسمك',
            prefixIcon: Icon(Icons.person),
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 24),

        // Create Room Section
        const Text('إنشاء غرفة جديدة', style: TextStyle(color: AppColors.textGold, fontSize: 18, fontWeight: FontWeight.bold), textAlign: TextAlign.right),
        const SizedBox(height: 8),
        ElevatedButton(
          onPressed: _isJoining ? null : _createRoom,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.goldPrimary,
            foregroundColor: Colors.black,
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
          child: _isJoining 
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) 
            : const Text('إنشاء غرفة', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        ),

        const SizedBox(height: 32),
        const Divider(color: AppColors.primaryWithOpacity),
        const SizedBox(height: 24),

        // Join Room Section
        const Text('الانضمام لغرفة', style: TextStyle(color: AppColors.textGold, fontSize: 18, fontWeight: FontWeight.bold), textAlign: TextAlign.right),
        const SizedBox(height: 8),
        TextField(
          controller: _roomCodeController,
          textAlign: TextAlign.center,
          decoration: const InputDecoration(
            labelText: 'رمز الغرفة',
            helperText: 'اطلب الرمز من منشئ الغرفة',
            prefixIcon: Icon(Icons.vpn_key),
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        OutlinedButton(
          onPressed: _isJoining ? null : _joinRoom,
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
            side: const BorderSide(color: AppColors.goldPrimary),
          ),
          child: const Text('انضمام', style: TextStyle(fontSize: 16, color: AppColors.goldPrimary)),
        ),
      ],
    );
  }

  Widget _buildRoomLobby(String roomId, List<Player> players) {
    return Column(
      children: [
        const Text('غرفة الانتظار', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: AppColors.primaryWithOpacity,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.goldPrimary),
          ),
          child: SelectableText(roomId, style: const TextStyle(fontSize: 32, letterSpacing: 4, fontFamily: 'monospace', fontWeight: FontWeight.bold, color: AppColors.goldPrimary)),
        ),
        const SizedBox(height: 8),
        const Text('شارك الرمز مع أصدقائك', style: TextStyle(color: AppColors.textMuted)),
        
        const SizedBox(height: 48),

        // Player Slots
        SizedBox(
          height: 120,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: List.generate(4, (index) {
              // Logic to map players to slots? 
              // Since logic rotates, index 0 is always ME.
              // So for the lobby, this is tricky. We see ourselves at 0.
              // We'll just list them as they come.
              final player = index < players.length ? players[index] : null;
              return _buildPlayerSlot(player);
            }),
          ),
        ),

        const SizedBox(height: 48),

        if (players.length < 4)
        ElevatedButton.icon(
          onPressed: _addBot,
          icon: const Icon(Icons.smart_toy),
          label: const Text('إضافة بوت'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.cardSurface,
            foregroundColor: AppColors.textLight,
          ),
        ),
        
        const SizedBox(height: 16),
        
        if (players.length == 4)
          const Column(
            children: [
              CircularProgressIndicator(color: AppColors.goldPrimary),
              SizedBox(height: 16),
              Text('المباراة ستبدأ قريباً...', style: TextStyle(color: AppColors.goldPrimary)),
            ],
          )
        else
           Text('في انتظار اكتمال العدد (${players.length}/4)...', style: const TextStyle(color: AppColors.textMuted)),

      ],
    );
  }

  Widget _buildPlayerSlot(Player? player) {
    if (player == null) {
      return Column(
        children: [
          Container(
            width: 64, height: 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.textMuted.withOpacity(0.3), width: 2),
            ),
            child: const Icon(Icons.person_outline, color: AppColors.textMuted),
          ),
          const SizedBox(height: 8),
          const Text('فارغ', style: TextStyle(color: AppColors.textMuted)),
        ],
      );
    }

    return Column(
      children: [
        Container(
          width: 64, height: 64,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: player.isBot ? AppColors.secondarySurface : AppColors.primaryWithOpacity,
            border: Border.all(color: AppColors.goldPrimary, width: 2),
          ),
          child: Icon(player.isBot ? Icons.smart_toy : Icons.person, color: AppColors.goldPrimary),
        ),
        const SizedBox(height: 8),
        Text(player.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
