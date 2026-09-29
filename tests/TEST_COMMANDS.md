# 🧪 Команды для запуска тестов

> Файл будет дополняться по мере добавления новых фаз тестирования.

---

## 📦 Базовые команды

```powershell
# Все команды выполняются при активном venv (в промпте видно "(venv)")
# Запустить ВСЕ тесты (unit + integration)
python -m pytest

# Запустить только unit-тесты
python -m pytest -m "unit"

# Запустить только integration-тесты
python -m pytest -m "integration"
```

---

## 📊 Coverage (покрытие кода)

```bash
# Coverage в терминале (пропущенные строки)
.\venv\Scripts\python.exe -m pytest --cov=services --cov=routers --cov=utils --cov=schemas --cov=models --cov-report=term-missing

# Coverage с HTML-отчётом (открыть htmlcov/index.html в браузере)
.\venv\Scripts\python.exe -m pytest --cov=services --cov=routers --cov=utils --cov=schemas --cov=models --cov-report=html

# Coverage только для unit-тестов
.\venv\Scripts\python.exe -m pytest -m "unit" --cov=services --cov=routers --cov=utils --cov=schemas --cov=models --cov-report=term-missing

# Coverage только для integration-тестов
.\venv\Scripts\python.exe -m pytest -m "integration" --cov=services --cov=routers --cov=utils --cov=schemas --cov=models --cov-report=term-missing
```

---

## 🎯 Фильтрация тестов

```bash
# По маркеру
.\venv\Scripts\python.exe -m pytest -m "unit"
.\venv\Scripts\python.exe -m pytest -m "integration"
.\venv\Scripts\python.exe -m pytest -m "smoke"
.\venv\Scripts\python.exe -m pytest -m "regression"

# По имени теста (ключевое слово)
.\venv\Scripts\python.exe -m pytest -k "add_one"
.\venv\Scripts\python.exe -m pytest -k "delete"
.\venv\Scripts\python.exe -m pytest -k "not_found or error"
.\venv\Scripts\python.exe -m pytest -k "patch"
.\venv\Scripts\python.exe -m pytest -k "create_task"

# По файлу
.\venv\Scripts\python.exe -m pytest tests/unit/test_schemas.py
.\venv\Scripts\python.exe -m pytest tests/unit/test_repository.py
.\venv\Scripts\python.exe -m pytest tests/unit/test_db_decorators.py
.\venv\Scripts\python.exe -m pytest tests/integration/test_api_health.py
.\venv\Scripts\python.exe -m pytest tests/integration/test_api_tasks.py
.\venv\Scripts\python.exe -m pytest tests/integration/test_api_errors.py

# По директории
.\venv\Scripts\python.exe -m pytest tests/unit/
.\venv\Scripts\python.exe -m pytest tests/integration/
```

---

## 🐛 Отладка

```bash
# Показать print() в тестах (не подавлять вывод)
.\venv\Scripts\python.exe -m pytest -s

# Остановиться на первой ошибке
.\venv\Scripts\python.exe -m pytest -x

# Подробный отчёт по каждой ошибке (-ra уже в pytest.ini)
.\venv\Scripts\python.exe -m pytest --tb=long

# Запустить конкретный тест
.\venv\Scripts\python.exe -m pytest tests/unit/test_repository.py::TestAddOne::test_add_one_success -v

# Запустить конкретный integration-тест
.\venv\Scripts\python.exe -m pytest tests/integration/test_api_tasks.py::TestCreateTask::test_create_task_success -v
```

---

## 🗄️ Миграции (Alembic)

> Миграции применяются к ЛОКАЛЬНОМУ PostgreSQL (сервер Sokol, база task_manager).
> Перед командами убедись, что PostgreSQL запущен.

```powershell
# Создать новую миграцию (автогенерация) — выполняется при активном venv
python -m alembic revision --autogenerate -m "описание"

# Применить все миграции
python -m alembic upgrade head

# Откатить последнюю миграцию
python -m alembic downgrade -1

# Показать историю миграций
python -m alembic history

# Текущая ревизия
python -m alembic current

# Проверить синхронизацию моделей и БД
python -m alembic check
```

---

## 🐳 Docker Compose

> В Docker поднимается ТОЛЬКО приложение (uvicorn).
> База данных — локальный PostgreSQL на хосте: контейнер обращается к нему
> через `host.docker.internal:5432` (см. docker-compose.yml, extra_hosts).

```bash
# Запустить API в Docker (БД остаётся локальной)
docker compose up --build

# Запустить в фоне
docker compose up -d --build

# Остановить и удалить контейнер
docker compose down

# Посмотреть логи API
docker compose logs -f api

# Пересобрать образ после изменения requirements.txt
docker compose build --no-cache api
```

---

## 📋 Текущий статус (Фаза 1 + Фаза 2)

| Файл | Тестов | Статус |
|------|--------|--------|
| `tests/unit/test_schemas.py` | 15 | ✅ Все проходят |
| `tests/unit/test_repository.py` | 19 | ✅ Все проходят |
| `tests/unit/test_db_decorators.py` | 6 | ✅ Все проходят |
| `tests/integration/test_api_health.py` | 1 | ✅ Все проходят |
| `tests/integration/test_api_tasks.py` | 20 | ✅ Все проходят |
| `tests/integration/test_api_errors.py` | 2 | ✅ Все проходят |
| **Всего** | **63** | **✅ 100% coverage** |

---

## 🚀 Быстрый старт (одна команда)

```powershell
# Самый частый сценарий — все тесты с coverage (при активном venv)
python -m pytest --cov=services --cov=routers --cov=utils --cov=schemas --cov=models --cov-report=term-missing