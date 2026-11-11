import 'package:flutter/material.dart';
import '../services/api.dart';
import 'shared.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({required this.api, this.initialError, super.key});
  final LooksyApi api;
  final String? initialError;
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final form = GlobalKey<FormState>();
  final server = TextEditingController();
  final username = TextEditingController();
  final password = TextEditingController();
  final name = TextEditingController();
  final email = TextEditingController();
  bool register = false, busy = false, obscure = true;
  String? error;
  @override
  void initState() {
    super.initState();
    server.text = widget.api.server?.origin ?? '';
    error = widget.initialError;
  }

  @override
  void dispose() {
    for (final c in [server, username, password, name, email]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> submit() async {
    if (!form.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await widget.api.configure(server.text);
      if (register) {
        await widget.api.register(
          username.text.trim(),
          password.text,
          name.text.trim(),
          email.text.trim(),
        );
      }
      await widget.api.login(username.text.trim(), password.text);
    } catch (e) {
      if (mounted && context.mounted) setState(() => error = e.toString());
    } finally {
      if (mounted && context.mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Form(
              key: form,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.auto_awesome,
                        color: Theme.of(context).colorScheme.primary,
                        size: 32,
                      ),
                      const SizedBox(width: 10),
                      Text(
                        'looksy.',
                        style: Theme.of(context).textTheme.displaySmall,
                      ),
                    ],
                  ),
                  const SizedBox(height: 22),
                  Text(
                    'Ваши вещи. Новые истории.',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Личный гардероб и образы из того, что у вас уже есть.',
                  ),
                  const SizedBox(height: 26),
                  TextFormField(
                    controller: server,
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    decoration: const InputDecoration(
                      labelText: 'Адрес backend',
                      hintText: 'http://192.168.1.5:8000',
                      prefixIcon: Icon(Icons.dns_outlined),
                    ),
                    validator: (v) {
                      try {
                        LooksyApi.parseServer(v ?? '');
                        return null;
                      } catch (e) {
                        return e.toString();
                      }
                    },
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Телефон и компьютер должны быть в одной Wi-Fi сети. Укажите IPv4 компьютера из ipconfig, не localhost. Для опубликованного сервера используйте HTTPS.',
                    style: TextStyle(fontSize: 12),
                  ),
                  const SizedBox(height: 20),
                  SegmentedButton<bool>(
                    segments: const [
                      ButtonSegment(value: false, label: Text('Вход')),
                      ButtonSegment(value: true, label: Text('Регистрация')),
                    ],
                    selected: {register},
                    onSelectionChanged: busy
                        ? null
                        : (v) => setState(() => register = v.first),
                  ),
                  const SizedBox(height: 20),
                  if (register) ...[
                    TextFormField(
                      controller: name,
                      decoration: const InputDecoration(labelText: 'Ваше имя'),
                      maxLength: 100,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: email,
                      decoration: const InputDecoration(
                        labelText: 'Email (необязательно)',
                      ),
                      keyboardType: TextInputType.emailAddress,
                    ),
                    const SizedBox(height: 16),
                  ],
                  TextFormField(
                    controller: username,
                    autocorrect: false,
                    decoration: const InputDecoration(
                      labelText: 'Имя пользователя',
                    ),
                    validator: (v) => (v ?? '').trim().isEmpty
                        ? 'Введите имя пользователя'
                        : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: password,
                    obscureText: obscure,
                    autocorrect: false,
                    enableSuggestions: false,
                    decoration: InputDecoration(
                      labelText: 'Пароль',
                      suffixIcon: IconButton(
                        tooltip: 'Показать или скрыть пароль',
                        onPressed: () => setState(() => obscure = !obscure),
                        icon: Icon(
                          obscure
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                        ),
                      ),
                    ),
                    validator: (v) =>
                        (v ?? '').isEmpty ? 'Введите пароль' : null,
                  ),
                  if (error != null)
                    MessageBox(error!, icon: Icons.error_outline),
                  const SizedBox(height: 20),
                  FilledButton(
                    onPressed: busy ? null : submit,
                    child: Text(
                      busy
                          ? 'Подключаемся…'
                          : register
                          ? 'Создать аккаунт'
                          : 'Войти',
                    ),
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    'Фото остаются приватными. AI и погода могут быть недоступны — образы подбираются и по локальным правилам.',
                    style: TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
