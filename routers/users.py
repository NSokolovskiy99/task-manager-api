from fastapi import APIRouter, Query, status
from services.users_repository import UserRepository
from schemas.user import SUserAdd, SUser, SUserPatch
from database import SessionDep

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.post("/", response_model=SUser, status_code=status.HTTP_201_CREATED)
async def create(data: SUserAdd, session: SessionDep):
    return await UserRepository.add_one(data=data, session=session)