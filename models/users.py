from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean

from database import Model


if TYPE_CHECKING:
    from models.tasks import TaskModel

class UserModel(Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tasks: Mapped[list[TaskModel]] = relationship(
        back_populates="user"
    )

    def __repr__(self) -> str:
        return (
            f"UserModel(id={self.id!r}, "
            f"name={self.name!r}, "
            f"email={self.email!r}, "
            f"is_active={self.is_active!r})"
        )        