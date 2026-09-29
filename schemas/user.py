from pydantic import BaseModel, ConfigDict, Field, EmailStr


class SUserAdd(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    is_active: bool = Field(default=True)


class SUser(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SUserPatch(BaseModel, extra="forbid"):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    is_active: bool | None = None        