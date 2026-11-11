import 'package:flutter/material.dart';
import '../services/api.dart';
import 'shared.dart';
import 'wardrobe.dart';
import 'outfits.dart';
import 'profile.dart';
import 'extras.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({required this.api, required this.toggleTheme, super.key});
  final LooksyApi api;
  final VoidCallback toggleTheme;
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int tab = 0;
  int revision = 0;
  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeTab(api: widget.api, create: () => setState(() => tab = 2)),
      WardrobePage(api: widget.api),
      CreatePage(api: widget.api),
      OutfitsPage(api: widget.api, savedOnly: true),
      ProfilePage(api: widget.api, toggleTheme: widget.toggleTheme),
    ];
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(
              Icons.auto_awesome,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(width: 9),
            const Text(
              'looksy.',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'AI-стилист',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => StylistPage(api: widget.api)),
            ),
            icon: const Icon(Icons.chat_bubble_outline),
          ),
          IconButton(
            tooltip: 'Календарь',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => CalendarPage(api: widget.api)),
            ),
            icon: const Icon(Icons.calendar_month_outlined),
          ),
          IconButton(
            tooltip: 'Обновить',
            onPressed: () => setState(() => revision++),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: KeyedSubtree(key: ValueKey('$tab-$revision'), child: pages[tab]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: (value) => setState(() => tab = value),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Главная',
          ),
          NavigationDestination(
            icon: Icon(Icons.checkroom_outlined),
            label: 'Гардероб',
          ),
          NavigationDestination(
            icon: Icon(Icons.auto_awesome_outlined),
            label: 'Образ',
          ),
          NavigationDestination(
            icon: Icon(Icons.favorite_border),
            selectedIcon: Icon(Icons.favorite),
            label: 'Избранное',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            label: 'Профиль',
          ),
        ],
      ),
    );
  }
}

class HomeTab extends StatefulWidget {
  const HomeTab({required this.api, required this.create, super.key});
  final LooksyApi api;
  final VoidCallback create;
  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends RemoteState<HomeTab> {
  @override
  Future<Json> load() async {
    final data = await Future.wait([
      widget.api.request('/api/profile/'),
      widget.api.request('/api/clothing/summary/'),
      widget.api.collection('/api/outfits/'),
      widget.api.collection('/api/saved-outfits/'),
    ]);
    return {
      'profile': data[0],
      'summary': data[1],
      'outfits': data[2],
      'saved': data[3],
    };
  }

  @override
  Widget build(BuildContext context) => remote((data) {
    final profile = data['profile'] as Json;
    final outfits = (data['outfits'] as List).cast<Json>();
    return ListView(
      padding: const EdgeInsets.all(20),
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        Text(
          'Привет${(profile['display_name'] as String).isEmpty ? '' : ', ${profile['display_name']}'}!',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 8),
        const Text('Сегодня — хороший день для нового сочетания.'),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.secondaryContainer,
            borderRadius: BorderRadius.circular(24),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.auto_awesome, size: 32),
              const SizedBox(height: 16),
              Text(
                'А что, если любимый образ уже у вас?',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              const Text('Находите новые сочетания в знакомых вещах.'),
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: widget.create,
                icon: const Icon(Icons.auto_awesome),
                label: const Text('Создать мой образ'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            Chip(
              avatar: const Icon(Icons.checkroom, size: 18),
              label: Text('${data['summary']['total']} вещей'),
            ),
            Chip(
              avatar: const Icon(Icons.auto_awesome, size: 18),
              label: Text('${outfits.length} образов'),
            ),
            Chip(
              avatar: const Icon(Icons.favorite, size: 18),
              label: Text('${(data['saved'] as List).length} любимых'),
            ),
          ],
        ),
        const SizedBox(height: 22),
        Row(
          children: [
            Expanded(
              child: Text(
                'Последние образы',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
            TextButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => Scaffold(
                    appBar: AppBar(title: const Text('История образов')),
                    body: OutfitsPage(api: widget.api),
                  ),
                ),
              ),
              child: const Text('Все'),
            ),
          ],
        ),
        if (outfits.isEmpty)
          const MessageBox(
            'Создайте первый образ из своих вещей. Демонстрационных гардеробов здесь нет.',
          ),
        ...outfits
            .take(3)
            .map(
              (outfit) => OutfitTile(
                api: widget.api,
                outfit: outfit,
                open: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => OutfitDetailPage(
                      api: widget.api,
                      id: outfit['id'] as int,
                    ),
                  ),
                ),
              ),
            ),
      ],
    );
  });
}
