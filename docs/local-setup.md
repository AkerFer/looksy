# Запуск Looksy в VS Code

Нужны Git, Python 3.12, Node.js 24 (проверено 24.22.1), VS Code и запущенный
Docker Desktop с Linux-контейнерами. PostgreSQL отдельно устанавливать не нужно:
его запускает Compose. В Windows команды ниже рассчитаны на PowerShell.
Активация virtualenv не требуется, поэтому политику выполнения PowerShell менять
не нужно.

## 1. Получить проект

В терминале VS Code:

```bash
git clone https://github.com/AkerFer/looksy.git
cd looksy
code .
```

Если репозиторий уже клонирован, откройте его папку в VS Code, сохраните свои
изменения и обновите рабочую копию: `git pull --ff-only origin main`.
Дальнейшие команды запускайте из корня проекта `looksy`.

## 2. Backend — Windows PowerShell

Первоначальная установка:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\scripts\init_env.py
docker compose up -d --wait db
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Последняя команда занимает терминал, пока работает backend. Не закрывайте его.
Если команда `py` отсутствует, используйте `python -m venv .venv`, предварительно
проверив, что `python --version` показывает 3.12.

## 2. Backend — Linux / macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python backend/scripts/init_env.py
docker compose up -d --wait db
.venv/bin/python backend/manage.py migrate
.venv/bin/python backend/manage.py runserver 127.0.0.1:8000
```

В Linux вместо Docker Desktop можно использовать Docker Engine с Compose plugin.
Зависимости и сценарий запуска проверены в Linux. Команды Windows приведены для
PowerShell, но на Windows/macOS установка и запуск в этой среде не проверялись.
Если системные ML-пакеты не устанавливаются на вашей ОС, используйте WSL2/Linux.

`init_env.py` создаёт `.env` из примера со случайными DJANGO_SECRET_KEY и
POSTGRES_PASSWORD, не выводит их и не перезаписывает существующий `.env`.
При существующем `.env` проверьте, что секрет Django содержит минимум 32 символа,
а POSTGRES_PASSWORD заполнен. DEBUG=true подходит только для локальной разработки.
Файл `.env`, база, загруженные фото и веса моделей не входят в Git.

## 3. Frontend — второй терминал VS Code

Из корня проекта:

```bash
cd frontend
npm ci
npm run dev
```

Откройте **http://localhost:3000**. Backend работает на **http://127.0.0.1:8000**,
проверка процесса — `/health/`. Зарегистрируйте свой аккаунт: готового логина и
пароля, демонстрационных пользователей и гардеробов нет.

Frontend сам проксирует `/api/` в backend. Дополнительный `.env.local` не нужен
при стандартных портах. Секреты Django в frontend не копируются. Не запускайте
два процесса Next.js одновременно на порту 3000. Если меняете адрес/порт сайта,
добавьте новый origin в DJANGO_CSRF_TRUSTED_ORIGINS корневого `.env` и перезапустите
backend. Для изменения адреса backend задайте BACKEND_URL по frontend/.env.example.

## 4. Следующие запуски

Устанавливать окружение заново не нужно.

Windows, первый терминал:

```powershell
docker compose up -d --wait db
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Linux/macOS, первый терминал:

```bash
docker compose up -d --wait db
.venv/bin/python backend/manage.py migrate
.venv/bin/python backend/manage.py runserver 127.0.0.1:8000
```

Второй терминал на любой ОС: `cd frontend`, затем `npm run dev`.
После обновления зависимостей повторите pip install и npm ci.
Остановка серверов — Ctrl+C. Остановка БД — `docker compose stop db`.
Не удаляйте Docker volume, если хотите сохранить свой гардероб.

## Фото, погода и AI

Для нейросетевого удаления фона (необязательно для запуска сайта):

```powershell
# Windows, из корня проекта:
.\.venv\Scripts\python.exe backend\manage.py prepare_photo_model
```

```bash
# Linux/macOS:
.venv/bin/python backend/manage.py prepare_photo_model
```

Команда скачивает и проверяет u2netp. Без весов используется OpenCV с явными
предупреждениями. Модель распознавания категории одежды отдельно не установлена:
категорию можно выбрать вручную. [Подробности обработки фото](stage-3.md).

Open-Meteo требует доступа к api.open-meteo.com и geocoding-api.open-meteo.com.
На обычном компьютере ограничений облачной среды может не быть; фактический доступ
проверяйте запросом погоды из сайта. При сбое доступен подбор без погоды либо
ручная температура. Локальная Ollama необязательна: без неё работает резервный
стилист. [Настройка погоды и Ollama](stage-5.md).

## Проверки

Из корня в Windows:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py test backend/wardrobe
```

Из корня в Linux/macOS:

```bash
.venv/bin/python backend/manage.py check
.venv/bin/python backend/manage.py test backend/wardrobe
```

Для проверки frontend из его папки: `npm run typecheck`, `npm run build`.
Настройка браузерных тестов и Chromium: [frontend/README.md](../frontend/README.md).
