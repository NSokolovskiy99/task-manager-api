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

### Вариант 1: Docker Compose (рекомендуется)

Требуется запущенный PostgreSQL на хосте (или в отдельном контейнере).

```bash
# 1. Создать БД (один раз)
# CREATE DATABASE task_manager;

# 2. Поднять API
docker compose up -d --build

# 3. Применить миграции
docker compose exec api python -m alembic upgrade head
```

Приложение будет доступно на **http://localhost:8000**.

### Вариант 2: Локально (venv)

```bash
python -m venv venv
venv\Scripts\activate              # Windows
# source venv/bin/activate         # Linux/macOS

pip install -r requirements.txt

copy .env.example .env             # и при необходимости поправь настройки БД
# cp .env.example .env             # Linux/macOS

venv\Scripts\python.exe -m alembic upgrade head
uvicorn main:app --reload
```

### Конфигурация (.env)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_MODE` | `sqlite` | `sqlite` или `postgres` |
| `DB_HOST` | `localhost` | Хост PostgreSQL |
| `DB_PORT` | `5432` | Порт |
| `DB_USER` | `postgres` | Пользователь |
| `DB_PASSWORD` | — | Пароль |
| `DB_NAME` | `task_manager` | Имя БД |

> ⚠️ `.env` с реальными значениями не коммитится в git. Для репозитория предназначен шаблон [`.env.example`](.env.example).

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
venv\Scripts\python.exe -m pytest

# Только unit / только integration
venv\Scripts\python.exe -m pytest -m "unit"
venv\Scripts\python.exe -m pytest -m "integration"
```

- **144 теста** (89 unit + 55 integration), покрытие **99%**.
- Интеграционные тесты используют in-memory SQLite и переопределяют зависимость `get_db`.
- Подробнее: [tests/TEST_COMMANDS.md](tests/TEST_COMMANDS.md).

---

## 🗄 Миграции

```bash
# Создать новую миграцию по изменениям моделей
venv\Scripts\python.exe -m alembic revision --autogenerate -m "описание"

# Применить / откатить
venv\Scripts\python.exe -m alembic upgrade head
venv\Scripts\python.exe -m alembic downgrade -1

# Проверить синхронизацию схемы БД с моделями
venv\Scripts\python.exe -m alembic check
```

---

## 🗺 Дорожная карта (идеи для развития)

- Аутентификация и авторизация (JWT/OAuth2)
- Soft-delete и аудит изменений
- Фильтры по приоритету/датам, сортировки
- Пагинация через курсоры
- CI/CD (GitHub Actions) с прогоном тестов и линтеров
- Structured logging и метрики (Prometheus)