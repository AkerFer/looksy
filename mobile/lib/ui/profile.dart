import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api.dart';
import 'shared.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({required this.api, required this.toggleTheme, super.key});
  final LooksyApi api;
  final VoidCallback toggleTheme;
  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends RemoteState<ProfilePage> {
  @override
  Future<Json> load() async {
    final data = await Future.wait([
      widget.api.request('/api/profile/'),
      widget.api.request('/api/preferences/'),
      widget.api.collection('/api/colors/'),
      widget.api.collection('/api/categories/'),
    ]);
    return {
      'profile': data[0],
      'preferences': data[1],
      'colors': data[2],
      'categories': data[3],
    };
  }

  @override
  Widget build(BuildContext context) => remote((data) {
    final profile = data['profile'] as Json;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text('Ваш профиль', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 20),
        PrivatePhoto(
          api: widget.api,
          photo: profile['avatar'] as Json?,
          height: 150,
          name: 'Аватар',
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 10,
          children: [
            FilledButton.tonalIcon(
              onPressed: () async {
                final epoch = widget.api.epoch;
                try {
                  final file = await ImagePicker().pickImage(
                    source: ImageSource.gallery,
                  );
                  if (file == null) return;
                  if (await file.length() > 5 * 1024 * 1024) {
                    throw const ApiException(
                      'Файл должен быть не больше 5 МБ.',
                    );
                  }
                  final bytes = await file.readAsBytes();
                  if (!mounted || widget.api.epoch != epoch) return;
                  await widget.api.upload(
                    '/api/profile/avatar/',
                    bytes,
                    file.name,
                  );
                  if (mounted && context.mounted) reload();
                } catch (e) {
                  if (mounted && context.mounted) showError(context, e);
                }
              },
              icon: const Icon(Icons.image_outlined),
              label: const Text('Аватар'),
            ),
            if (profile['avatar'] != null)
              TextButton(
                onPressed: () async {
                  try {
                    await widget.api.request(
                      '/api/profile/avatar/',
                      method: 'DELETE',
                    );
                    if (mounted && context.mounted) reload();
                  } catch (e) {
                    if (mounted && context.mounted) showError(context, e);
                  }
                },
                child: const Text('Удалить фото'),
              ),
          ],
        ),
        const SizedBox(height: 20),
        Text(
          profile['display_name'] as String,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        Text(
          (profile['city'] as String).isEmpty
              ? 'Город ещё не выбран'
              : profile['city'] as String,
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: () async {
            await Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ProfileEditor(api: widget.api, data: data),
              ),
            );
            if (mounted && context.mounted) reload();
          },
          icon: const Icon(Icons.edit_outlined),
          label: const Text('Настроить профиль и стиль'),
        ),
        ListTile(
          leading: const Icon(Icons.dark_mode_outlined),
          title: const Text('Переключить тему'),
          onTap: widget.toggleTheme,
        ),
        ListTile(
          leading: const Icon(Icons.dns_outlined),
          title: const Text('Адрес сервера'),
          subtitle: Text(widget.api.server?.origin ?? ''),
        ),
        const MessageBox(
          'Для смены сервера выйдите из аккаунта и укажите новый адрес на экране входа. Секреты и фотографии не сохраняются в открытом хранилище.',
        ),
        ListTile(
          leading: const Icon(Icons.logout),
          title: const Text('Выйти'),
          onTap: () async {
            try {
              await widget.api.logout();
            } catch (_) {
              /* Local credentials are cleared even if the backend is offline. */
            }
          },
        ),
        ListTile(
          leading: Icon(
            Icons.delete_forever,
            color: Theme.of(context).colorScheme.error,
          ),
          title: const Text('Удалить аккаунт'),
          onTap: () async {
            final controller = TextEditingController();
            final password = await showDialog<String>(
              context: context,
              builder: (context) => AlertDialog(
                title: const Text('Удалить аккаунт?'),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Будут удалены гардероб, фотографии, образы и планы. Для подтверждения введите текущий пароль.',
                    ),
                    const SizedBox(height: 15),
                    TextField(
                      controller: controller,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Текущий пароль',
                      ),
                    ),
                  ],
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Отмена'),
                  ),
                  FilledButton(
                    onPressed: () => Navigator.pop(context, controller.text),
                    child: const Text('Удалить'),
                  ),
                ],
              ),
            );
            controller.dispose();
            if (!mounted || password == null || password.isEmpty) return;
            try {
              await widget.api.deleteAccount(password);
            } catch (e) {
              if (mounted && context.mounted) showError(context, e);
            }
          },
        ),
        const SizedBox(height: 20),
      ],
    );
  });
}

