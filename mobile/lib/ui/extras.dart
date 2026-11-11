import 'package:flutter/material.dart';
import '../services/api.dart';
import 'shared.dart';
import 'outfits.dart';

class StylistPage extends StatefulWidget {
  const StylistPage({required this.api, super.key});
  final LooksyApi api;
  @override
  State<StylistPage> createState() => _StylistPageState();
}

class _StylistPageState extends State<StylistPage> {
  final message = TextEditingController();
  bool ai = true, busy = false;
  String? error;
  List<Json> replies = [];
  @override
  void dispose() {
    message.dispose();
    super.dispose();
  }

  Future<void> send() async {
    if (message.text.trim().isEmpty) return;
    setState(() => busy = true);
    final question = message.text;
    try {
      final reply =
          await widget.api.request(
                '/api/stylist/',
                method: 'POST',
                body: {'message': question, 'use_ai': ai},
              )
              as Json;
      if (mounted && context.mounted) {
        setState(() {
          replies.add({'question': question, 'reply': reply});
          message.clear();
          error = null;
        });
      }
    } catch (e) {
      if (mounted && context.mounted) setState(() => error = e.toString());
    } finally {
      if (mounted && context.mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Looksy-стилист')),
    body: Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              const MessageBox(
                'Спросите про свои вещи. Если AI недоступен, алгоритм предложит базовый комплект. Переписка не сохраняется после закрытия страницы.',
              ),
              ...replies.map((row) {
                final reply = row['reply'] as Json;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Card(
                      color: Theme.of(context).colorScheme.secondaryContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Text(row['question'] as String),
                      ),
                    ),
                    Text(
                      reply['source'] == 'ollama'
                          ? 'Looksy AI'
                          : 'Looksy · алгоритм правил',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Text(reply['message'] as String),
                    ...(reply['items'] as List).cast<Json>().map(
                      (item) => Card(
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            children: [
                              PrivatePhoto(
                                api: widget.api,
                                photo: item['photo'] as Json?,
                                name: item['name'] as String,
                                height: 120,
                              ),
                              Text(item['name'] as String),
                            ],
                          ),
                        ),
                      ),
                    ),
                    if ((reply['missing_slots'] as List).isNotEmpty)
                      MessageBox(
                        'Можно дополнить гардероб: ${(reply['missing_slots'] as List).map((slot) => slots[slot] ?? slot).join(', ')}. Вещи не добавлены автоматически.',
                      ),
                    ...(reply['warnings'] as List? ?? []).map(
                      (w) => MessageBox(w as String),
                    ),
                    const Divider(height: 30),
                  ],
                );
              }),
              if (error != null) MessageBox(error!, icon: Icons.error_outline),
            ],
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: ai,
                  onChanged: (v) => setState(() => ai = v),
                  title: const Text('Использовать AI, если доступен'),
                ),
                TextField(
                  controller: message,
                  minLines: 1,
                  maxLines: 3,
                  maxLength: 1000,
                  decoration: InputDecoration(
                    labelText: 'Сообщение стилисту',
                    suffixIcon: IconButton(
                      tooltip: 'Отправить',
                      onPressed: busy ? null : send,
                      icon: busy
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(),
                            )
                          : const Icon(Icons.send),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  );
}

class CalendarPage extends StatefulWidget {
  const CalendarPage({required this.api, super.key});
  final LooksyApi api;
  @override
  State<CalendarPage> createState() => _CalendarPageState();
}

class _CalendarPageState extends RemoteState<CalendarPage> {
  DateTime date = DateTime.now();
  int? selected;
  final note = TextEditingController();
  bool busy = false;
  String get stamp =>
      '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  @override
  void dispose() {
    note.dispose();
    super.dispose();
  }

  @override
  Future<Json> load() async {
    final data = await Future.wait([
      widget.api.collection('/api/calendar/'),
      widget.api.collection('/api/outfits/'),
    ]);
    return {'entries': data[0], 'outfits': data[1]};
  }

  Future<void> save(Json? entry) async {
    if (selected == null) {
      showError(context, 'Выберите образ.');
      return;
    }
    setState(() => busy = true);
    try {
      await widget.api.request(
        entry == null ? '/api/calendar/' : '/api/calendar/${entry['id']}/',
        method: entry == null ? 'POST' : 'PATCH',
        body: {'date': stamp, 'outfit': selected, 'note': note.text},
      );
      if (mounted && context.mounted) reload();
    } catch (e) {
      if (mounted && context.mounted) showError(context, e);
    } finally {
      if (mounted && context.mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Календарь образов')),
    body: remote((data) {
      final entries = (data['entries'] as List).cast<Json>();
      final outfits = (data['outfits'] as List).cast<Json>();
      final entry = entries.where((e) => e['date'] == stamp).firstOrNull;
      return ListView(
        padding: const EdgeInsets.all(20),
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          Text(
            'Планы на $stamp',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 12),
          FilledButton.tonalIcon(
            onPressed: () async {
              final value = await showDatePicker(
                context: context,
                initialDate: date,
                firstDate: DateTime(2020),
                lastDate: DateTime(2100),
              );
              if (mounted && value != null) {
                setState(() {
                  date = value;
                  selected = null;
                  note.clear();
                });
              }
            },
            icon: const Icon(Icons.calendar_month),
            label: const Text('Выбрать дату'),
          ),
          if (outfits.isEmpty) const MessageBox('Сначала создайте образ.'),
          if (outfits.isNotEmpty) ...[
            const SizedBox(height: 20),
            DropdownButtonFormField<int>(
              key: ValueKey(stamp),
              initialValue: selected,
              decoration: const InputDecoration(
                labelText: 'Образ для этой даты',
              ),
              items: outfits
                  .map(
                    (o) => DropdownMenuItem(
                      value: o['id'] as int,
                      child: Text(
                        o['name'] as String,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (v) => selected = v,
            ),
            const SizedBox(height: 14),
            TextField(
              controller: note,
              maxLength: 300,
              decoration: const InputDecoration(labelText: 'Заметка'),
            ),
            FilledButton(
              onPressed: busy ? null : () => save(entry),
              child: Text(entry == null ? 'Запланировать' : 'Обновить план'),
            ),
          ],
          if (entry != null) ...[
            const SizedBox(height: 16),
            OutfitTile(
              api: widget.api,
              outfit: entry['outfit_details'] as Json,
              open: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => OutfitDetailPage(
                    api: widget.api,
                    id: entry['outfit'] as int,
                  ),
                ),
              ),
            ),
            Text(entry['note'] as String),
            TextButton(
              onPressed: busy
                  ? null
                  : () async {
                      try {
                        await widget.api.request(
                          '/api/calendar/${entry['id']}/',
                          method: 'DELETE',
                        );
                        if (mounted && context.mounted) reload();
                      } catch (e) {
                        if (mounted && context.mounted) showError(context, e);
                      }
                    },
              child: const Text('Удалить план'),
            ),
          ],
          const SizedBox(height: 24),
          Text(
            'Все запланированные образы',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          ...entries.map(
            (e) => ListTile(
              title: Text(e['date'] as String),
              subtitle: Text(e['outfit_details']['name'] as String),
              onTap: () => setState(() {
                date = DateTime.parse(e['date'] as String);
                selected = e['outfit'] as int;
                note.text = e['note'] as String;
              }),
            ),
          ),
        ],
      );
    }),
  );
}
