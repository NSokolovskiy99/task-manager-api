# 📝 Task Manager API

Асинхронное REST API для управления задачами и пользователями на **FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL**.

Проект демонстрирует чистую слоистую архитектуру (роуты → репозитории → модели), Pydantic-валидацию v2, Alembic-миграции, Docker-развёртывание и полное покрытие тестами (unit + integration, 99% coverage).

---

## ✨ Возможности

- **Пользователи**: создание, список с пагинацией, фильтр по наличию выполненных/невыполненных задач, просмотр пользователя со списком его задач, полное/частичное обновление, удаление.
- **Задачи**: CRUD, пагинация, фильтры по статусу выполнения и исполнителю, список задач без исполнителя (`/tasks/unassigned`).
- **Целостность данных**:
  - `ON DELETE SET NULL` — при удалении пользователя его задачи сохраняются и становятся «без исполнителя»;
  - CheckConstraint `priority BETWEEN 1 AND 5`;
  - уникальный `email` у пользователей;
  - проверка существования исполнителя перед назначением.
- **Обработка ошибок**: HTTP-статусы 400/404/409/422/500 с человекочитаемыми сообщениями, централизованный декоратор `@db_transaction` (откат транзакции + логирование).
- **Swagger UI** из коробки, тесты с in-memory SQLite, Docker Compose для быстрого старта.

---

## 🛠 Стек

| Слой | Технологии |
|---|---|
| Язык | Python 3.11+ (в контейнере — 3.11-slim) |
| Web | FastAPI 0.136, Uvicorn |
| ORM | SQLAlchemy 2.0 (async), aiosqlite / psycopg |
| Валидация | Pydantic v2 (EmailStr, Field, extra="forbid") |
| Миграции | Alembic |
| Тесты | pytest, pytest-asyncio, pytest-cov, httpx (ASGITransport) |
| Инфраструктура | Docker Compose, PostgreSQL |

---

## 📁 Структура проекта

```
├── alembic/                # Миграции БД
│   └── versions/
├── core/
│   └── config.py           # Настройки (pydantic-settings, .env)
├── models/                 # SQLAlchemy-модели (UserModel, TaskModel)
├── routers/                # Эндпоинты (tasks.py, users.py)
├── schemas/                # Pydantic-схемы запросов/ответов
├── services/               # Репозитории (вся работа с БД)
├── utils/
│   └── db_decorators.py    # @db_transaction: откат + логирование + статусы
├── tests/
│   ├── unit/               # Юнит-тесты (mock-сессия)
│   └── integration/        # Интеграционные тесты (in-memory SQLite)
├── database.py             # Engine, сессии, базовый класс Model
├── main.py                 # Точка входа FastAPI
├── docker-compose.yml
└── requirements.txt
```

---

## 🚀 Быстрый старт

```bash
docker compose --profile docker-db up -d --build
```

---

## Остановка и удаление контейнера

```bash
docker compose --profile docker-db down
```

---

## 🔌 API

Swagger UI: `http://localhost:8000/docs` • ReDoc: `http://localhost:8000/redoc`

### Health

| Метод | Путь | Описание |
|---|---|---|
| GET | `/health` | Статус сервиса |

### Пользователи

| Метод | Путь | Описание | Статусы |
|---|---|---|---|
| POST | `/users/` | Создать пользователя | 201, 400 (email занят), 422 |
| GET | `/users/` | Список; `skip`, `limit`, `has_completed_tasks` | 200 |
| GET | `/users/{user_id}` | Пользователь по ID | 200, 404 |
| GET | `/users/{user_id}/tasks` | Пользователь со списком задач | 200, 404 |
| PUT | `/users/{user_id}` | Полное обновление | 200, 404 |
| PATCH | `/users/{user_id}` | Частичное обновление | 200, 404, 422 |
| DELETE | `/users/{user_id}` | Удалить (задачи остаются, `user_id = null`) | 204, 404 |

### Задачи

| Метод | Путь | Описание | Статусы |
|---|---|---|---|
| POST | `/tasks/` | Создать задачу | 201, 404 (нет исполнителя), 422 |
| GET | `/tasks/` | Список; `skip`, `limit`, `is_completed`, `user_id` | 200 |
| GET | `/tasks/unassigned` | Задачи без исполнителя | 200 |
| GET | `/tasks/{task_id}` | Задача по ID | 200, 404 |
| PUT | `/tasks/{task_id}` | Полное обновление | 200, 404 |
| PATCH | `/tasks/{task_id}` | Частичное обновление | 200, 404, 422 |
| DELETE | `/tasks/{task_id}` | Удалить задачу | 204, 404 |

### Примеры запросов

```bash
# Создать пользователя
curl -X POST http://localhost:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Иван Петров", "email": "ivan@example.com"}'

# Создать задачу с исполнителем (user_id из ответа выше)
curl -X POST http://localhost:8000/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Купить молоко", "priority": 3, "user_id": 1}'

# Задачи без исполнителя
curl http://localhost:8000/tasks/unassigned

# Пользователь со списком его задач
curl http://localhost:8000/users/1/tasks

# Фильтр: пользователи с выполненными задачами
curl "http://localhost:8000/users/?has_completed_tasks=true"
```

---

## 🧪 Тесты

```bash
# Все тесты (unit + integration)

pytest tests -v
```

---

## 🗄 Миграции

```bash
# Создать новую миграцию по изменениям моделей
alembic revision --autogenerate -m "описание"

# Применить / откатить
alembic upgrade head
alembic downgrade -1

# Проверить синхронизацию схемы БД с моделями
alembic check
```

---

## 🗺 Дорожная карта (идеи для развития)

- Аутентификация и авторизация (JWT/OAuth2)
- CI/CD (GitHub Actions) с прогоном тестов и линтеров
- Structured logging и метрики (Prometheus)
