from fastapi import APIRouter, Query, status
from services.users_repository import UserRepository
from schemas.user import SUserAdd, SUser, SUserPatch, SUserWithTasks
from database import SessionDep

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.post("/", response_model=SUser, status_code=status.HTTP_201_CREATED)
async def create(data: SUserAdd, session: SessionDep):
    return await UserRepository.add_one(data=data, session=session)


@router.get("/", response_model=list[SUser])
async def get_users(
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    has_completed_tasks: bool | None = Query(None),
):
    return await UserRepository.find_all(session=session, skip=skip, limit=limit, has_completed_tasks=has_completed_tasks)


@router.get("/{user_id}", response_model=SUser)
async def get_user(user_id: int, session: SessionDep):
    return await UserRepository.find_one_or_404(user_id=user_id, session=session)


@router.get("/{user_id}/tasks", response_model=SUserWithTasks)
async def get_user_with_tasks(user_id: int, session: SessionDep):
    return await UserRepository.find_one_with_tasks(user_id=user_id, session=session)


@router.put("/{user_id}", response_model=SUser)
async def update_user(user_id: int, data: SUserAdd, session: SessionDep):
    return await UserRepository.update_full(user_id=user_id, data=data, session=session)


@router.patch("/{user_id}", response_model=SUser)
async def patch_user(user_id: int, data: SUserPatch, session: SessionDep):
    return await UserRepository.patch(user_id=user_id, data=data, session=session)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: SessionDep):
    await UserRepository.delete(user_id=user_id, session=session)