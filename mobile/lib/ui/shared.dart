import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../services/api.dart';

typedef Json = Map<String, dynamic>;
const slots = {
  'top': 'Верх',
  'bottom': 'Брюки / юбка',
  'dress': 'Платье',
  'shoes': 'Обувь',
  'outerwear': 'Верхняя одежда',
  'accessory': 'Аксессуар',
  'other': 'Другое',
};
const seasons = {
  'all': 'Все сезоны',
  'summer': 'Лето',
  'winter': 'Зима',
  'spring': 'Весна',
  'autumn': 'Осень',
};
const fits = {
  'unknown': 'Не указан',
  'regular': 'Обычный',
  'slim': 'Приталенный',
  'relaxed': 'Свободный',
  'oversized': 'Оверсайз',
};

void showError(BuildContext context, Object error) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(error.toString()),
      behavior: SnackBarBehavior.floating,
    ),
  );
}

Future<bool> confirm(BuildContext context, String title, String text) async =>
    await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(text),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Отмена'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Подтвердить'),
          ),
        ],
      ),
    ) ??
    false;

class MessageBox extends StatelessWidget {
  const MessageBox(this.text, {super.key, this.icon = Icons.info_outline});
  final String text;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.symmetric(vertical: 8),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.secondaryContainer,
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20),
        const SizedBox(width: 10),
        Expanded(child: Text(text)),
      ],
    ),
  );
}

class EmptyState extends StatelessWidget {
  const EmptyState(this.title, this.message, {super.key, this.action});
  final String title, message;
  final Widget? action;
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.checkroom_outlined,
            size: 54,
            color: Theme.of(context).colorScheme.primary,
          ),
          const SizedBox(height: 18),
          Text(
            title,
            style: Theme.of(context).textTheme.headlineSmall,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 10),
          Text(message, textAlign: TextAlign.center),
          if (action != null) ...[const SizedBox(height: 20), action!],
        ],
      ),
    ),
  );
}

class Busy extends StatelessWidget {
  const Busy({super.key});
  @override
  Widget build(BuildContext context) =>
      const Center(child: CircularProgressIndicator());
}

class Failed extends StatelessWidget {
  const Failed(this.error, this.retry, {super.key});
  final Object error;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) => EmptyState(
    'Не удалось загрузить',
    error.toString(),
    action: FilledButton.tonal(
      onPressed: retry,
      child: const Text('Повторить'),
    ),
  );
}

class PrivatePhoto extends StatefulWidget {
  const PrivatePhoto({
    required this.api,
    required this.photo,
    this.height = 160,
    this.name = 'Фото вещи',
    super.key,
  });
  final LooksyApi api;
  final Json? photo;
  final double height;
  final String name;
  @override
  State<PrivatePhoto> createState() => _PrivatePhotoState();
}

class _PrivatePhotoState extends State<PrivatePhoto> {
  Future<Uint8List>? future;
  @override
  void initState() {
    super.initState();
    load();
  }

  void load() {
    final url = widget.photo?['url'] as String?;
    future = url == null ? null : widget.api.photo(url);
  }

  @override
  void didUpdateWidget(PrivatePhoto old) {
    super.didUpdateWidget(old);
    if (old.photo?['url'] != widget.photo?['url'] ||
        old.photo?['version'] != widget.photo?['version']) {
      load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final bg = Theme.of(context).colorScheme.surfaceContainerHighest;
    return Container(
      height: widget.height,
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(16),
      ),
      child: future == null
          ? const Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.image_not_supported_outlined),
                Text('Без фото'),
              ],
            )
          : FutureBuilder(
              future: future,
              builder: (context, snapshot) {
                if (snapshot.hasError) {
                  return const Center(
                    child: Text('Фото недоступно', textAlign: TextAlign.center),
                  );
                }
                if (!snapshot.hasData) {
                  return const Center(child: CircularProgressIndicator());
                }
                return Image.memory(
                  snapshot.data!,
                  fit: BoxFit.contain,
                  cacheWidth: 640,
                  semanticLabel: widget.name,
                );
              },
            ),
    );
  }
}

class OutfitTile extends StatelessWidget {
  const OutfitTile({
    required this.api,
    required this.outfit,
    required this.open,
    super.key,
  });
  final LooksyApi api;
  final Json outfit;
  final VoidCallback open;
  @override
  Widget build(BuildContext context) {
    final details = (outfit['item_details'] as List? ?? []).cast<Json>();
    final generation = outfit['generation'] as Json? ?? {};
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: open,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                height: 150,
                child: Row(
                  children: details
                      .take(4)
                      .map(
                        (item) => Expanded(
                          child: Padding(
                            padding: const EdgeInsets.all(3),
                            child: PrivatePhoto(
                              api: api,
                              photo: item['photo'] as Json?,
                              name: item['name'] as String,
                              height: 150,
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: 14),
              Text(
                outfit['name'] as String,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Text(details.map((e) => e['name']).join(' · ')),
              if (generation['score'] != null)
                Text(
                  outfit['generation_is_stale'] == true
                      ? 'Оценка устарела'
                      : 'Совместимость ${generation['score']} / 100',
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
              const SizedBox(height: 6),
              const Row(
                children: [
                  Text('Посмотреть образ'),
                  Spacer(),
                  Icon(Icons.arrow_forward, size: 18),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

abstract class RemoteState<T extends StatefulWidget> extends State<T> {
  late Future<Json> future;
  Future<Json> load();
  @override
  void initState() {
    super.initState();
    future = load();
  }

  void reload() {
    setState(() => future = load());
  }

  Widget remote(Widget Function(Json) builder) => FutureBuilder<Json>(
    future: future,
    builder: (context, snapshot) {
      if (snapshot.hasError) return Failed(snapshot.error!, reload);
      if (!snapshot.hasData) return const Busy();
      return RefreshIndicator(
        onRefresh: () async {
          reload();
          await future;
        },
        child: builder(snapshot.data!),
      );
    },
  );
}
