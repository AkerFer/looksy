# Этап 2 — регистрация, профиль и цифровой гардероб

Backend API работает с реальной БД. Веб-экраны появятся на этапе 6.
Фотографии и аватары реализованы отдельно на [этапе 3](stage-3.md).

## Регистрация и настройки

POST `/api/auth/register/`: username, password, необязательные email и display_name.
Вместе с пользователем транзакционно создаются профиль и настройки подбора.
Для регистрации нужен CSRF: GET `/api/auth/session/`, затем cookie и заголовок
`X-CSRFToken`. JWT-вход и сессионный вход остаются доступными (см. README).
Регистрация не подтверждает владение email; верификация email пока отсутствует.

GET/PATCH `/api/profile/` работает только с профилем текущего пользователя:

- display_name, preferred_style (старое одиночное поле стиля).
- city — город, введённый вручную; геолокация не нужна.
- cold_sensitivity, heat_sensitivity — 1…5, по умолчанию 3.

GET/PATCH `/api/preferences/`:

- styles — до 20 уникальных строк, до 80 символов каждая.
- preferred_colors, disliked_colors — списки ID справочника цветов, без пересечения.
- preferred_fit: unknown, regular, slim, relaxed, oversized.
- comfort_priority: 0…100 (0 — внешний вид, 100 — комфорт), по умолчанию 50.
- excluded_categories — ID исключённых категорий.
- style — прежнее одиночное поле для совместимости; новый клиент использует styles.

Пустой список очищает настройку. PATCH сохраняет остальные значения.
Проверка пересечения цветов учитывает и сохранённые значения при частичном
обновлении. Настройки сохраняются, но будут использоваться генератором
только после его реализации на этапе 4; чувствительность к погоде — этап 5.

## Гардероб

POST `/api/clothing/` создаёт вещь. Обязательны name и category (ID справочника).
Дополнительные поля: colors (ID), description, season, is_available, brand,
material, fit, styles. Материал и крой вводятся вручную: неизвестный материал
остаётся пустым, неизвестный крой — unknown. created_at и updated_at задаёт сервер.

GET/PATCH/PUT/DELETE `/api/clothing/<id>/` — просмотр, редактирование, удаление.
`is_available=false` означает, например, что вещь в стирке. Удаление вещи удаляет
её связи OutfitItem, но сохраняет сам образ; образ может остаться пустым.
Недоступные вещи остаются видимыми; при генерации этапа 4 их нужно исключать.

GET `/api/clothing/` — пагинация по 30 вещей. Поддерживаются совместные фильтры:

| Параметр | Значения |
| --- | --- |
| search | Подстрока в названии, описании или бренде (без учёта регистра на PostgreSQL) |
| category, color | Один положительный ID |
| slot | top, bottom, dress, outerwear, shoes, accessory, other |
| season | all, summer, winter, spring, autumn (точное совпадение) |
| is_available | true / false |
| fit | unknown, regular, slim, relaxed, oversized |
| ordering | name, -name, created_at, -created_at, updated_at, -updated_at |
| page | Номер страницы |

По умолчанию: -created_at; дополнительная сортировка по ID обеспечивает
стабильный порядок при равных значениях. Пустые результаты возвращают count=0.
Некорректные, неизвестные и повторные фильтры возвращают 400. Чужой корректный
ID категории/цвета не открывает чужие вещи. Фильтры применяются только к коллекциям,
не к запросам по ID.

GET `/api/clothing/summary/` — total, available, unavailable и categories
(category_id, category__name, count). Принимает те же фильтры. Сводка учитывает
все результаты фильтра, до пагинации, и только вещи текущего пользователя.
Это размеры гардероба, а не статистика ношения — она появится отдельно.

Пример создания (с `Authorization: Bearer <access>`):

```json
{
  "name": "Мои чёрные брюки",
  "category": 4,
  "colors": [1],
  "season": "all",
  "fit": "regular",
  "styles": ["Minimalism"],
  "is_available": true
}
```

ID в примере нужно заменить на реальные из `/api/categories/` и `/api/colors/`.

## Запуск и проверка

```bash
cd /workspace/looksy
docker compose up -d --wait db
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py test
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

В другом терминале (сервер должен быть запущен):

```bash
cd /workspace/looksy/backend
../.venv/bin/python scripts/smoke_wardrobe.py http://127.0.0.1:8000
```

Smoke создаёт временный настоящий аккаунт, проверяет настройки и CRUD, затем
удаляет аккаунт. Секреты и токены в вывод не попадают. Пустые существующие
профили и гардеробы остаются пустыми: фиктивные вещи не создаются.

Проверка текущего этапа: все 26 тестов прошли на PostgreSQL; 11 новых тестов
гардероба прошли также на SQLite. Миграции 0003/0004 применены в обеих БД.
Django check и проверка отсутствия несозданных миграций прошли.
HTTP smoke выполнен на PostgreSQL, временный аккаунт удалён.
