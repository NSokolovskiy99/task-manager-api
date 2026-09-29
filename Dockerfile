# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей (кэшируется)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Параметры подключения к БД передаются через docker-compose (environment),
# а для локального запуска — через .env (см. core/config.py).

# Healthcheck (опционально, но полезно)
# HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
#   CMD ["curl", "-f", "http://localhost:8000/health"] || exit 1


# Запуск с --reload для разработки
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
