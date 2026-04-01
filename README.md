# Профильное задание для стажировки в VK

Тестовое задание: асинхронный FastAPI-сервис для безопасной выдачи тестовых пользователей в E2E-прогонах с TTL-блокировкой, JWT-авторизацией, PostgreSQL и интеграционными тестами конкурентного доступа.

## Что реализовано

- Создание пользователя ботофермы с валидацией входных данных.
- Получение списка пользователей.
- Выдача первого доступного пользователя через locktime.
- Снятие всех блокировок через free_users.
- JWT-защита пользовательских endpoint'ов.
- Конкурентно-безопасная блокировка на PostgreSQL через FOR UPDATE SKIP LOCKED.
- Health, liveness, startup и readiness пробы.
- Миграции Alembic и контейнеризация через Docker Compose.

## Технологический стек

- Python 3.12+
- FastAPI + Uvicorn
- SQLAlchemy 2 (AsyncSession)
- asyncpg
- PostgreSQL 14
- Pydantic v2
- Alembic
- JWT (PyJWT) для защиты API
- pytest + pytest-asyncio + pytest-cov
- Docker + Docker Compose

## Быстрая проверка за 2 минуты

1. Поднять сервис:

```bash
docker compose up --build
```

2. Получить JWT:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/token \
	-H "Content-Type: application/json" \
	-d '{"username":"admin","password":"admin"}'
```

3. Создать пользователя:

```bash
curl -X POST http://localhost:8000/api/v1/users \
	-H "Authorization: Bearer <TOKEN>" \
	-H "Content-Type: application/json" \
	-d '{
		"login": "user@example.com",
		"password": "secret",
		"project_id": "8d9c2150-cf88-4b7a-9f4d-f2dd9e7f36f3",
		"env": "stage",
		"domain": "regular"
	}'
```

4. Заблокировать и выдать пользователя для теста:

```bash
curl -X POST http://localhost:8000/api/v1/users/lock \
	-H "Authorization: Bearer <TOKEN>"
```

## API

| Method | Path | Auth | Назначение |
|---|---|---|---|
| POST | /api/v1/auth/token | Нет | Получить JWT-токен |
| POST | /api/v1/users | Bearer JWT | Создать пользователя |
| GET | /api/v1/users | Bearer JWT | Получить список пользователей |
| POST | /api/v1/users/lock | Bearer JWT | Выдать первого свободного пользователя и установить locktime |
| POST | /api/v1/users/free | Bearer JWT | Снять блокировки со всех пользователей |
| GET | /health | Нет | Базовая проверка API |
| GET | /health/liveness | Нет | Проверка жизнеспособности процесса |
| GET | /health/startup | Нет | Проверка завершения старта приложения |
| GET | /health/readiness | Нет | Проверка готовности БД |

## Архитектура

Проект разделен на слои:
- API слой: роуты и HTTP-контракты.
- Service слой: бизнес-логика и работа с блокировками.
- DB слой: подключение к базе и DI сессий.
- Schemas: входные и выходные Pydantic-схемы.
- Models: ORM-модели SQLAlchemy.

Особенности реализации:
- Асинхронные эндпоинты и асинхронный доступ к БД.
- DI сессии через get_db.
- Пароль хранится в виде хэша bcrypt.
- JWT для доступа к пользовательским эндпоинтам.
- Пробы health/liveness/startup/readiness.
- Миграции Alembic применяются при старте контейнера приложения.

## Архитектура сервиса

![docs/architecture.png](docs/architecture.png)

## Инженерные решения

### Почему locktime + TTL

Для E2E-платформы важно, чтобы выданный пользователь не доставался параллельно другому тесту. TTL на locktime решает это без отдельного воркера очистки: после истечения времени пользователь автоматически становится доступным.

### Почему сервисный слой

Бизнес-логика вынесена из роутов в services, чтобы:
- изолировать HTTP-слой от доменной логики,
- упростить unit/integration тесты,
- централизовать правила выдачи пользователей.

### Почему FOR UPDATE SKIP LOCKED

На PostgreSQL конкурентная выдача пользователей выполняется безопасно: параллельные транзакции не берут одну и ту же запись. Это важный механизм для реального E2E-нагрузочного сценария.

## Логика блокировки

Алгоритм lock_user:
1. Берется текущее UTC-время.
2. Считается lock_until = now + USER_LOCK_TTL_SECONDS.
3. Ищется первый пользователь по created_at, у кого locktime is null или locktime <= now.
4. Для PostgreSQL используется FOR UPDATE SKIP LOCKED для корректной конкуренции.
5. У пользователя обновляется locktime.
6. Пользователь возвращается в ответ.

Если свободного пользователя нет, возвращается 404 no available users.

## Структура проекта

```text
app/
	api/        # REST-роуты и health-пробы
	db/         # engine/session и DI
	models/     # ORM-модели
	schemas/    # Pydantic-схемы запросов/ответов
	services/   # бизнес-логика
alembic/      # миграции
tests/        # unit/integration тесты
```

Дополнительно для PostgreSQL интеграционного теста конкурентного lock_user:
- TEST_POSTGRES_DB_URL

## Запуск через Docker Compose

```bash
docker compose up --build
```

Что происходит при старте app-контейнера:
1. Применяются миграции Alembic.
2. Поднимается Uvicorn с FastAPI.

Сервис будет доступен на порту 8000.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Тесты

Базовый прогон:

```bash
pytest -q
```

С покрытием:

```bash
pytest --cov=app --cov-report=term-missing
```

В проекте настроен порог покрытия 75% (fail_under).

PostgreSQL интеграционный тест конкурентного lock_user:

```bash
TEST_POSTGRES_DB_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/botfarm pytest tests/test_lock_postgres.py -q
```

## Заключение
Реализованный сервис соответствует требованиям задания, обеспечивает безопасную выдачу пользователей с TTL-блокировкой, JWT-защитой и поддерживает конкурентный доступ через PostgreSQL. Код структурирован и покрыт тестами, а также готов к развертыванию через Docker Compose.


# Контактные данные
- Telegram: [@blancfort](https://t.me/blancfort)
- Email: blancfort300@gmail.com