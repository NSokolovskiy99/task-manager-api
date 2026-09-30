import logging
import time
from functools import wraps
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def db_transaction(method):
    """
    Логирование, замеряет скорость и превращает
    технические ошибки БД в красивые HTTP-статусы для фронтенда
    """
    @wraps(method) # Сохраняет оригинальное имя функции (__name__) и документацию (__doc__). Без неё FastAPI перестал бы понимать, какие роуты за что отвечают
    async def wrapper(*args, **kwargs):
        session = kwargs.get("session")   # Ищем session в kwargs (надёжнее, чем в args)
        if not session or not isinstance(session, AsyncSession):
            raise RuntimeError(
                f"Метод '{method.__name__}' требует передачи 'session' в качестве именованного аргумента"
            )

        start = time.perf_counter() # Фиксируем время(высокоточный таймер)
        try:
            result = await method(*args, **kwargs) # Вызываем метод
            duration_ms = (time.perf_counter() - start) * 1000 # Итог времени выполнения(мсек)
            logger.info("✅ %s успешно выполнен за %.2f ms", method.__name__, duration_ms)
            return result
        except IntegrityError as e: # Ошибка (уникальность, внешние ключи)
            await session.rollback()

            logger.warning(
                "🛑 Ошибка целостности %s: %s",
                method.__name__,
                e,
                exc_info=True,     # Прикрепит к этому сообщению весь стек вызовов (Traceback) 
            )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нарушение ограничений базы данных (например, такое имя или email уже существует).",
            ) from e               # Cохраняет связь с {e}, показывая, какая именно ошибка БД вызвала этот HTTP-ответ
        except SQLAlchemyError as e:
            await session.rollback()

            logger.error(
                "🛑 Ошибка базы данных в %s: %s",
                method.__name__,
                e,
                exc_info=True,
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Сбой при работе с базой данных",
            ) from e
        except HTTPException:         # Откатываем сессию (чтобы очистить «грязные» объекты),
            await session.rollback()  # а затем пробрасываем ручную ошибку добавленную в методах
            raise                                    
        except Exception as e:
            await session.rollback()
            logger.critical(
                "💥 Непредвиденная ошибка в %s: %s",
                method.__name__,
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера. Пожалуйста, попробуйте позже.",
            ) from e

    return wrapper