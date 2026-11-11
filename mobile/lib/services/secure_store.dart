import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api.dart';

class SecureSessionStore implements SessionStore {
  final FlutterSecureStorage storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  @override
  Future<String?> read() => storage.read(key: 'looksy_session_v1');
  @override
  Future<void> write(String value) =>
      storage.write(key: 'looksy_session_v1', value: value);
  @override
  Future<void> clear() => storage.delete(key: 'looksy_session_v1');
}
