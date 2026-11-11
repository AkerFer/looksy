import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

abstract class SessionStore {
  Future<String?> read();
  Future<void> write(String value);
  Future<void> clear();
}

class ApiException implements Exception {
  final String message;
  final int? status;
  const ApiException(this.message, [this.status]);
  @override
  String toString() => message;
}

class LooksyApi {
  LooksyApi({required this.store, http.Client? client})
    : client = client ?? http.Client();
  final SessionStore store;
  final http.Client client;
  final changes = StreamController<void>.broadcast();
  Uri? server;
  String? _access;
  String? _refresh;
  Future<void>? _refreshing;
  int _epoch = 0;
  int get epoch => _epoch;
  bool get signedIn => _access != null;

  static Uri parseServer(String input) {
    final value = Uri.tryParse(input.trim());
    if (value == null ||
        value.host.isEmpty ||
        value.userInfo.isNotEmpty ||
        value.hasQuery ||
        value.hasFragment ||
        !['http', 'https'].contains(value.scheme) ||
        !['', '/'].contains(value.path)) {
      throw const ApiException(
        'Введите адрес backend, например http://192.168.1.5:8000, без /api/.',
      );
    }
    if (value.scheme == 'http') {
      final ip = value.host.split('.').map(int.tryParse).toList();
      final local =
          value.host == 'localhost' ||
          value.host == '::1' ||
          (ip.length == 4 &&
              ip.every((n) => n != null && n >= 0 && n <= 255) &&
              (ip[0] == 10 ||
                  ip[0] == 127 ||
                  (ip[0] == 192 && ip[1] == 168) ||
                  (ip[0] == 172 && ip[1]! >= 16 && ip[1]! <= 31)));
      if (!local) {
        throw const ApiException(
          'Для публичного сервера требуется HTTPS. HTTP разрешён только для локальной сети.',
        );
      }
    }
    return value.replace(path: '/');
  }

  Future<void> restore() async {
    try {
      final saved = await store.read();
      if (saved == null) return;
      final data = jsonDecode(saved) as Map<String, dynamic>;
      server = parseServer(data['server'] as String);
      _refresh = data['refresh'] as String?;
      if (_refresh != null) await refreshSession();
    } catch (_) {
      _access = null;
      _refresh = null;
      await store.clear();
    }
    changes.add(null);
  }

  Future<void> configure(String value) async {
    final next = parseServer(value);
    if (server != next) {
      await forget(notify: signedIn);
      server = next;
      await _save();
    }
    final data = await request('/health/', auth: false) as Map;
    if (data['status'] != 'ok') {
      throw const ApiException(
        'Этот адрес не отвечает как Looksy API. Проверьте порт 8000.',
      );
    }
  }

  Uri _url(String path) {
    if (server == null) {
      throw const ApiException('Сначала укажите адрес backend.');
    }
    final result = server!.resolve(path);
    if (result.origin != server!.origin ||
        result.userInfo.isNotEmpty ||
        !result.path.startsWith('/api/') && result.path != '/health/') {
      throw const ApiException('Отклонена ссылка на другой сервер.');
    }
    return result;
  }

  Future<void> _save() => store.write(
    jsonEncode({'server': server.toString(), 'refresh': _refresh}),
  );
  Future<void> forget({bool notify = true}) async {
    _epoch++;
    _access = null;
    _refresh = null;
    _refreshing = null;
    await store.clear();
    if (notify) changes.add(null);
  }

  Future<void> login(String username, String password) async {
    final start = _epoch;
    final data =
        await request(
              '/api/auth/token/',
              method: 'POST',
              body: {'username': username, 'password': password},
              auth: false,
            )
            as Map;
    if (start != _epoch) {
      throw const ApiException(
        'Настройки подключения изменились. Повторите вход.',
      );
    }
    _access = data['access'] as String;
    _refresh = data['refresh'] as String;
    try {
      await _save();
    } catch (_) {
      _access = null;
      _refresh = null;
      throw const ApiException(
        'Не удалось сохранить сессию в защищённом хранилище.',
      );
    }
    changes.add(null);
  }

  Future<void> register(
    String username,
    String password,
    String name,
    String email,
  ) async {
    // Django protects registration with CSRF, including native clients.
    final response = await _send(
      http.Request('GET', _url('/api/auth/session/')),
    );
    final session = _decode(response) as Map;
    final cookie = RegExp(
      r'(?:^|,\s*)csrftoken=([^;,\s]+)',
    ).firstMatch(response.headers['set-cookie'] ?? '')?.group(1);
    if (cookie == null) {
      throw const ApiException('Backend не выдал CSRF cookie для регистрации.');
    }
    final req = http.Request('POST', _url('/api/auth/register/'));
    req.headers.addAll({
      'Content-Type': 'application/json',
      'Cookie': 'csrftoken=$cookie',
      'X-CSRFToken': session['csrfToken'] as String,
      'Origin': server!.origin,
    });
    req.body = jsonEncode({
      'username': username,
      'password': password,
      'display_name': name,
      'email': email,
    });
    _decode(await _send(req));
  }

  Future<void> refreshSession() {
    if (_refreshing != null) return _refreshing!;
    final future = _doRefresh();
    _refreshing = future;
    return future.whenComplete(() {
      if (identical(_refreshing, future)) _refreshing = null;
    });
  }

