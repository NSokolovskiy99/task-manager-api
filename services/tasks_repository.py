from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from models.users import UserModel
from models.tasks import TaskModel
from schemas.task import STaskAdd, STaskPatch
import logging
from utils.db_decorators import db_transaction

logger = logging.getLogger(__name__)


class TaskRepository:
    @classmethod
    @db_transaction
    async def add_one(cls, data: STaskAdd, session: AsyncSession) -> TaskModel:
        logger.info("DEBUG: received data = %s", data.model_dump())
        task = TaskModel(
            title=data.title,
            description=data.description,
            is_completed=data.is_completed,
            priority=data.priority,
            user_id=data.user_id,
        )

        if data.user_id is not None:
            user = await session.get(UserModel, data.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {data.user_id} not found",
                )

        session.add(task)
        await session.commit()
        await session.refresh(task)

        logger.info("SUCCESS: Task created with id=%s", task.id)
        return task

    @classmethod
    async def find_all(
        cls,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        is_completed: bool | None = None,
    ):
        query = select(TaskModel).offset(skip).limit(limit)
        if is_completed is not None:
            query = query.where(TaskModel.is_completed == is_completed)

        result = await session.execute(query)
        tasks = result.scalars().all()
        return tasks

    @classmethod
    async def find_one_or_404(cls, task_id: int, session: AsyncSession) -> TaskModel:
        """
        Найти задачу по ID или выбросить ошибку 404 Not Found.
        """

        task = await session.get(TaskModel, task_id)
        if not task:
            logger.debug("Task with id=%d not found", task_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found",
            )
        return task

    @classmethod
    @db_transaction
    async def update_full(
        cls, task_id: int, data: STaskAdd, session: AsyncSession
    ) -> TaskModel:
        # find_one_or_404 НЕ под декоратором — он выбросит 404, и это нормально
        task = await cls.find_one_or_404(task_id, session=session)

        if data.user_id is not None:
            user = await session.get(UserModel, data.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {data.user_id} not found",
                )

        task.title = data.title
        task.description = data.description
        task.is_completed = data.is_completed
        task.priority = data.priority
        task.user_id = data.user_id

        await session.commit()
        await session.refresh(task)

        logger.info("SUCCESS: Task id=%s updated", task.id)
        return task

    @classmethod
    @db_transaction
    async def patch(
        cls, task_id: int, data: STaskPatch, session: AsyncSession
    ) -> TaskModel:
        task = await cls.find_one_or_404(task_id, session=session)
        update_data = data.model_dump(exclude_unset=True)

        # Проверка: если присваиваем НОВОГО исполнителя, он должен существовать.
        # Явный null ("отвязка") пропускаем — это легитимное действие.
        if "user_id" in update_data and update_data["user_id"] is not None:
            user = await session.get(UserModel, update_data["user_id"])
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {update_data['user_id']} not found",
                )

        # Поля, которым в БД разрешён NULL (nullable=True в модели)
        nullable_fields = {"description", "user_id"}

        for key, value in update_data.items():
            if value is None and key not in nullable_fields:
                # title / priority / is_completed — NOT NULL в БД:
                # лучше сразу отдать 422, чем 409 от IntegrityError
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Field '{key}' cannot be set to null",
                )
            setattr(task, key, value)

        await session.commit()
        await session.refresh(task)

        logger.info(
            "SUCCESS: Task id=%s patched with fields: %s",
            task.id,
            list(update_data.keys()),
        )
        return task

    @classmethod
    @db_transaction
    async def delete(cls, task_id: int, session: AsyncSession) -> None:
        task = await cls.find_one_or_404(task_id, session=session)
        await session.delete(task)
        await session.commit()

        logger.info("SUCCESS: Task id=%s deleted", task_id)