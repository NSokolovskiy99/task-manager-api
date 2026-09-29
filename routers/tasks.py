from fastapi import APIRouter, Query, status
from services.tasks_repository import TaskRepository
from schemas.task import STask, STaskAdd, STaskPatch
from database import SessionDep

router = APIRouter(prefix="/tasks", tags=["Задачи"])


@router.post("/", response_model=STask, status_code=status.HTTP_201_CREATED)
async def create(data: STaskAdd, session: SessionDep):
    return await TaskRepository.add_one(data=data, session=session)


@router.get("/", response_model=list[STask])
async def get_tasks(
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_completed: bool | None = Query(None),
):
    tasks = await TaskRepository.find_all(
        session, skip=skip, limit=limit, is_completed=is_completed
    )
    return tasks


@router.get("/{task_id}", response_model=STask)
async def get_task(task_id: int, session: SessionDep):
    return await TaskRepository.find_one_or_404(task_id=task_id, session=session)


@router.put("/{task_id}", response_model=STask)
async def update_task(task_id: int, data: STaskAdd, session: SessionDep):
    return await TaskRepository.update_full(task_id=task_id, data=data, session=session)


@router.patch("/{task_id}", response_model=STask)
async def patch_task(task_id: int, data: STaskPatch, session: SessionDep):
    return await TaskRepository.patch(task_id=task_id, data=data, session=session)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, session: SessionDep):
    await TaskRepository.delete(task_id=task_id, session=session)