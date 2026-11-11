import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:looksy_mobile/services/api.dart';
import 'widget_test.dart' show MemoryStore;

http.Response json(Object data, [int status = 200]) =>
    http.Response(jsonEncode(data), status);

void main() {
  test('Only HTTPS or private LAN HTTP roots are accepted', () {
    for (final value in [
      'https://looksy.example',
      'http://192.168.1.5:8000',
      'http://10.0.2.2:8000',
      'http://127.0.0.1:8000',
    ]) {
      expect(LooksyApi.parseServer(value).path, '/');
    }
    for (final value in [
      'http://looksy.example',
      'https://u:p@looksy.example',
      'https://looksy.example/api/',
      'file:///tmp/x',
      'http://8.8.8.8',
      'https://looksy.example?token=secret',
    ]) {
      expect(() => LooksyApi.parseServer(value), throwsA(isA<ApiException>()));
    }
  });

  test('Registration sends CSRF and only refresh is persisted', () async {
    final store = MemoryStore();
    final api = LooksyApi(
      store: store,
      client: MockClient((req) async {
        switch (req.url.path) {
          case '/health/':
            return json({'status': 'ok'});
          case '/api/auth/session/':
            return http.Response(
              '{"csrfToken":"csrf"}',
              200,
              headers: {'set-cookie': 'csrftoken=cookie; Path=/; SameSite=Lax'},
            );
          case '/api/auth/register/':
            expect(req.headers['cookie'], 'csrftoken=cookie');
            expect(req.headers['x-csrftoken'], 'csrf');
            expect(req.headers['origin'], 'https://looksy.example');
            expect(jsonDecode(req.body)['display_name'], 'Анна');
            return json({}, 201);
          default:
            return json({
              'access': 'access-secret',
              'refresh': 'refresh-secret',
            });
        }
      }),
    );
    addTearDown(api.dispose);
    await api.configure('https://looksy.example');
    await api.register('anna', 'password-secret', 'Анна', '');
    await api.login('anna', 'password-secret');
    expect(jsonDecode(store.value!)['refresh'], 'refresh-secret');
    expect(store.value, isNot(contains('password-secret')));
    expect(store.value, isNot(contains('access-secret')));
  });

  test(
    'Concurrent expired requests share refresh and persist rotation',
    () async {
      final store = MemoryStore();
      var refreshes = 0;
      final gate = Completer<void>();
      final api = LooksyApi(
        store: store,
        client: MockClient((req) async {
          if (req.url.path == '/health/') return json({'status': 'ok'});
          if (req.url.path == '/api/auth/token/') {
            return json({'access': 'expired', 'refresh': 'old-refresh'});
          }
          if (req.url.path == '/api/auth/token/refresh/') {
            refreshes++;
            await gate.future;
            return json({'access': 'new-access', 'refresh': 'rotated-refresh'});
          }
          if (req.headers['authorization'] == 'Bearer new-access') {
            return json({'ok': true});
          }
          return json({'detail': 'expired'}, 403);
        }),
      );
      addTearDown(api.dispose);
      await api.configure('https://looksy.example');
      await api.login('anna', 'password');
      final first = api.request('/api/profile/');
      final second = api.request('/api/preferences/');
      await Future<void>.delayed(const Duration(milliseconds: 20));
      gate.complete();
      expect(await first, {'ok': true});
      expect(await second, {'ok': true});
      expect(refreshes, 1);
      expect(jsonDecode(store.value!)['refresh'], 'rotated-refresh');
    },
  );

  test('Foreign photos and pagination cannot receive bearer tokens', () async {
    final seen = <Uri>[];
    final api = LooksyApi(
      store: MemoryStore(),
      client: MockClient((req) async {
        seen.add(req.url);
        if (req.url.path == '/health/') return json({'status': 'ok'});
        return json({
          'results': [],
          'next': 'https://evil.example/api/clothing/',
        });
      }),
    );
    addTearDown(api.dispose);
    await api.configure('https://looksy.example');
    await expectLater(
      api.photo('https://evil.example/api/photo/'),
      throwsA(isA<ApiException>()),
    );
    await expectLater(
      api.collection('/api/clothing/'),
      throwsA(isA<ApiException>()),
    );
    expect(seen.every((url) => url.host == 'looksy.example'), isTrue);
    await expectLater(
      api.upload(
        '/api/clothing/1/photo/',
        Uint8List(5 * 1024 * 1024 + 1),
        'big.jpg',
      ),
      throwsA(isA<ApiException>()),
    );
  });

  test('Logout clears local session even when server is offline', () async {
    final store = MemoryStore();
    final api = LooksyApi(
      store: store,
      client: MockClient((req) async {
        if (req.url.path == '/health/') return json({'status': 'ok'});
        if (req.url.path.endsWith('/logout/')) {
          throw http.ClientException('offline');
        }
        return json({'access': 'access', 'refresh': 'refresh'});
      }),
    );
    addTearDown(api.dispose);
    await api.configure('https://looksy.example');
    await api.login('anna', 'password');
    await expectLater(api.logout(), throwsA(isA<ApiException>()));
    expect(api.signedIn, isFalse);
    expect(store.value, isNull);
  });

  test('In-flight login cannot restore an account after logout', () async {
    final gate = Completer<http.Response>();
    final store = MemoryStore();
    final api = LooksyApi(
      store: store,
      client: MockClient((req) async {
        if (req.url.path == '/health/') return json({'status': 'ok'});
        return gate.future;
      }),
    );
    addTearDown(api.dispose);
    await api.configure('https://looksy.example');
    final login = api.login('anna', 'password');
    final check = expectLater(login, throwsA(isA<ApiException>()));
    await api.forget();
    gate.complete(json({'access': 'access', 'refresh': 'refresh'}));
    await check;
    expect(api.signedIn, isFalse);
    expect(store.value, isNull);
  });
}
