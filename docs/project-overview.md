# Task Manager API — обзор проекта

## Стек технологий

- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0 (async)** — ORM для работы с БД
- **Pydantic v2** — валидация входящих/исходящих данных
- **Uvicorn** — ASGI-сервер для запуска
- **pydantic-settings** — конфигурация через `.env`
- **PostgreSQL + asyncpg** — продакшен-БД
- **SQLite + aiosqlite** — БД для разработки и тестов
- **Alembic** — миграции схемы БД
- **Docker Compose** — оркестрация API + PostgreSQL

---

## 1. Конфигурация — `core/config.py`

```python
class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "task_manager"
    SQLITE_URL: str = "sqlite+aiosqlite:///tasks.db"
    DATABASE_MODE: str = "sqlite"  # "postgres" или "sqlite"
```

- Настройки читаются из `.env` файла
- `DATABASE_MODE` переключает между PostgreSQL и SQLite
- Глобальный объект `settings = Settings()` импортируется в `database.py`

---

## 2. Точка входа — `main.py`

```python
app = FastAPI(lifespan=lifespan)
app.include_router(tasks.router)
```

**При старте сервера:**
1. Срабатывает `lifespan` — логирует запуск
2. Таблицы создаются через **Alembic миграции**, а не через `create_all`
3. Становится доступен endpoint `/health` — проверка что сервер жив
4. Подключается роутер задач по префиксу `/tasks`

**Команда запуска:** `uvicorn main:app --reload`

---

## 3. База данных — `database.py`

```python
if settings.DATABASE_MODE == "postgres":
    DATABASE_URL = settings.DATABASE_URL      # postgresql+asyncpg://...
else:
    DATABASE_URL = settings.SQLITE_URL        # sqlite+aiosqlite:///tasks.db
```

- **Engine** — `create_async_engine(DATABASE_URL)` — выбирает БД по режиму
- **Session factory** — `async_sessionmaker(engine)` — создаёт сессии
- **`get_db()`** — FastAPI-зависимость: открывает сессию на каждый HTTP-запрос
- **`SessionDep`** — тип `Annotated[AsyncSession, Depends(get_db)]`

---

## 4. Модель БД — `models/tasks.py`

```python
class TaskModel(Model):
    __tablename__ = "tasks"

    id: Mapped[int]              # первичный ключ, автоинкремент
    name: Mapped[str]            # название задачи (обязательное)
    description: Mapped[str | None]  # описание (может быть None)
    is_completed: Mapped[bool]   # статус (default=False)
```

Таблица `tasks` с 4 колонками.

---

## 5. Схемы валидации — `schemas/task.py`

Три Pydantic-схемы:

| Схема | Назначение | Особенности |
|-------|-----------|-------------|
| `STaskAdd` | Создание задачи (POST) | `name` от 3 до 100 символов, `description` макс 500, `is_completed` по умолч. `False` |
| `STask` | Ответ API (GET, PUT, PATCH) | `from_attributes=True` — умеет создаваться из ORM-объекта |
| `STaskPatch` | Частичное обновление (PATCH) | Все поля опциональны, `extra="forbid"` — лишние поля запрещены |

---

## 6. API endpoints — `routers/tasks.py`

| Метод | URL | Что делает | Статус ответа |
|-------|-----|-----------|--------------|
| `POST` | `/tasks/` | Создаёт задачу | `201 Created` |
| `GET` | `/tasks/` | Список задач (пагинация + фильтр по статусу) | `200 OK` |
| `GET` | `/tasks/{id}` | Одна задача по ID | `200 OK` / `404` |
| `PUT` | `/tasks/{id}` | Полное обновление задачи | `200 OK` / `404` |
| `PATCH` | `/tasks/{id}` | Частичное обновление задачи | `200 OK` / `404` |
| `DELETE` | `/tasks/{id}` | Удаление задачи | `204 No Content` / `404` |

Каждый endpoint получает `session: SessionDep` и вызывает соответствующий метод `TaskRepository`.

---

## 7. Бизнес-логика — `services/tasks_repository.py`

Класс `TaskRepository` с 6 методами:

| Метод | `@db_transaction` | Что делает |
|-------|-------------------|-----------|
| `add_one` | ✅ | Создаёт `TaskModel`, копирует поля из схемы, `add` → `commit` → `refresh` |
| `find_all` | ❌ | `SELECT` с `OFFSET`/`LIMIT` и опциональным фильтром по `is_completed` |
| `find_one_or_404` | ❌ | `SELECT` по ID → если не найдено, `HTTPException(404)` |
| `update_full` | ✅ | Находит задачу → перезаписывает все поля → `commit` → `refresh` |
| `patch` | ✅ | Находит задачу → обновляет только переданные поля → `commit` → `refresh` |
| `delete` | ✅ | Находит задачу → `delete` → `commit` |

---

## 8. Декоратор транзакций — `utils/db_decorators.py`

```python
@db_transaction
```

Оборачивает методы, которые изменяют БД. Делает:
1. **Проверяет** что `session` передан в kwargs
2. **Замеряет** время выполнения метода
3. **Обрабатывает ошибки:**
   - `IntegrityError` → `409 Conflict`
   - `SQLAlchemyError` → `500 Internal Server Error`
   - `HTTPException` → пробрасывает без изменений (404 остаётся 404)
   - Любая другая ошибка → `500 Internal Server Error`
4. Делает `rollback()` при ошибках БД

---

## 9. Миграции — Alembic

- Конфигурация: `alembic.ini` (SQLite для разработки)
- `alembic/env.py` — подключены модели `TaskModel` и `Model.metadata`
- Первая миграция: `alembic/versions/83297d3a5db8_init.py`
- Скрипт управления: `scripts/migrate.bat`

```bash
scripts\migrate.bat new       # создать миграцию
scripts\migrate.bat up        # применить
scripts\migrate.bat down      # откатить
```

---

## 10. Docker Compose

```yaml
services:
  db:       # postgres:16-alpine
  api:      # FastAPI + uvicorn
```

- `db` — PostgreSQL 16 с healthcheck, volume `pgdata`
- `api` — зависит от `db` (ждёт `service_healthy`)
- Переменные окружения `DATABASE_MODE=postgres`, `DB_HOST=db` и т.д.

---

## Визуальная схема запроса

```
Клиент (curl/браузер)
    │
    ▼
FastAPI (main.py)
    │
    ├── /health ──→ {"status": "ok"}
    │
    └── /tasks/* ──→ routers/tasks.py
                        │
                        ├── Получает session через SessionDep
                        │   (database.py открывает сессию)
                        │
                        └── Вызывает TaskRepository.method()
                                │
                                ├── @db_transaction (если есть)
                                │   └── проверка session → try/except/rollback
                                │
                                └── SQLAlchemy запрос
                                        │
                                        ├── SQLite (разработка) → tasks.db
                                        └── PostgreSQL (продакшен) → db:5432
```

---

## Как запустить

```bash
# Разработка (SQLite)
pip install -r requirements.txt
uvicorn main:app --reload

# Продакшен (PostgreSQL через Docker)
docker-compose up --build
docker-compose exec api alembic upgrade head

# Документация: http://localhost:8000/docs