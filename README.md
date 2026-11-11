# Looksy

**[Пошаговый запуск в VS Code: Windows, Linux и macOS](docs/local-setup.md).**

Этапы 1–6: Django backend и Next.js веб-приложение с гардеробом, приватными фото, генератором, избранным, календарём и настройками. Погода/AI имеют резервный режим; живые Open-Meteo/Ollama пока недоступны в этой среде. Добавлен нативный Flutter-клиент Android: [APK, подключение телефона и сборка](mobile/README.md).

[Фото: установка модели, API и ограничения распознавания](docs/stage-3.md).
[Генератор: API, оценки и ограничения](docs/stage-4.md).
[Погода и AI: API, настройка сети и ограничения](docs/stage-5.md).
[Веб-интерфейс: запуск и браузерные проверки](docs/stage-6.md).
[Архитектура и этапы](docs/architecture.md). [API и сценарии этапа 2](docs/stage-2.md).

## Локальный запуск (Python 3.12)

```bash
cd /workspace/looksy
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
# Запишите в DJANGO_SECRET_KEY результат команды:
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
# Укажите также POSTGRES_PASSWORD в .env (случайный локальный пароль БД).
docker compose up -d --wait db
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Не перезаписывайте существующий .env. DEBUG=true предназначен только для локальной
разработки. Секрет не коммитить. В подготовленной среде .env и .venv уже созданы.

## Проверки

```bash
cd /workspace/looksy/backend
../.venv/bin/python manage.py check
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py test
curl --fail http://127.0.0.1:8000/health/
```

## REST API

Все URL со слешем на конце. JSON, пагинация `count/next/previous/results`.

| URL | Методы | Назначение |
| --- | --- | --- |
| `/health/` | GET | Проверка HTTP процесса |
| `/api/auth/session/` | GET, POST, DELETE | CSRF, вход, выход |
| `/api/auth/register/` | POST | username, password; email, display_name (необязательны) |
| `/api/account/` | GET, DELETE | Данные аккаунта, удаление с password |
| `/api/profile/` | GET, PATCH | Имя, город, чувствительность к температуре |
| `/api/preferences/` | GET, PATCH | Стили, цвета, крой, комфорт, исключённые категории |
| `/api/clothing/` | GET, POST | CRUD вещей, поиск, фильтры и сортировка |
| `/api/clothing/summary/` | GET | Сводка своего гардероба с фильтрами |
| `/api/outfits/generate/` | POST | Подбор и сохранение 3–5 образов (или меньше, если вариантов недостаточно) |
| `/api/outfits/` | GET, POST | name, items: список ID своих вещей |
| `/api/feedback/` | GET, POST | outfit, rating (1–5), comment |
| `/api/saved-outfits/` | GET, POST | outfit |
| `/api/locations/` | GET | Поиск городов Open-Meteo |
| `/api/weather/forecast/` | POST | Прогноз и сохранение своего контекста |
| `/api/stylist/` | POST | Локальный AI или резервный подбор |
| `/api/calendar/` | GET, POST | Свои планы образов на даты; detail — PATCH/DELETE |
| `/api/weather/` | GET | Сохранённый погодный контекст |
| `/api/categories/`, `/api/colors/` | GET | Общие справочники |

Коллекции clothing/outfits/feedback/saved-outfits также поддерживают
GET/PATCH/PUT/DELETE по `/api/<коллекция>/<id>/`. Weather — только чтение.
Регистрация не выполняет автоматический вход.

Для входа сначала GET `/api/auth/session/`, сохраните cookie и передайте
`csrfToken` в `X-CSRFToken` при POST. После входа GET повторно: Django меняет CSRF.
Сессионную cookie и актуальный CSRF передавайте для всех изменяющих запросов.
При HTTPS также нужен корректный Origin/Referer. Чужие объекты недоступны.
JWT API доступен уже сейчас; интеграция Flutter и secure storage — этап 7.

Тесты проверяют реальную сессию/CSRF, регистрацию, ограничения, CRUD образов,
изоляцию коллекций и связей, удаление аккаунта. Алгоритмические тесты генератора находятся в wardrobe/test_generator.py.

## Уточнение стека по полному заданию

[Полное ТЗ](docs/product-specification.md) сохранено в репозитории.
PostgreSQL 17 — основная БД, настройки POSTGRES_* читаются из окружения/.env.
`docker compose up -d --wait db` запускает локальную БД; данные остаются в volume.
Не используйте `docker compose down -v`, если данные нужно сохранить.
SQLite — только явный резерв для локальных проверок:

```bash
cd /workspace/looksy/backend
DB_ENGINE=sqlite ../.venv/bin/python manage.py migrate
DB_ENGINE=sqlite ../.venv/bin/python manage.py test
DB_ENGINE=sqlite ../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Выбор БД не переносит существующие данные автоматически.

### JWT и Django Admin

- POST `/api/auth/token/`: username/password → access и refresh.
- `Authorization: Bearer <access>` для запросов к защищённому API.
- POST `/api/auth/token/refresh/`: refresh → новая пара токенов;
  предыдущий refresh отзывается.
- POST `/api/auth/token/logout/`: refresh → отзыв refresh-токена.
- Access действует 10 минут, refresh — 7 дней. Выход отзывает refresh;
  уже выданный access действует до истечения срока. Удалённый пользователь
  не может использовать оставшиеся токены.
- Не сохраняйте токены браузера в localStorage. Веб-клиент использует сессии Django с HttpOnly cookie и CSRF, без хранения JWT;
  для Flutter планируется secure storage на этапе 7.
- `/admin/`: административный интерфейс для доверенного персонала.
  Создание администратора: `../.venv/bin/python manage.py createsuperuser`.
  Обычные пользователи не имеют доступа к admin.
- Очистка истёкших записей JWT: `../.venv/bin/python manage.py flushexpiredtokens`.

Загрузка и обработка фото реализованы на этапе 3. Классификация без локальных весов явно недоступна; генератор работает без AI, доступны ручная температура и запрос Open-Meteo. AI-стилист и погода реализованы с обработкой отказов; живые сервисы заблокированы/не настроены, веб-клиент реализован; Flutter ещё не реализован.

## Проверенный результат этапа 1

Миграции применены к PostgreSQL 17 и SQLite. Набор из 15 тестов проверяет
изоляцию, связи, регистрацию, CSRF, JWT, ротацию/отзыв refresh и удаление аккаунта.
Через HTTP на PostgreSQL проверена цепочка: регистрация → JWT → создание вещи
и образа → refresh → удаление аккаунта. Этот раздел описывает результат этапа 1; веб-клиент добавлен на этапе 6.

## Фотографии (этап 3)

После установки зависимостей и миграций выполните `../.venv/bin/python manage.py prepare_photo_model` из backend. Загрузка и аватары: [описание API](docs/stage-3.md). Реальные веса классификатора одежды пока не установлены — категория выбирается вручную.

## Веб-приложение

После запуска backend откройте второй терминал:

```bash
cd /workspace/looksy/frontend
npm ci --cache /workspace/.npm-cache
npm run dev
```

Frontend работает на порту 3000 и проксирует API в Django на 8000.
Сессии/CSRF, приватные фото и backend календаря описаны в [этапе 6](docs/stage-6.md).
