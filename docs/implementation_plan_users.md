# План внедрения схемы User и связи User → Task (1:N)

> Статус: план согласован, реализация ещё не начата.
> Проект: Task Manager API (FastAPI + async SQLAlchemy 2.0 + Alembic).
> Цель: добавить сущность `User`, связать её с задачами отношением «один пользователь — много задач», добавить CRUD-эндпоинты `/users`, расширить задачи, покрыть изменения тестами.

---

## Общая схема изменений

```
Клиент
  │
  ▼
main.py ── include_router ──► routers/users.py (новый)
  │                        └─► routers/tasks.py (расширить)
  ▼
services/
  ├── users_repository.py   (НОВЫЙ: UserRepository)
  └── tasks_repository.py   (РАСШИРИТЬ: фильтр user_id, проверка существования)
  ▼
models/
  ├── users.py              (НОВЫЙ: UserModel)
  └── tasks.py              (РАСШИРИТЬ: user_id, relationship user)
  ▼
schemas/
  ├── user.py               (НОВЫЙ: SUserAdd, SUser, SUserPatch)
  └── task.py               (РАСШИРИТЬ: user_id)
  ▼
Alembic: новая миграция (users + user_id в tasks)
```

---

## Шаг 1. Модель `UserModel` — файл `models/users.py` (новый)

```python
class UserModel(Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    tasks: Mapped[list["TaskModel"]] = relationship(back_populates="user")
```

Ключевые решения:
- `email` — **уникальный** (`unique=True`): дубликат даст `IntegrityError`, который [`db_transaction`](utils/db_decorators.py) уже превращает в `409 Conflict`.
- `relationship` на стороне «один» — коллекция `tasks` (однострочный `back_populates`).
- Тип `Mapped[list["TaskModel"]]` требует `from __future__ import annotations` (как в существующих моделях).

Критерий готовности: модуль импортируется без ошибок; таблица `users` попадает в `Model.metadata`.

---

## Шаг 2. Расширение `TaskModel` — файл `models/tasks.py`

Добавить:

```python
user_id: Mapped[int | None] = mapped_column(
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
user: Mapped["UserModel | None"] = relationship(back_populates="tasks")
```

Ключевые решения:
- `user_id` **nullable=True** — задача может существовать без исполнителя.
- `ondelete="SET NULL"` — удаление пользователя не удаляет его задачи, они становятся «бесхозными» (задачи `user_id` → NULL). Альтернативы для обсуждения: `CASCADE` (удалить и задачи), `RESTRICT` (нельзя удалить, если есть задачи).
- `index=True` — фильтрация `WHERE user_id = ?` пойдёт по индексу.
- **Не добавлять** `cascade="all, delete-orphan"` на сторону User → tasks, чтобы не было каскадного удаления.

Критерий готовности: связь двусторонняя; создание задачи с `user_id` и без него работает.

---

## Шаг 3. Alembic — регистрация модели и миграция

1. В `alembic/env.py` добавить импорт новой модели (для автогенерации):
   ```python
   from models.users import UserModel  # noqa: F401
   ```
2. Сгенерировать миграцию:
   ```
   python -m alembic revision --autogenerate -m "add users table and assignee relation"
   ```
3. Проверить сгенерированный файл вручную:
   - создание таблицы `users` (id, name, email, unique-constraint на email)
   - `add_column`/`batch_alter_table` для `tasks.assignee_id` с FK и `ondelete="SET NULL"`
   - корректный `downgrade` (обратный порядок: drop FK/колонку, потом таблицу)
4. Применить: `python -m alembic upgrade head` (PostgreSQL должен быть запущен).

Критерий готовности: `python -m alembic history` показывает новую ревизию; `upgrade head` применяется без ошибок.

---

## Шаг 4. Pydantic-схемы пользователей — файл `schemas/user.py` (новый)

По образцу `schemas/task.py` — три схемы:

