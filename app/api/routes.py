from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.hash import bcrypt

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


# [post] /users - создать юзера
# [get] /users - получить всех юзеров
# [post] /users/lock - заблокировать юзера путем установки locktime в текущее время
# [post] /users/free - разблокировать всех юзеров (locktime = null)

@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    hashed_password = bcrypt.hash(user_data.password)

    user = User(
        login=user_data.login,
        password=hashed_password,
        project_id=user_data.project_id,
        env=user_data.env,
        domain=user_data.domain,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users", response_model=list[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


@router.post("/users/lock", response_model=UserResponse)
async def lock_user(db: AsyncSession = Depends(get_db)):
    # ищем первого незанятого юзера
    result = await db.execute(
        select(User).where(User.locktime.is_(None)).limit(1)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="нет свободных пользователей")

    user.locktime = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/free")
async def free_users(db: AsyncSession = Depends(get_db)):
    await db.execute(update(User).values(locktime=None))
    await db.commit()
    return {"detail": "все пользователи разблокированы"}
