import logging
import time
from functools import wraps
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def db_transaction(method):
    @wraps(method)
    async def wrapper(*args, **kwargs):
        # Ищем session в kwargs (надёжнее, чем в args)
        session = kwargs.get("session")
        if not session or not isinstance(session, AsyncSession):
            raise RuntimeError(
                f"Method '{method.__name__}' requires 'session' as a keyword argument"
            )

        start = time.perf_counter()
        try:
            result = await method(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info("✅ %s completed in %.2f ms", method.__name__, duration_ms)
            return result
        except IntegrityError as e:
            await session.rollback()

            logger.warning(
                "🛑 Integrity error in %s: %s",
                method.__name__,
                e,
                exc_info=True,
            )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Constraint violation (e.g., duplicate name)",
            ) from e
        except SQLAlchemyError as e:
            await session.rollback()

            logger.error(
                "🛑 DB error in %s: %s",
                method.__name__,
                e,
                exc_info=True,
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database failure",
            ) from e
        except HTTPException:
            # Пробрасываем HTTPException без изменений (чтобы 404 оставался 404)
            raise
        except Exception as e:
            await session.rollback()
            logger.critical(
                "💥 Unexpected error in %s: %s",
                method.__name__,
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e

    return wrapper