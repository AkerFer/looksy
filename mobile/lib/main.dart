import 'dart:async';
import 'package:flutter/material.dart';
import 'services/api.dart';
import 'services/secure_store.dart';
import 'ui/auth.dart';
import 'ui/home.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(LooksyApp(api: LooksyApi(store: SecureSessionStore())));
}

class LooksyApp extends StatefulWidget {
  const LooksyApp({required this.api, super.key});
  final LooksyApi api;
  @override
  State<LooksyApp> createState() => _LooksyAppState();
}

class _LooksyAppState extends State<LooksyApp> {
  bool loading = true;
  ThemeMode mode = ThemeMode.system;
  String? error;
  StreamSubscription<void>? sub;
  @override
  void initState() {
    super.initState();
    sub = widget.api.changes.stream.listen((_) {
      if (mounted) setState(() {});
    });
    initialize();
  }

  Future<void> initialize() async {
    try {
      await widget.api.restore();
    } catch (_) {
      error =
          'Не удалось восстановить защищённую сессию. Выполните вход заново.';
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  ThemeData theme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF8B75BF),
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: brightness == Brightness.light
          ? const Color(0xFFFAF8F5)
          : const Color(0xFF19181E),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.outlineVariant),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: scheme.surface,
        margin: const EdgeInsets.symmetric(vertical: 8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(44, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    sub?.cancel();
    widget.api.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    key: ValueKey(widget.api.epoch),
    title: 'Looksy',
    debugShowCheckedModeBanner: false,
    theme: theme(Brightness.light),
    darkTheme: theme(Brightness.dark),
    themeMode: mode,
    home: loading
        ? const Scaffold(body: Center(child: CircularProgressIndicator()))
        : widget.api.signedIn
        ? HomeScreen(
            api: widget.api,
            toggleTheme: () => setState(
              () => mode = mode == ThemeMode.dark
                  ? ThemeMode.light
                  : ThemeMode.dark,
            ),
          )
        : AuthScreen(api: widget.api, initialError: error),
  );
}