  Future<void> _doRefresh() async {
    if (_refresh == null) throw const ApiException('Войдите в аккаунт заново.');
    final start = _epoch;
    try {
      final data =
          await request(
                '/api/auth/token/refresh/',
                method: 'POST',
                body: {'refresh': _refresh},
                auth: false,
              )
              as Map;
      if (start != _epoch) throw const ApiException('Сессия изменена.');
      _access = data['access'] as String;
      _refresh = data['refresh'] as String? ?? _refresh;
      await _save();
    } catch (_) {
      if (start == _epoch) await forget();
      rethrow;
    }
  }

  Future<dynamic> request(
    String path, {
    String method = 'GET',
    Object? body,
    bool auth = true,
  }) async {
    final response = await _authorized(() {
      final req = http.Request(method, _url(path));
      req.headers['Accept'] = 'application/json';
      if (body != null) {
        req.headers['Content-Type'] = 'application/json';
        req.body = jsonEncode(body);
      }
      return req;
    }, auth: auth);
    return _decode(response);
  }

  Future<http.Response> _authorized(
    http.BaseRequest Function() build, {
    bool auth = true,
  }) async {
    final start = _epoch;
    Future<http.Response> send() async {
      final req = build();
      if (auth && _access != null) {
        req.headers['Authorization'] = 'Bearer $_access';
      }
      return _send(req);
    }

    var response = await send();
    if (start != _epoch) {
      throw const ApiException('Сессия изменена. Повторите действие.');
    }
    if (auth &&
        (response.statusCode == 401 || response.statusCode == 403) &&
        _refresh != null) {
      await refreshSession();
      if (start != _epoch) throw const ApiException('Нужен повторный вход.');
      response = await send();
    }
    if (start != _epoch) throw const ApiException('Сессия изменена.');
    return response;
  }

  Future<http.Response> _send(http.BaseRequest req) async {
    req.followRedirects = false;
    try {
      return await http.Response.fromStream(
        await client.send(req),
      ).timeout(const Duration(seconds: 90));
    } on TimeoutException {
      throw const ApiException(
        'Сервер отвечает слишком долго. Попробуйте позже.',
      );
    } on http.ClientException {
      throw const ApiException(
        'Нет соединения с backend. Проверьте Wi-Fi, адрес сервера и запуск Django.',
      );
    }
  }

  dynamic _decode(http.Response response) {
    if (response.statusCode == 204) return null;
    dynamic data;
    try {
      data = jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      throw ApiException(
        'Backend вернул неподходящий ответ (${response.statusCode}). Проверьте адрес, порт 8000 и DJANGO_ALLOWED_HOSTS.',
        response.statusCode,
      );
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(_error(data), response.statusCode);
    }
    return data;
  }

  String _error(dynamic data) {
    if (data is String) return data;
    if (data is List) return data.map(_error).join(' ');
    if (data is Map) {
      return data.entries
          .map(
            (e) => '${e.key == 'detail' ? '' : '${e.key}: '}${_error(e.value)}',
          )
          .join('\n');
    }
    return 'Не удалось выполнить запрос.';
  }

  Future<List<Map<String, dynamic>>> collection(String path) async {
    final rows = <Map<String, dynamic>>[];
    String? next = path;
    while (next != null) {
      final data = await request(next) as Map;
      rows.addAll((data['results'] as List).cast<Map<String, dynamic>>());
      final value = data['next'] as String?;
      if (value == null) {
        next = null;
      } else {
        // Django may advertise a proxy host. Only accept the same origin.
        next = _url(value).toString();
      }
      if (rows.length > 5000) {
        throw const ApiException('Слишком большая коллекция. Сузьте поиск.');
      }
    }
    return rows;
  }

  Future<Uint8List> photo(String path) async {
    final response = await _authorized(() => http.Request('GET', _url(path)));
    if (response.statusCode != 200) {
      _decode(response);
    }
    if (!(response.headers['content-type'] ?? '').startsWith('image/')) {
      throw const ApiException('Не удалось получить фотографию.');
    }
    return response.bodyBytes;
  }

  Future<void> upload(String path, Uint8List bytes, String filename) async {
    if (bytes.length > 5 * 1024 * 1024) {
      throw const ApiException('Размер фото должен быть не больше 5 МБ.');
    }
    final response = await _authorized(
      () => http.MultipartRequest('POST', _url(path))
        ..files.add(
          http.MultipartFile.fromBytes('image', bytes, filename: filename),
        ),
    );
    _decode(response);
  }

  Future<void> logout() async {
    final refresh = _refresh;
    final revoke = refresh == null
        ? null
        : (http.Request('POST', _url('/api/auth/token/logout/'))
            ..headers['Content-Type'] = 'application/json'
            ..body = jsonEncode({'refresh': refresh}));
    // Remove private screens immediately, even if revocation times out offline.
    await forget();
    if (revoke != null) {
      _decode(await _send(revoke));
    }
  }

  Future<void> deleteAccount(String password) async {
    await request(
      '/api/account/',
      method: 'DELETE',
      body: {'password': password},
    );
    await forget();
  }

  void dispose() {
    client.close();
    changes.close();
  }
}
