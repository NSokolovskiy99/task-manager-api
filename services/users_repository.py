from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from models.tasks import TaskModel
from models.users import UserModel
from schemas.user import SUserAdd, SUserPatch
import logging
from utils.db_decorators import db_transaction

logger = logging.getLogger(__name__)


class UserRepository:
    @classmethod
    @db_transaction
    async def add_one(cls, data: SUserAdd, session: AsyncSession) -> UserModel:
        logger.info("DEBUG: Получены данные пользователя = %s", data.model_dump())

        existing_user = await cls.find_by_email(data.email, session=session)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Пользователь с email '{data.email}' уже зарегистрирован в системе.",
            )

        
        user = UserModel(
            name=data.name,
            email=data.email,
            is_active=data.is_active,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        logger.info("SUCCESS: Пользователь создан с id=%s", user.id)
        return user

    @classmethod
    async def find_all(
        cls,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        has_completed_tasks: bool | None = None,
    ):
        """
        Получить список пользователей с пагинацией и фильтрацией по статусу их задач.
        
        :param session: Асинхронная сессия SQLAlchemy.
        :param skip: Количество пропускаемых записей (смещение).
        :param limit: Максимальное количество возвращаемых записей.
        :param has_completed_tasks: 
            - True: вернет пользователей, у которых есть хотя бы одна выполненная задача.
            - False: вернет пользователей, у которых есть хотя бы одна невыполненная задача.
            - None: вернет всех пользователей из базы данных без учета их задач.
        """

        # 1. Базовый запрос выборки пользователей
        query = select(UserModel)
        # 2. Если передан фильтр по статусу задач, делаем JOIN и фильтруем по TaskModel
        if has_completed_tasks is not None:
            query = query.join(UserModel.tasks).where(
                TaskModel.is_completed == has_completed_tasks
            )
            # Избегаем дублирования пользователей на уровне SQL, так как у одного юзера много задач
            query = query.distinct()

        # 3. Пагинация
        query = query.offset(skip).limit(limit)
        users = await session.execute(query)
        # 4. Возвращаем список уникальных объектов пользователей.
        # Метод .unique() обязателен в SQLAlchemy 2.0 при наличии JOIN/relationship,
        # иначе библиотека вернет дубли или выбросит ошибку.
        return users.scalars().unique().all()     

    @classmethod
    async def find_one_or_404(cls, user_id: int, session: AsyncSession) -> UserModel:
        """
        Найти пользователя по ID или выбросить ошибку 404 Not Found.
        """

        user = await session.get(UserModel, user_id)
        if not user:
            logger.debug("Пользователь с id=%d не найден", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с id {user_id} Не найден",
            )
        return user

    @classmethod
    async def find_by_email(cls, email: str, session: AsyncSession) -> UserModel | None:
        """
        Найти пользователя по email.
        """
        query = select(UserModel).where(UserModel.email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def find_one_with_tasks(cls, user_id: int, session: AsyncSession) -> UserModel:
        """
        Найти пользователя по ID со списком его задач.
        """
        query = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.tasks))
        )
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с id {user_id} не найден",
            )
        return user
    

    @classmethod
    @db_transaction
    async def update_full(
        cls, user_id: int, data: SUserAdd, session: AsyncSession
    ) -> UserModel:
        # find_one_or_404 НЕ под декоратором — он выбросит 404, и это нормально
        user = await cls.find_one_or_404(user_id, session=session)

        user.name = data.name
        user.email = data.email
        user.is_active = data.is_active

        await session.commit()
        await session.refresh(user)

        logger.info("SUCCESS: Данные пользователя id=%s обновлены", user.id)
        return user

    @classmethod
    @db_transaction
    async def patch(
        cls, user_id: int, data: SUserPatch, session: AsyncSession
    ) -> UserModel:
        user = await cls.find_one_or_404(user_id, session=session)
        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(user, key, value)

        await session.commit()
        await session.refresh(user)

        logger.info(
            "SUCCESS: Пользователь id=%s частично обновлен. Измененные поля: %s",
            user.id,
            list(update_data.keys()),
        )
        return user

    @classmethod
    @db_transaction
    async def delete(cls, user_id: int, session: AsyncSession) -> None:
        user = await cls.find_one_or_404(user_id, session=session)
        await session.delete(user)
        await session.commit()

        logger.info("SUCCESS: Пользователь id=%s удален, его задачи теперь без исполнителя", user_id)