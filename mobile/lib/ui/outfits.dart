import 'package:flutter/material.dart';
import '../services/api.dart';
import 'shared.dart';

class OutfitsPage extends StatefulWidget {
  const OutfitsPage({required this.api, this.savedOnly = false, super.key});
  final LooksyApi api;
  final bool savedOnly;
  @override
  State<OutfitsPage> createState() => _OutfitsPageState();
}

class _OutfitsPageState extends RemoteState<OutfitsPage> {
  @override
  Future<Json> load() async {
    final results = await Future.wait([
      widget.api.collection('/api/outfits/'),
      widget.api.collection('/api/saved-outfits/'),
    ]);
    final saved = results[1].map((e) => e['outfit']).toSet();
    return {
      'items': results[0]
          .where((e) => !widget.savedOnly || saved.contains(e['id']))
          .toList(),
    };
  }

  @override
  Widget build(BuildContext context) => remote((data) {
    final items = (data['items'] as List).cast<Json>();
    return ListView(
      padding: const EdgeInsets.all(20),
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        Text(
          widget.savedOnly ? 'Любимые образы' : 'История образов',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 10),
        if (items.isEmpty)
          const MessageBox(
            'Пока здесь пусто. Создайте образ и добавьте понравившийся в избранное.',
          ),
        ...items.map(
          (o) => OutfitTile(
            api: widget.api,
            outfit: o,
            open: () async {
              await Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) =>
                      OutfitDetailPage(api: widget.api, id: o['id'] as int),
                ),
              );
              if (mounted && context.mounted) reload();
            },
          ),
        ),
      ],
    );
  });
}

class CreatePage extends StatefulWidget {
  const CreatePage({required this.api, super.key});
  final LooksyApi api;
  @override
  State<CreatePage> createState() => _CreatePageState();
}

class _CreatePageState extends State<CreatePage> {
  final style = TextEditingController();
  final temperature = TextEditingController();
  final notes = TextEditingController();
  String occasion = 'everyday', season = 'all';
  double comfort = 50;
  bool weather = false, busy = false;
  String? error;
  List<Json>? items;
  Set<int> required = {}, excluded = {};
  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void dispose() {
    style.dispose();
    temperature.dispose();
    notes.dispose();
    super.dispose();
  }

  Future<void> load() async {
    try {
      final data = await widget.api.collection('/api/clothing/');
      if (mounted && context.mounted) setState(() => items = data);
    } catch (e) {
      if (mounted && context.mounted) setState(() => error = e.toString());
    }
  }

