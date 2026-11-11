import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api.dart';
import 'shared.dart';

class WardrobePage extends StatefulWidget {
  const WardrobePage({required this.api, super.key});
  final LooksyApi api;
  @override
  State<WardrobePage> createState() => _WardrobePageState();
}

class _WardrobePageState extends RemoteState<WardrobePage> {
  final search = TextEditingController();
  int? category;
  String available = '';
  @override
  void dispose() {
    search.dispose();
    super.dispose();
  }

  @override
  Future<Json> load() async {
    final query = Uri(
      queryParameters: {
        if (search.text.isNotEmpty) 'search': search.text,
        if (category != null) 'category': '$category',
        if (available.isNotEmpty) 'is_available': available,
      },
    ).query;
    final data = await Future.wait([
      widget.api.collection('/api/clothing/?$query'),
      widget.api.collection('/api/categories/'),
    ]);
    return {'items': data[0], 'categories': data[1]};
  }

  Future<void> edit([Json? item]) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ItemEditor(api: widget.api, item: item),
      ),
    );
    if (mounted && context.mounted) reload();
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Мой гардероб',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ),
                FilledButton.icon(
                  onPressed: () => edit(),
                  icon: const Icon(Icons.add),
                  label: const Text('Добавить'),
                ),
              ],
            ),
            const SizedBox(height: 14),
            TextField(
              controller: search,
              onSubmitted: (_) => reload(),
              decoration: InputDecoration(
                hintText: 'Поиск вещей',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  tooltip: 'Найти',
                  onPressed: reload,
                  icon: const Icon(Icons.arrow_forward),
                ),
              ),
            ),
            const SizedBox(height: 10),
          ],
        ),
      ),
      Expanded(
        child: remote((data) {
          final items = (data['items'] as List).cast<Json>();
          final categories = (data['categories'] as List).cast<Json>();
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            physics: const AlwaysScrollableScrollPhysics(),
            children: [
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<int?>(
                      initialValue: category,
                      decoration: const InputDecoration(labelText: 'Категория'),
                      items: [
                        const DropdownMenuItem<int?>(
                          value: null,
                          child: Text('Все'),
                        ),
                        ...categories.map(
                          (c) => DropdownMenuItem<int?>(
                            value: c['id'] as int,
                            child: Text(
                              c['name'] as String,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ),
                      ],
                      onChanged: (v) {
                        category = v;
                        reload();
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: available,
                      decoration: const InputDecoration(
                        labelText: 'Доступность',
                      ),
                      items: const [
                        DropdownMenuItem(value: '', child: Text('Все вещи')),
                        DropdownMenuItem(
                          value: 'true',
                          child: Text('Доступные'),
                        ),
                        DropdownMenuItem(
                          value: 'false',
                          child: Text('Недоступные'),
                        ),
                      ],
                      onChanged: (v) {
                        available = v ?? '';
                        reload();
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text('${items.length} вещей'),
              if (items.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 35),
                  child: MessageBox(
                    'Пока нет вещей или фильтры ничего не нашли. Добавьте свою первую вещь.',
                  ),
                ),
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: items.length,
                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 240,
                  mainAxisExtent: 260,
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                ),
                itemBuilder: (context, index) {
                  final item = items[index];
                  return Card(
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: () => edit(item),
                      child: Padding(
                        padding: const EdgeInsets.all(10),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            PrivatePhoto(
                              api: widget.api,
                              photo: item['photo'] as Json?,
                              height: 155,
                              name: item['name'] as String,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              item['name'] as String,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const Spacer(),
                            Text(
                              item['is_available'] == true
                                  ? 'В гардеробе'
                                  : 'Временно недоступна',
                              style: TextStyle(
                                fontSize: 11,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              ),
              const SizedBox(height: 25),
            ],
          );
        }),
      ),
    ],
  );
}

class ItemEditor extends StatefulWidget {
  const ItemEditor({required this.api, this.item, super.key});
  final LooksyApi api;
  final Json? item;
  @override
  State<ItemEditor> createState() => _ItemEditorState();
}

class _ItemEditorState extends State<ItemEditor> {
  final form = GlobalKey<FormState>();
  final name = TextEditingController();
  final description = TextEditingController();
  final styles = TextEditingController();
  final material = TextEditingController();
  final brand = TextEditingController();
  List<Json>? categories, colors;
  Set<int> colorIds = {};
  int? id, category, comfort, warmth;
  String season = 'all', fit = 'unknown';
  bool available = true, busy = false;
  String? error;
  Uint8List? image;
  String filename = 'photo.jpg';
  Json? photo;
  @override
  void initState() {
    super.initState();
    final item = widget.item;
    id = item?['id'] as int?;
    category = item?['category'] as int?;
    name.text = item?['name'] as String? ?? '';
    description.text = item?['description'] as String? ?? '';
    styles.text = (item?['styles'] as List? ?? []).join(', ');
    material.text = item?['material'] as String? ?? '';
    brand.text = item?['brand'] as String? ?? '';
    season = item?['season'] as String? ?? 'all';
    fit = item?['fit'] as String? ?? 'unknown';
    comfort = item?['comfort'] as int?;
    warmth = item?['warmth'] as int?;
    available = item?['is_available'] as bool? ?? true;
    colorIds = (item?['colors'] as List? ?? []).cast<int>().toSet();
    photo = item?['photo'] as Json?;
    load();
  }

  Future<void> load() async {
    try {
      final values = await Future.wait([
        widget.api.collection('/api/categories/'),
        widget.api.collection('/api/colors/'),
      ]);
      if (mounted && context.mounted) {
        setState(() {
          categories = values[0];
          colors = values[1];
        });
      }
    } catch (e) {
      if (mounted && context.mounted) setState(() => error = e.toString());
    }
  }

  @override
  void dispose() {
    for (final c in [name, description, styles, material, brand]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> select(XFile file) async {
    if (await file.length() > 5 * 1024 * 1024) {
      if (mounted && context.mounted) {
        setState(() => error = 'Фото должно быть не больше 5 МБ.');
      }
      return;
    }
    final bytes = await file.readAsBytes();
    if (mounted && context.mounted) {
      setState(() {
        image = bytes;
        filename = file.name;
        error = null;
      });
    }
  }

  Future<void> pick(ImageSource source) async {
    try {
      final file = await ImagePicker().pickImage(source: source);
      if (file != null) await select(file);
    } catch (e) {
      if (mounted && context.mounted) {
        showError(
          context,
          'Не удалось открыть камеру или галерею. Проверьте разрешения приложения.',
        );
      }
    }
  }

  Future<void> save() async {
    if (!form.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final payload = {
        'name': name.text.trim(),
        'category': category,
        'colors': colorIds.toList(),
        'description': description.text,
        'styles': styles.text
            .split(',')
            .map((s) => s.trim())
            .where((s) => s.isNotEmpty)
            .toList(),
        'material': material.text,
        'brand': brand.text,
        'season': season,
        'fit': fit,
        'comfort': comfort,
        'warmth': warmth,
        'is_available': available,
      };
      final item =
          await widget.api.request(
                id == null ? '/api/clothing/' : '/api/clothing/$id/',
                method: id == null ? 'POST' : 'PATCH',
                body: payload,
              )
              as Json;
      id = item['id'] as int;
      if (image != null) {
        await widget.api.upload('/api/clothing/$id/photo/', image!, filename);
      }
      if (mounted && context.mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted && context.mounted) {
        setState(
          () => error =
              '${id != null ? 'Карточка сохранена; повторите загрузку или исправьте данные. ' : ''}$e',
        );
      }
    } finally {
      if (mounted && context.mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(widget.item == null ? 'Новая вещь' : 'Детали вещи'),
    ),
    body: categories == null
        ? error != null
              ? Failed(error!, load)
              : const Busy()
        : Form(
            key: form,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                if (error != null)
                  MessageBox(error!, icon: Icons.error_outline),
                if (image != null)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Image.memory(
                      image!,
                      height: 210,
                      fit: BoxFit.contain,
                    ),
                  )
                else
                  PrivatePhoto(api: widget.api, photo: photo, height: 210),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 10,
                  children: [
                    FilledButton.tonalIcon(
                      onPressed: busy ? null : () => pick(ImageSource.camera),
                      icon: const Icon(Icons.camera_alt_outlined),
                      label: const Text('Камера'),
                    ),
                    FilledButton.tonalIcon(
                      onPressed: busy ? null : () => pick(ImageSource.gallery),
                      icon: const Icon(Icons.photo_library_outlined),
                      label: const Text('Галерея'),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                const Text(
                  'JPEG, PNG, WebP · до 5 МБ · до 16 Мп',
                  style: TextStyle(fontSize: 12),
                ),
                if (photo != null) ...[
                  MessageBox(
                    (photo!['analysis']?['recognition']?['message'] ??
                            'Характеристики можно исправить вручную.')
                        as String,
                  ),
                  TextButton(
                    onPressed: busy
                        ? null
                        : () async {
                            try {
                              await widget.api.request(
                                '/api/clothing/$id/photo/',
                                method: 'DELETE',
                              );
                              if (mounted && context.mounted) {
                                setState(() => photo = null);
                              }
                            } catch (e) {
                              if (mounted && context.mounted) {
                                showError(context, e);
                              }
                            }
                          },
                    child: const Text('Удалить фото'),
                  ),
                ],
                const SizedBox(height: 20),
                TextFormField(
                  controller: name,
                  decoration: const InputDecoration(labelText: 'Название'),
                  maxLength: 150,
                  validator: (v) =>
                      (v ?? '').trim().isEmpty ? 'Назовите вещь' : null,
                ),
                const SizedBox(height: 14),
                DropdownButtonFormField<int>(
                  initialValue: category,
                  items: categories!
                      .map(
                        (c) => DropdownMenuItem(
                          value: c['id'] as int,
                          child: Text(c['name'] as String),
                        ),
                      )
                      .toList(),
                  onChanged: (v) => category = v,
                  decoration: const InputDecoration(labelText: 'Категория'),
                  validator: (v) => v == null ? 'Выберите категорию' : null,
                ),
                const SizedBox(height: 14),
                DropdownButtonFormField<String>(
                  initialValue: season,
                  items: seasons.entries
                      .map(
                        (e) => DropdownMenuItem(
                          value: e.key,
                          child: Text(e.value),
                        ),
                      )
                      .toList(),
                  onChanged: (v) => season = v!,
                  decoration: const InputDecoration(labelText: 'Сезон'),
                ),
                const SizedBox(height: 14),
                DropdownButtonFormField<String>(
                  initialValue: fit,
                  items: fits.entries
                      .map(
                        (e) => DropdownMenuItem(
                          value: e.key,
                          child: Text(e.value),
                        ),
                      )
                      .toList(),
                  onChanged: (v) => fit = v!,
                  decoration: const InputDecoration(labelText: 'Крой'),
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: styles,
                  decoration: const InputDecoration(
                    labelText: 'Стили через запятую',
                    hintText: 'casual, minimalism',
                  ),
                ),
                const SizedBox(height: 14),
                Text('Цвета', style: Theme.of(context).textTheme.titleMedium),
                Wrap(
                  spacing: 8,
                  children: colors!
                      .map(
                        (c) => FilterChip(
                          label: Text(c['name'] as String),
                          selected: colorIds.contains(c['id']),
                          onSelected: (selected) => setState(() {
                            if (selected) {
                              colorIds.add(c['id'] as int);
                            } else {
                              colorIds.remove(c['id']);
                            }
                          }),
                        ),
                      )
                      .toList(),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<int?>(
                        initialValue: comfort,
                        decoration: const InputDecoration(labelText: 'Комфорт'),
                        items: [
                          const DropdownMenuItem<int?>(
                            value: null,
                            child: Text('Не оценён'),
                          ),
                          ...[1, 2, 3, 4, 5].map(
                            (n) => DropdownMenuItem<int?>(
                              value: n,
                              child: Text('$n / 5'),
                            ),
                          ),
                        ],
                        onChanged: (v) => comfort = v,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonFormField<int?>(
                        initialValue: warmth,
                        decoration: const InputDecoration(labelText: 'Теплота'),
                        items: [
                          const DropdownMenuItem<int?>(
                            value: null,
                            child: Text('Не оценена'),
                          ),
                          ...[1, 2, 3, 4, 5].map(
                            (n) => DropdownMenuItem<int?>(
                              value: n,
                              child: Text('$n / 5'),
                            ),
                          ),
                        ],
                        onChanged: (v) => warmth = v,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: brand,
                  maxLength: 100,
                  decoration: const InputDecoration(
                    labelText: 'Бренд (необязательно)',
                  ),
                ),
                TextFormField(
                  controller: material,
                  maxLength: 100,
                  decoration: const InputDecoration(
                    labelText: 'Материал (если известен)',
                  ),
                ),
                TextFormField(
                  controller: description,
                  maxLength: 2000,
                  maxLines: 3,
                  decoration: const InputDecoration(labelText: 'Заметки'),
                ),
                SwitchListTile(
                  value: available,
                  onChanged: (v) => setState(() => available = v),
                  title: const Text('Доступна для подбора'),
                  subtitle: const Text('Отключите, если вещь в стирке'),
                ),
                FilledButton(
                  onPressed: busy ? null : save,
                  child: Text(busy ? 'Сохраняем…' : 'Сохранить вещь'),
                ),
                if (id != null) ...[
                  const SizedBox(height: 15),
                  TextButton.icon(
                    onPressed: busy
                        ? null
                        : () async {
                            if (!await confirm(
                              context,
                              'Удалить вещь?',
                              'Карточка и фотографии будут удалены.',
                            )) {
                              return;
                            }
                            try {
                              await widget.api.request(
                                '/api/clothing/$id/',
                                method: 'DELETE',
                              );
                              if (mounted && context.mounted) {
                                Navigator.pop(context, true);
                              }
                            } catch (e) {
                              if (mounted && context.mounted) {
                                showError(context, e);
                              }
                            }
                          },
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('Удалить вещь'),
                  ),
                ],
                const SizedBox(height: 30),
              ],
            ),
          ),
  );
}
