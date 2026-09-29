from pydantic import BaseModel, ConfigDict, Field


# Схема для создания задачи (POST)
class STaskAdd(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Название задачи")
    description: str | None = Field(
        default=None, max_length=500, description="Описание задачи"
    )
    is_completed: bool = Field(default=False, description="Статус выполнения")
    priority: int = Field(..., ge=1, le=5, description="Приоритет задачи от 1 до 5")
    user_id: int | None = Field(default=None, description="ID пользователя")


# Схема для ответа API (GET, PUT, PATCH после обновления)
# Только отражает данные из БД, без валидации
class STask(BaseModel):
    id: int
    title: str
    description: str | None
    is_completed: bool
    priority: int
    user_id: int | None
    

    model_config = ConfigDict(from_attributes=True)


# Схема для частичного обновления (PATCH)
class STaskPatch(BaseModel, extra="forbid"):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    is_completed: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    user_id: int | None = None