| Схема | Назначение | Особенности |
|---|---|---|
| `SUserAdd` | POST /users/ | `name`: 3–100 символов; `email`: `EmailStr` (валидация формата) |
| `SUser` | Ответ API | `from_attributes=True`; поля `id`, `name`, `email` |
| `SUserPatch` | PATCH /users/{id} | все поля опциональны, `extra="forbid"` |

Примечание: `EmailStr` требует пакет `email-validator` — добавить в `requirements.txt`.

Критерий готовности: схемы валидируют входные данные (короткое имя, неверный email → 422).

---

## Шаг 5. Обновление схем задач — файл `schemas/task.py`

- В `STaskAdd` и `STaskPatch` добавить поле `user_id: int | None = None`.
- В `STask` добавить `user_id: int | None`.

Примечание: вложенный объект `user` в ответе задач НЕ добавляем на этом этапе — это пункт про N+1 (см. Шаг 10).

Критерий готовности: POST /tasks/ принимает `user_id`; ответ содержит `user_id`.

---

## Шаг 6. Новый репозиторий — файл `services/users_repository.py`

Класс `UserRepository` в стиле `TaskRepository` (classmethod-методы, `@db_transaction` на мутирующих операциях):

| Метод | `@db_transaction` | Поведение |
|---|---|---|
| `add_one(data: SUserAdd, session)` | ✅ | создать, `commit`, `refresh`, вернуть модель |
| `find_all(session, skip, limit)` | ❌ | список с пагинацией |
| `find_one_or_404(user_id, session)` | ❌ | по ID или `HTTPException(404)` |
| `patch(user_id, data: SUserPatch, session)` | ✅ | обновить только переданные поля (`model_dump(exclude_unset=True)`) |
| `delete(user_id, session)` | ✅ | удалить; задачи остаются (ORM сам обнулит `user_id`, т.к. FK `SET NULL`) |

Экспорт в `services/__init__.py`: `from .users_repository import UserRepository`, добавить в `__all__`.

Критерий готовности: методы повторяют поведение `TaskRepository` и проходят юнит-тесты на mock-сессии.

---

## Шаг 7. Расширение `TaskRepository` — файл `services/tasks_repository.py`

Не переписывать! Добавить:

1. `find_all`: параметр `user_id: int | None = None` → условный `query.where(TaskModel.user_id == user_id)`.
2. `add_one` / `update_full` / `patch`: если передан `user_id` — проверить, что пользователь существует (запрос к `UserModel`), иначе `HTTPException(404, "User with id ... not found")`.
3. Не менять сигнатуры существующих вызовов (параметры с дефолтами).

Критерий готовности: старые тесты `test_repository.py` проходят без изменений ожиданий; новые ветки покрыты тестами.

---

## Шаг 8. Роутер пользователей — файл `routers/users.py` (новый)

`router = APIRouter(prefix="/users", tags=["Пользователи"])`

| Метод | URL | Описание | Статус |
|---|---|---|---|
| POST | `/users/` | создать пользователя | 201 / 409 (дубль email) / 422 |
| GET | `/users/` | список (пагинация skip/limit) | 200 |
| GET | `/users/{user_id}` | один пользователь | 200 / 404 |
| GET | `/users/{user_id}/tasks` | задачи пользователя (связь 1:N) | 200 / 404 |
| PATCH | `/users/{user_id}` | частичное обновление | 200 / 404 / 409 |
| DELETE | `/users/{user_id}` | удаление (задачи остаются) | 204 / 404 |

Подключить в `main.py`: `app.include_router(users.router)`.

Критерий готовности: все эндпоинты отвечают корректными статусами; в Swagger видны `/users*`.

---

## Шаг 9. Обновление роутера задач — файл `routers/tasks.py`

- Добавить query-параметр: `user_id: int | None = Query(None)` в `GET /tasks/` → передать в `find_all`.