class ProfileEditor extends StatefulWidget {
  const ProfileEditor({required this.api, required this.data, super.key});
  final LooksyApi api;
  final Json data;
  @override
  State<ProfileEditor> createState() => _ProfileEditorState();
}

class _ProfileEditorState extends State<ProfileEditor> {
  final name = TextEditingController(),
      city = TextEditingController(),
      lat = TextEditingController(),
      lon = TextEditingController(),
      styles = TextEditingController();
  int cold = 3, heat = 3;
  double comfort = 50;
  String fit = 'unknown';
  Set<int> preferred = {}, disliked = {}, excluded = {};
  List<Json> locations = [];
  bool busy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    final p = widget.data['profile'] as Json;
    final pref = widget.data['preferences'] as Json;
    name.text = p['display_name'] as String;
    city.text = p['city'] as String;
    lat.text = p['latitude']?.toString() ?? '';
    lon.text = p['longitude']?.toString() ?? '';
    cold = p['cold_sensitivity'] as int;
    heat = p['heat_sensitivity'] as int;
    styles.text = (pref['styles'] as List).join(', ');
    fit = pref['preferred_fit'] as String;
    comfort = (pref['comfort_priority'] as num).toDouble();
    preferred = (pref['preferred_colors'] as List).cast<int>().toSet();
    disliked = (pref['disliked_colors'] as List).cast<int>().toSet();
    excluded = (pref['excluded_categories'] as List).cast<int>().toSet();
  }

  @override
  void dispose() {
    for (final c in [name, city, lat, lon, styles]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> save() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await widget.api.request(
        '/api/profile/',
        method: 'PATCH',
        body: {
          'display_name': name.text,
          'city': city.text,
          'latitude': lat.text.trim().isEmpty ? null : lat.text,
          'longitude': lon.text.trim().isEmpty ? null : lon.text,
          'cold_sensitivity': cold,
          'heat_sensitivity': heat,
        },
      );
      await widget.api.request(
        '/api/preferences/',
        method: 'PATCH',
        body: {
          'styles': styles.text
              .split(',')
              .map((s) => s.trim())
              .where((s) => s.isNotEmpty)
              .toList(),
          'preferred_colors': preferred.toList(),
          'disliked_colors': disliked.toList(),
          'excluded_categories': excluded.toList(),
          'preferred_fit': fit,
          'comfort_priority': comfort.round(),
        },
      );
      if (mounted && context.mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted && context.mounted) {
        setState(
          () =>
              error = 'Часть настроек могла сохраниться. Проверьте данные. $e',
        );
      }
    } finally {
      if (mounted && context.mounted) setState(() => busy = false);
    }
  }

  Widget colors(String title, Set<int> selected) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(title, style: Theme.of(context).textTheme.titleMedium),
      Wrap(
        spacing: 8,
        children: (widget.data['colors'] as List)
            .cast<Json>()
            .map(
              (color) => FilterChip(
                label: Text(color['name'] as String),
                selected: selected.contains(color['id']),
                onSelected: (v) => setState(() {
                  if (v) {
                    selected.add(color['id'] as int);
                  } else {
                    selected.remove(color['id']);
                  }
                }),
              ),
            )
            .toList(),
      ),
      const SizedBox(height: 20),
    ],
  );
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Ваши предпочтения')),
    body: ListView(
      padding: const EdgeInsets.all(20),
      children: [
        if (error != null) MessageBox(error!, icon: Icons.error_outline),
        TextField(
          controller: name,
          maxLength: 100,
          decoration: const InputDecoration(labelText: 'Ваше имя'),
        ),
        TextField(
          controller: city,
          maxLength: 150,
          onChanged: (_) {
            lat.clear();
            lon.clear();
          },
          decoration: const InputDecoration(labelText: 'Город'),
        ),
        FilledButton.tonalIcon(
          onPressed: busy
              ? null
              : () async {
                  setState(() => busy = true);
                  try {
                    final data =
                        await widget.api.request(
                              '/api/locations/?search=${Uri.encodeQueryComponent(city.text)}',
                            )
                            as Json;
                    if (mounted && context.mounted) {
                      setState(
                        () =>
                            locations = (data['results'] as List).cast<Json>(),
                      );
                    }
                    if (locations.isEmpty) {
                      throw const ApiException(
                        'Город не найден. Уточните название или укажите координаты вручную.',
                      );
                    }
                  } catch (e) {
                    if (mounted && context.mounted) {
                      setState(() => error = e.toString());
                    }
                  } finally {
                    if (mounted && context.mounted) {
                      setState(() => busy = false);
                    }
                  }
                },
          icon: const Icon(Icons.search),
          label: const Text('Найти город'),
        ),
        for (final item in locations)
          ListTile(
            title: Text('${item['name']} · ${item['country']}'),
            subtitle: Text(item['region'] as String? ?? ''),
            onTap: () => setState(() {
              city.text = item['name'] as String;
              lat.text = (item['latitude'] as num).toStringAsFixed(5);
              lon.text = (item['longitude'] as num).toStringAsFixed(5);
              locations = [];
            }),
          ),
        const SizedBox(height: 15),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: lat,
                keyboardType: const TextInputType.numberWithOptions(
                  signed: true,
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: 'Широта'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: TextField(
                controller: lon,
                keyboardType: const TextInputType.numberWithOptions(
                  signed: true,
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: 'Долгота'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 15),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<int>(
                initialValue: cold,
                decoration: const InputDecoration(
                  labelText: 'Чувств. к холоду',
                ),
                items: [1, 2, 3, 4, 5]
                    .map(
                      (n) => DropdownMenuItem(value: n, child: Text('$n / 5')),
                    )
                    .toList(),
                onChanged: (v) => cold = v!,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: DropdownButtonFormField<int>(
                initialValue: heat,
                decoration: const InputDecoration(labelText: 'Чувств. к жаре'),
                items: [1, 2, 3, 4, 5]
                    .map(
                      (n) => DropdownMenuItem(value: n, child: Text('$n / 5')),
                    )
                    .toList(),
                onChanged: (v) => heat = v!,
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),
        TextField(
          controller: styles,
          decoration: const InputDecoration(
            labelText: 'Стили через запятую',
            hintText: 'casual, minimalism',
          ),
        ),
        const SizedBox(height: 15),
        DropdownButtonFormField<String>(
          initialValue: fit,
          decoration: const InputDecoration(labelText: 'Предпочтительный крой'),
          items: fits.entries
              .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
              .toList(),
          onChanged: (v) => fit = v!,
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
        colors('Любимые цвета', preferred),
        colors('Нежелательные цвета', disliked),
        Text(
          'Исключённые категории',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        ...(widget.data['categories'] as List).cast<Json>().map(
          (c) => CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(c['name'] as String),
            value: excluded.contains(c['id']),
            onChanged: (v) => setState(() {
              if (v == true) {
                excluded.add(c['id'] as int);
              } else {
                excluded.remove(c['id']);
              }
            }),
          ),
        ),
        FilledButton(
          onPressed: busy ? null : save,
          child: Text(busy ? 'Сохраняем…' : 'Сохранить настройки'),
        ),
        const SizedBox(height: 25),
      ],
    ),
  );
}