  Future<void> generate() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final payload = <String, dynamic>{
        'count': 3,
        'occasion': occasion,
        'style': style.text,
        'season': season,
        'comfort_priority': comfort.round(),
        'required_items': required.toList(),
        'excluded_items': excluded.toList(),
        'use_weather': weather,
        'weather_failure': 'continue',
        'notes': notes.text,
      };
      if (!weather && temperature.text.trim().isNotEmpty) {
        final n = double.tryParse(temperature.text.replaceAll(',', '.'));
        if (n == null || !n.isFinite || n < -60 || n > 60) {
          throw const ApiException('Укажите температуру от -60 до 60.');
        }
        payload['temperature_c'] = n;
      }
      final data =
          await widget.api.request(
                '/api/outfits/generate/',
                method: 'POST',
                body: payload,
              )
              as Json;
      if (mounted && context.mounted) {
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => Scaffold(
              appBar: AppBar(title: const Text('Ваши сочетания')),
              body: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  ...(data['messages'] as List).map(
                    (m) => MessageBox(m as String),
                  ),
                  ...(data['results'] as List).cast<Json>().map(
                    (o) => OutfitTile(
                      api: widget.api,
                      outfit: o,
                      open: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => OutfitDetailPage(
                            api: widget.api,
                            id: o['id'] as int,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted && context.mounted) setState(() => error = e.toString());
    } finally {
      if (mounted && context.mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => items == null
      ? error != null
            ? Failed(error!, load)
            : const Busy()
      : ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Что наденем сегодня?',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 10),
            const Text('Подберём до трёх образов из вашего гардероба.'),
            if (error != null) MessageBox(error!, icon: Icons.error_outline),
            const SizedBox(height: 20),
            DropdownButtonFormField<String>(
              initialValue: occasion,
              decoration: const InputDecoration(labelText: 'Куда собираетесь?'),
              items: const [
                DropdownMenuItem(
                  value: 'everyday',
                  child: Text('На каждый день'),
                ),
                DropdownMenuItem(
                  value: 'university',
                  child: Text('В университет'),
                ),
                DropdownMenuItem(value: 'work', child: Text('На работу')),
                DropdownMenuItem(value: 'sport', child: Text('На тренировку')),
                DropdownMenuItem(value: 'party', child: Text('На вечеринку')),
                DropdownMenuItem(
                  value: 'formal',
                  child: Text('Официальное мероприятие'),
                ),
              ],
              onChanged: (v) => occasion = v!,
            ),
            const SizedBox(height: 14),
            TextField(
              controller: style,
              maxLength: 80,
              decoration: const InputDecoration(
                labelText: 'Стиль',
                hintText: 'casual / minimalism',
              ),
            ),
            DropdownButtonFormField<String>(
              initialValue: season,
              decoration: const InputDecoration(labelText: 'Сезон'),
              items: seasons.entries
                  .map(
                    (e) => DropdownMenuItem(value: e.key, child: Text(e.value)),
                  )
                  .toList(),
              onChanged: (v) => season = v!,
            ),
            const SizedBox(height: 15),
            Text('Приоритет комфорта: ${comfort.round()}%'),
            Slider(
              value: comfort,
              min: 0,
              max: 100,
              divisions: 100,
              onChanged: (v) => setState(() => comfort = v),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Учитывать Open-Meteo'),
              subtitle: const Text(
                'Город и координаты выбираются в профиле. При сбое подбор продолжится без погоды.',
              ),
              value: weather,
              onChanged: (v) => setState(() => weather = v),
            ),
            if (!weather)
              TextField(
                controller: temperature,
                keyboardType: const TextInputType.numberWithOptions(
                  signed: true,
                  decimal: true,
                ),
                decoration: const InputDecoration(
                  labelText: 'Температура вручную, °C (необязательно)',
                ),
              ),
            const SizedBox(height: 22),
            Text(
              'Обязательные и исключённые вещи',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (items!.isEmpty)
              const MessageBox('Сначала добавьте свои вещи в гардероб.'),
            ...items!.map((item) {
              final id = item['id'] as int;
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(item['name'] as String),
                      Wrap(
                        spacing: 12,
                        children: [
                          FilterChip(
                            label: const Text('Обязательно'),
                            selected: required.contains(id),
                            onSelected:
                                item['is_available'] != true ||
                                    excluded.contains(id)
                                ? null
                                : (v) => setState(() {
                                    if (v) {
                                      required.add(id);
                                    } else {
                                      required.remove(id);
                                    }
                                  }),
                          ),
                          FilterChip(
                            label: const Text('Исключить'),
                            selected: excluded.contains(id),
                            onSelected: required.contains(id)
                                ? null
                                : (v) => setState(() {
                                    if (v) {
                                      excluded.add(id);
                                    } else {
                                      excluded.remove(id);
                                    }
                                  }),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }),
            const SizedBox(height: 14),
            TextField(
              controller: notes,
              maxLength: 1000,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Дополнительные пожелания',
              ),
            ),
            const MessageBox(
              'Свободный текст сохраняется, но не заменяет ограничения. Генератор работает по проверяемым правилам; для обсуждения есть AI-стилист.',
            ),
            FilledButton.icon(
              onPressed: busy || items!.isEmpty ? null : generate,
              icon: const Icon(Icons.auto_awesome),
              label: Text(busy ? 'Ищем сочетания…' : 'Создать мой образ'),
            ),
            const SizedBox(height: 24),
          ],
        );
}

class OutfitDetailPage extends StatefulWidget {
  const OutfitDetailPage({required this.api, required this.id, super.key});
  final LooksyApi api;
  final int id;
  @override
  State<OutfitDetailPage> createState() => _OutfitDetailState();
}

class _OutfitDetailState extends RemoteState<OutfitDetailPage> {
  bool busy = false;
  @override
  Future<Json> load() async {
    final data = await Future.wait([
      widget.api.request('/api/outfits/${widget.id}/'),
      widget.api.collection('/api/saved-outfits/'),
      widget.api.collection('/api/feedback/'),
    ]);
    return {'outfit': data[0], 'saved': data[1], 'feedback': data[2]};
  }

  Future<void> action(Future<void> Function() operation) async {
    setState(() => busy = true);
    try {
      await operation();
      if (mounted && context.mounted) reload();
    } catch (e) {
      if (mounted && context.mounted) showError(context, e);
    } finally {
      if (mounted && context.mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Ваш образ')),
    body: remote((data) {
      final outfit = data['outfit'] as Json;
      final items = (outfit['item_details'] as List).cast<Json>();
      final gen = outfit['generation'] as Json;
      final saved = (data['saved'] as List)
          .cast<Json>()
          .where((e) => e['outfit'] == widget.id)
          .firstOrNull;
      final feedback = (data['feedback'] as List)
          .cast<Json>()
          .where((e) => e['outfit'] == widget.id)
          .firstOrNull;
      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            outfit['name'] as String,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 15),
          ...items.map(
            (item) => Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    PrivatePhoto(
                      api: widget.api,
                      photo: item['photo'] as Json?,
                      height: 180,
                      name: item['name'] as String,
                    ),
                    const SizedBox(height: 8),
                    Text(item['name'] as String),
                    if (item['is_available'] != true)
                      const Text('Временно недоступна'),
                  ],
                ),
              ),
            ),
          ),
          if (gen['score'] != null)
            MessageBox(
              outfit['generation_is_stale'] == true
                  ? 'Вещи изменились — прежняя оценка устарела.'
                  : 'Совместимость ${gen['score']} / 100. Субъективный рейтинг алгоритма, а не объективная оценка стиля.',
            ),
          ...(gen['explanation'] as List? ?? []).map(
            (s) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Text(s as String),
            ),
          ),
          ...(gen['warnings'] as List? ?? []).map(
            (s) => MessageBox(s as String),
          ),
          FilledButton.icon(
            onPressed: busy
                ? null
                : () => action(() async {
                    await widget.api.request(
                      saved == null
                          ? '/api/saved-outfits/'
                          : '/api/saved-outfits/${saved['id']}/',
                      method: saved == null ? 'POST' : 'DELETE',
                      body: saved == null ? {'outfit': widget.id} : null,
                    );
                  }),
            icon: Icon(saved == null ? Icons.favorite_border : Icons.favorite),
            label: Text(saved == null ? 'В избранное' : 'Убрать из избранного'),
          ),
          const SizedBox(height: 16),
          const Text('Как вам этот образ?'),
          Wrap(
            children: [1, 2, 3, 4, 5]
                .map(
                  (rating) => IconButton(
                    tooltip: 'Оценить на $rating',
                    onPressed: busy
                        ? null
                        : () => action(() async {
                            await widget.api.request(
                              feedback == null
                                  ? '/api/feedback/'
                                  : '/api/feedback/${feedback['id']}/',
                              method: feedback == null ? 'POST' : 'PATCH',
                              body: {'outfit': widget.id, 'rating': rating},
                            );
                          }),
                    icon: Icon(
                      rating <= ((feedback?['rating'] as int?) ?? 0)
                          ? Icons.star
                          : Icons.star_border,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                )
                .toList(),
          ),
          TextButton.icon(
            onPressed: busy
                ? null
                : () async {
                    if (!await confirm(
                      context,
                      'Удалить образ?',
                      'Он будет удалён из истории, избранного и календаря.',
                    )) {
                      return;
                    }
                    try {
                      await widget.api.request(
                        '/api/outfits/${widget.id}/',
                        method: 'DELETE',
                      );
                      if (mounted && context.mounted) Navigator.pop(context);
                    } catch (e) {
                      if (mounted && context.mounted) showError(context, e);
                    }
                  },
            icon: const Icon(Icons.delete_outline),
            label: const Text('Удалить образ'),
          ),
          const SizedBox(height: 24),
        ],
      );
    }),
  );
}
