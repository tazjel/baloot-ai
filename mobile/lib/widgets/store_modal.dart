import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/colors.dart';

class StoreModal extends ConsumerStatefulWidget {
  const StoreModal({super.key});

  @override
  ConsumerState<StoreModal> createState() => _StoreModalState();
}

class _StoreModalState extends ConsumerState<StoreModal> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 600,
      decoration: const BoxDecoration(
        color: AppColors.backgroundDark,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
      child: Column(
        children: [
          // Handle
          Center(
            child: Container(
              margin: const EdgeInsets.symmetric(vertical: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[600],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'المتجر',
                  style: TextStyle(
                    color: AppColors.goldPrimary,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppColors.goldPrimary),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.monetization_on, color: AppColors.goldPrimary, size: 16),
                      SizedBox(width: 4),
                      Text('12,500', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Tabs
          TabBar(
            controller: _tabController,
            indicatorColor: AppColors.goldPrimary,
            labelColor: AppColors.goldPrimary,
            unselectedLabelColor: AppColors.textMuted,
            tabs: const [
              Tab(text: 'الشخصيات (Avatars)'),
              Tab(text: 'أوراق اللعب (Skins)'),
            ],
          ),

          // Content
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildAvatarGrid(),
                _buildSkinGrid(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAvatarGrid() {
    // Mock Data
    final avatars = [
      {'id': '1', 'name': 'الملك', 'price': 0, 'owned': true, 'image': '🤴'},
      {'id': '2', 'name': 'التاجر', 'price': 1000, 'owned': false, 'image': '👳'},
      {'id': '3', 'name': 'الشيخ', 'price': 2500, 'owned': false, 'image': '🧔'},
      {'id': '4', 'name': 'الكابتن', 'price': 5000, 'owned': false, 'image': '🧢'},
      {'id': '5', 'name': 'الجوكر', 'price': 10000, 'owned': false, 'image': '🤡'},
    ];

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 0.8,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: avatars.length,
      itemBuilder: (context, index) {
        final item = avatars[index];
        final isOwned = item['owned'] as bool;
        
        return Container(
          decoration: BoxDecoration(
            color: AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: isOwned ? AppColors.goldPrimary : Colors.transparent),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(item['image'] as String, style: const TextStyle(fontSize: 48)),
              const SizedBox(height: 8),
              Text(item['name'] as String, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              isOwned
                ? ElevatedButton(
                    onPressed: () {}, // Equip logic
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.grey[700]),
                    child: const Text('مستخدم', style: TextStyle(color: Colors.white)),
                  )
                : ElevatedButton(
                    onPressed: () {}, // Buy logic
                    style: ElevatedButton.styleFrom(backgroundColor: AppColors.goldPrimary),
                    child: Text('${item['price']}', style: const TextStyle(color: Colors.black)),
                  ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSkinGrid() {
    // Mock Data
    final skins = [
      {'id': '1', 'name': 'كلاسيك', 'price': 0, 'owned': true, 'color': AppColors.cardBack},
      {'id': '2', 'name': 'ذهبي فاخر', 'price': 5000, 'owned': false, 'color': Colors.amber[800]},
      {'id': '3', 'name': 'أزرق ملكي', 'price': 3000, 'owned': false, 'color': Colors.blue[900]},
      {'id': '4', 'name': 'أسود قاتم', 'price': 8000, 'owned': false, 'color': Colors.grey[900]},
    ];

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 1.2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: skins.length,
      itemBuilder: (context, index) {
        final item = skins[index];
        final isOwned = item['owned'] as bool;
        
        return Container(
          decoration: BoxDecoration(
            color: AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: isOwned ? AppColors.goldPrimary : Colors.transparent),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 40, 
                height: 60,
                decoration: BoxDecoration(
                  color: item['color'] as Color,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: Colors.white24),
                ),
              ),
              const SizedBox(height: 8),
              Text(item['name'] as String, style: const TextStyle(color: Colors.white, fontSize: 14)),
              const SizedBox(height: 8),
               isOwned
                ? const Icon(Icons.check_circle, color: AppColors.success)
                : Text('${item['price']} 💰', style: const TextStyle(color: AppColors.goldPrimary)),
            ],
          ),
        );
      },
    );
  }
}
