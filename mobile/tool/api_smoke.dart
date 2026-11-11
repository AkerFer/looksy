// Exercises the actual Dart mobile client against a running Django server.
// Creates a temporary account and removes it, with all related data, afterwards.
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:looksy_mobile/services/api.dart';

class MemoryStore implements SessionStore {
  String? value;
  @override
  Future<String?> read() async => value;
  @override
  Future<void> write(String value) async => this.value = value;
  @override
  Future<void> clear() async => value = null;
}

void check(bool condition, String description) {
  if (!condition) throw StateError(description);
}

Future<void> main(List<String> args) async {
  final store = MemoryStore();
  final api = LooksyApi(store: store);
  final suffix = List.generate(
    12,
    (_) => Random.secure().nextInt(16).toRadixString(16),
  ).join();
  final username = 'mobile_smoke_$suffix';
  final password = 'Looksy-$suffix-Pass!234';
  var registered = false;
  try {
    await api.configure(args.isEmpty ? 'http://127.0.0.1:8000' : args.first);
    await api.register(username, password, 'Mobile smoke', '');
    registered = true;
    await api.login(username, password);
    final categories = await api.collection('/api/categories/');
    final ids = <int>[];
    for (final slot in ['top', 'bottom', 'shoes']) {
      final category = categories.firstWhere((item) => item['slot'] == slot);
      final item =
          await api.request(
                '/api/clothing/',
                method: 'POST',
                body: {
                  'name': 'Mobile $slot',
                  'category': category['id'],
                  'styles': ['casual'],
                  'comfort': 4,
                  'warmth': 3,
                },
              )
              as Map;
      ids.add(item['id'] as int);
    }
    final photo = await File(
      '../frontend/tests/fixtures/shirt.png',
    ).readAsBytes();
    await api.upload('/api/clothing/${ids.first}/photo/', photo, 'shirt.png');
    check(
      (await api.photo('/api/clothing/${ids.first}/photo/')).isNotEmpty,
      'Private photo missing',
    );
    final before = jsonDecode(store.value!)['refresh'];
    await api.refreshSession();
    check(
      jsonDecode(store.value!)['refresh'] != before,
      'Refresh token was not rotated',
    );
    check(
      (await api.photo('/api/clothing/${ids.first}/photo/')).isNotEmpty,
      'Photo after refresh',
    );
    final generated =
        await api.request(
              '/api/outfits/generate/',
              method: 'POST',
              body: {'count': 3, 'temperature_c': 20, 'style': 'casual'},
            )
            as Map;
    final outfits = generated['results'] as List;
    check(outfits.isNotEmpty, 'No outfit generated');
    final outfit = outfits.first as Map;
    check(
      (outfit['items'] as List).every(ids.contains),
      'Foreign clothing in result',
    );
    await api.request(
      '/api/saved-outfits/',
      method: 'POST',
      body: {'outfit': outfit['id']},
    );
    await api.request(
      '/api/feedback/',
      method: 'POST',
      body: {'outfit': outfit['id'], 'rating': 5, 'comment': 'Mobile smoke'},
    );
    await api.request(
      '/api/calendar/',
      method: 'POST',
      body: {
        'outfit': outfit['id'],
        'date': DateTime.now().toIso8601String().substring(0, 10),
        'note': 'Mobile smoke',
      },
    );
    await api.request(
      '/api/profile/',
      method: 'PATCH',
      body: {'display_name': 'Mobile verified'},
    );
    check(
      (await api.request('/api/profile/'))['display_name'] == 'Mobile verified',
      'Profile not saved',
    );
    check(
      (await api.collection('/api/saved-outfits/')).length == 1,
      'Favorite not saved',
    );
    stdout.writeln(
      'PASS: real Django registration, JWT rotation, wardrobe CRUD, private photo, generation, favorites, feedback, calendar, profile.',
    );
  } finally {
    if (registered) {
      if (!api.signedIn) await api.login(username, password);
      await api.deleteAccount(password);
      check(store.value == null && !api.signedIn, 'Session not cleared');
      stdout.writeln('Temporary account and all related data removed.');
    }
    api.dispose();
  }
}
