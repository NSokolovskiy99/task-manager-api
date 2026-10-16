from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from sqlalchemy import String, Boolean, Text, false, CheckConstraint, Index

from database import Model

if TYPE_CHECKING:
    from models.users import UserModel


class TaskModel(Model):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    priority: Mapped[int] = mapped_column(nullable=False)

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), # Удаление пользователя не удаляет его задачи 
        nullable=True,
        index=True         # Фильтрация `WHERE user_id = ?` пойдёт по индексу
    )

    user: Mapped[UserModel | None] = relationship(
        back_populates="tasks",
    )

    __table_args__ = (
        CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="ck_tasks_priority_range",
        ),
        Index(
            "ix_tasks_completed_priority",
            "is_completed",
            "priority",
        )
    )

    def __repr__(self) -> str:
        return (
            f"TaskModel(id={self.id!r}, "
            f"title={self.title!r}, "
            f"description={self.description!r}, "
            f"is_completed={self.is_completed!r}, "
            f"priority={self.priority!r})"
        )