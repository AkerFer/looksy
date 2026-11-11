import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:looksy_mobile/main.dart';
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

void main() {
  testWidgets(
    'Validates connection, opens account, clears private routes on logout',
    (tester) async {
      final calls = <String>[];
      final api = LooksyApi(
        store: MemoryStore(),
        client: MockClient((req) async {
          calls.add(req.url.path);
          final data = switch (req.url.path) {
            '/health/' => {'status': 'ok'},
            '/api/auth/token/' => {'access': 'access', 'refresh': 'refresh'},
            '/api/profile/' => {'display_name': 'Анна'},
            '/api/clothing/summary/' => {'total': 0},
            _ => {'results': [], 'next': null},
          };
          return http.Response(
            jsonEncode(data),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      await tester.pumpWidget(LooksyApp(api: api));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Войти'));
      await tester.tap(find.widgetWithText(FilledButton, 'Войти'));
      await tester.pumpAndSettle();
      expect(find.text('Введите имя пользователя'), findsOneWidget);
      expect(calls, isEmpty);
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), 'http://192.168.1.5:8000');
      await tester.enterText(fields.at(1), 'anna');
      await tester.enterText(fields.at(2), 'test-password');
      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Войти'));
      await tester.tap(find.widgetWithText(FilledButton, 'Войти'));
      await tester.pumpAndSettle();
      expect(find.text('Привет, Анна!'), findsOneWidget);
      expect(find.text('0 вещей'), findsOneWidget);
      expect(
        calls,
        containsAll(['/health/', '/api/auth/token/', '/api/profile/']),
      );
      await tester.tap(find.byTooltip('Календарь'));
      await tester.pumpAndSettle();
      await api.forget();
      await tester.pumpAndSettle();
      expect(find.text('Адрес backend'), findsOneWidget);
      expect(find.byType(NavigationBar), findsNothing);
    },
  );
}
