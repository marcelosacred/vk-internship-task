from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user import (
    create_user as create_user_service,
    free_users as free_users_service,
    get_users as get_users_service,
    lock_user as lock_user_service,
)

router = APIRouter()


# [post] /users - создать юзера
# [get] /users - получить всех юзеров
# [post] /users/lock - заблокировать юзера путем установки locktime в текущее время
# [post] /users/free - разблокировать всех юзеров (locktime = null)

@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user_service(db, user_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return user


@router.get("/users", response_model=list[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    return await get_users_service(db)


@router.post("/users/lock", response_model=UserResponse)
async def lock_user(db: AsyncSession = Depends(get_db)):
    try:
        user = await lock_user_service(db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return user


@router.post("/users/free")
async def free_users(db: AsyncSession = Depends(get_db)):
    await free_users_service(db)
    return {"detail": "all users unlocked"}