Критерий готовности: `GET /tasks/?user_id=1` возвращает только задачи пользователя 1.

---

## Шаг 10. [ПОСЛЕДНИЙ ПУНКТ] Тесты — новые и обновлённые

> Важно: в проекте настроен порог покрытия 100% — без дополнения тестов `pytest` начнёт падать.

### Новые файлы

1. `tests/unit/test_users_repository.py` — юнит-тесты `UserRepository` на mock-сессии (паттерн из `test_repository.py`):
   - `add_one` успех, дефолты, дубликат email → `IntegrityError` → 409
   - `find_all` пагинация
   - `find_one_or_404` найден / 404
   - `patch` только переданные поля
   - `delete` вызов `session.delete` + `commit`

2. `tests/integration/test_api_users.py` — API-тесты на in-memory SQLite:
   - CRUD `/users` (201, 200, 404, 204)
   - валидация: короткое имя, неверный email → 422
   - дубликат email → 409
   - `GET /users/{id}/tasks`: пользователь с 2 задачами → 2; без задач → `[]`; несуществующий → 404

### Обновление существующих

3. `tests/integration/test_api_tasks.py`:
   - создание задачи с `user_id` и без
   - `GET /tasks/?user_id=` фильтрация
   - `POST /tasks/` с несуществующим `user_id` → 404
   - ответ содержит `user_id`
   - удаление пользователя → его задачи получают `user_id=None` (SET NULL)

4. `tests/unit/test_repository.py`:
   - `find_all` с `user_id` → в запросе есть `WHERE user_id`
   - `add_one` с несуществующим `user_id` → 404 (mock для проверки существования)

Критерий готовности: `pytest -q` — все тесты зелёные, покрытие 100%.

---

## Шаг 11. [ПОСЛЕДНИЙ ПУНКТ] Документация — файл `docs/project-overview.md`

- Добавить описание моделей `users` и `tasks` (таблица с колонками, связь 1:N)
- Добавить таблицу эндпоинтов `/users`
- Добавить ER-схему (Mermaid) User → Task
- Обновить раздел про слои (`services`)

---

## Шаг 12. [ПОСЛЕДНИЙ ПУНКТ] Финальная проверка

```
python -m alembic history          # новая ревизия на месте
python -m alembic upgrade head     # применяется к PostgreSQL
python -m pytest -q                # все зелёные, 100%
uvicorn main:app --reload          # smoke-тест: /docs, POST /users, POST /tasks с user_id
```

---

## Шаг 13. [ОТДЕЛЬНЫЙ ПОСЛЕДНИЙ ПУНКТ] Проблема N+1 и selectinload

> Отложено: сначала разобраться в теме. Этот шаг выполняется после базовой реализации.

**Что такое N+1:** при `GET /tasks/` ответ для каждой задачи содержит вложенный объект `user`. Без явной загрузки ORM сделает 1 запрос на список задач + 1 запрос на каждого пользователя = N+1 запросов.

**Решение:** в `find_all`/`find_one_or_404` добавить eager-загрузку:

```python
from sqlalchemy.orm import selectinload

query = select(TaskModel).options(selectinload(TaskModel.user))
```

ORM выполнит 2 запроса суммарно (список задач + пакетная загрузка всех связанных пользователей через `IN (...)`), вместо N+1.

**Для этого шага также понадобятся:**
- вложенный `user: SUser | None` в схеме `STask`
- тест: проверка, что запрос содержит `.options(selectinload(...))`

---

## Порядок выполнения (итог)

1. Модель `UserModel` → 2. Расширение `TaskModel` → 3. Alembic (импорт + миграция) → 4. Схемы пользователей → 5. Схемы задач → 6. `UserRepository` → 7. Расширение `TaskRepository` → 8. Роутер `/users` → 9. Роутер `/tasks` → 10. Тесты → 11. Документация → 12. Проверка → 13. N+1 (после разбора темы).